"""Section 4.2's built-in falsifier, recomputed row by row from the sealed trace.

Runs BEFORE any score is read. Every flown row's ``prompt_tokens`` must equal
``49 + analysis.e22_short_clip_encoding.llamacpp_audio_tokens(n_samples)`` for
that row's variant media, with the predicted audio-token count RECOMPUTED from
the row's own ``n_samples`` rather than read from the roster column -- and the
roster column checked against it as well.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis.e22_short_clip_encoding import (  # noqa: E402
    llamacpp_audio_tokens,
)

ROSTER = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-07-e22-test2735-tail2s-media/roster/flight-roster-receipt.json"
)
TEXT_ENVELOPE_TOKENS = 49


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--rows-expected", required=True, type=int)
    parser.add_argument("--predicted-total", required=True, type=int)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    roster_bytes = ROSTER.read_bytes()
    roster = json.loads(roster_bytes.decode("utf-8"))
    by_id = {str(item["sample_id"]): item for item in roster["items"]}

    # The sealed trace carries the sample id on the MODEL_REQUEST record and the
    # usage block on the matching MODEL_RESPONSE record; both share the request
    # id, which is the join key.
    trace_path = args.run_dir / f"{args.run_id}.trace.jsonl"
    sample_by_request: dict[str, str] = {}
    tokens_by_request: dict[str, int] = {}
    completion_by_request: dict[str, int] = {}
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        channel = record.get("channel")
        record_id = str(record.get("record_id") or "")
        request_id = record_id.rsplit("/", 1)[0]
        payload = record.get("payload") or {}
        if channel == "MODEL_REQUEST":
            inner = payload.get("payload") or {}
            sample_by_request[request_id] = str(inner["sample_id"])
        elif channel == "MODEL_RESPONSE":
            usage = payload.get("usage") or {}
            tokens_by_request[request_id] = int(usage["prompt_tokens"])
            completion_by_request[request_id] = int(usage.get("completion_tokens", 0))

    measured: dict[str, int] = {}
    completions: dict[str, int] = {}
    for request_id, sample_id in sample_by_request.items():
        if request_id not in tokens_by_request:
            raise SystemExit(f"no MODEL_RESPONSE usage for request {request_id!r}")
        if sample_id in measured:
            raise SystemExit(f"duplicate trace row for {sample_id!r}")
        measured[sample_id] = tokens_by_request[request_id]
        completions[sample_id] = completion_by_request[request_id]

    rows = []
    disagreements = []
    roster_column_disagreements = []
    for sample_id in sorted(measured):
        item = by_id.get(sample_id)
        if item is None:
            raise SystemExit(f"trace row {sample_id!r} is not in the frozen roster")
        n_samples = int(item["n_samples"])
        predicted_audio = int(llamacpp_audio_tokens(n_samples))
        expected = TEXT_ENVELOPE_TOKENS + predicted_audio
        actual = measured[sample_id]
        roster_column = int(item["audio_tokens"])
        row = {
            "sample_id": sample_id,
            "seconds": float(item["audio_seconds"]),
            "published_seconds": float(item["source_audio_seconds"]),
            "n_samples": n_samples,
            "predicted_audio_tokens": predicted_audio,
            "roster_audio_tokens_column": roster_column,
            "expected_prompt_tokens": expected,
            "measured_prompt_tokens": actual,
            "completion_tokens": completions[sample_id],
            "holds": actual == expected,
        }
        rows.append(row)
        if actual != expected:
            disagreements.append(row)
        if roster_column != predicted_audio:
            roster_column_disagreements.append(row)

    measured_total = sum(r["measured_prompt_tokens"] for r in rows)
    expected_total = sum(r["expected_prompt_tokens"] for r in rows)

    # The sealed cost block's own prompt_tokens_total, as an independent read.
    manifest = json.loads(
        (args.run_dir / f"{args.run_id}.run-manifest.json").read_text(encoding="utf-8")
    )

    def find_cost_total(node):
        if isinstance(node, dict):
            if "prompt_tokens_total" in node:
                return node["prompt_tokens_total"]
            for value in node.values():
                found = find_cost_total(value)
                if found is not None:
                    return found
        elif isinstance(node, list):
            for value in node:
                found = find_cost_total(value)
                if found is not None:
                    return found
        return None

    cost_total = find_cost_total(manifest)

    verdict = (
        "HOLDS"
        if (
            not disagreements
            and not roster_column_disagreements
            and len(rows) == args.rows_expected
            and measured_total == expected_total == args.predicted_total
        )
        else "FALSIFIED"
    )

    receipt = {
        "schema": "saea-e22-encoding-falsifier-v1",
        "study": "speech-aware-evidence-acquisition",
        "rule": (
            "prompt_tokens == 49 + "
            "analysis.e22_short_clip_encoding.llamacpp_audio_tokens(n_samples), recomputed "
            "from each row's own n_samples rather than read from the roster column"
        ),
        "preregistration": (
            "docs/readiness/2026-09-07-e22-esb-shortform-tail2s-test-v1-preregistration.md "
            "section 4.2"
        ),
        "run_id": args.run_id,
        "variant": "tail-silence-2s",
        "text_envelope_tokens": TEXT_ENVELOPE_TOKENS,
        "roster_receipt": (
            "docs/checks/speech-aware-evidence-acquisition/"
            "2026-09-07-e22-test2735-tail2s-media/roster/flight-roster-receipt.json"
        ),
        "roster_receipt_sha256": hashlib.sha256(roster_bytes).hexdigest(),
        "trace_sha256": sha256_file(trace_path),
        "rows_expected": args.rows_expected,
        "rows_checked": len(rows),
        "rows_where_the_falsifier_holds": sum(1 for r in rows if r["holds"]),
        "measured_prompt_tokens_total": measured_total,
        "expected_prompt_tokens_total": expected_total,
        "preregistered_predicted_total": args.predicted_total,
        "sealed_cost_prompt_tokens_total": cost_total,
        "predicted_prompt_tokens_total": expected_total,
        "disagreements": disagreements,
        "roster_audio_token_column_disagreements": roster_column_disagreements,
        "verdict": verdict,
        "rows": rows if len(rows) <= 16 else None,
        "rows_note": (
            None
            if len(rows) <= 16
            else "per-row detail elided at this size; the totals and the disagreement lists "
            "are the check"
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "verdict": verdict,
                "rows_checked": len(rows),
                "rows_expected": args.rows_expected,
                "holds": receipt["rows_where_the_falsifier_holds"],
                "measured_total": measured_total,
                "expected_total": expected_total,
                "preregistered_total": args.predicted_total,
                "sealed_cost_total": cost_total,
                "disagreements": len(disagreements),
                "roster_column_disagreements": len(roster_column_disagreements),
            },
            indent=1,
        )
    )
    if len(rows) <= 16:
        for r in rows:
            print(
                f"  {r['sample_id']:>22}  {r['seconds']:>10.6f}  n={r['n_samples']:>8}  "
                f"predicted_audio={r['predicted_audio_tokens']:>4}  "
                f"expected={r['expected_prompt_tokens']:>5}  "
                f"measured={r['measured_prompt_tokens']:>5}  {r['holds']}"
            )
    return 0 if verdict == "HOLDS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
