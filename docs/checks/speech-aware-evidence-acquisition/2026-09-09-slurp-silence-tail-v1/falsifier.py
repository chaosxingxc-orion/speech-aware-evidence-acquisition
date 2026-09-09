#!/usr/bin/env python3
"""Section 4.4 media falsifier for the SLURP silence-tail cell.

Run BEFORE any score file is opened. Every flown row must satisfy, with zero
disagreeing rows:

1. the delivered media is the committed ``@ts2`` byte: its on-disk SHA-256 and
   size equal the committed D1 media supplement's entry for that ``@ts2`` id
   and the frozen runtime view's own record;
2. the delivered audio seconds equal the SEALED comparator's own delivered
   seconds for the same published key PLUS exactly 2.0 -- checked both in
   floating point and as an exact 16 kHz sample count;
3. the packet the mmproj-free decoder was handed is the promoted ``@ts2``
   packet for that id, by SHA-256, from the pinned promotion receipt;
4. the roster is the comparator's own population, id for id after the ``@``
   suffix is stripped, with no extra and no missing row.

Zero model contacts. Reads the flight's own sealed trace, the committed
receipts and the media bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
DATA = Path("/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data")
PROMOTION = Path("/home/chao/feat-cache/slurp-dev1000-ts2-packets-04ccc72a/DEV-1000-TAIL2S-promotion.json")
COMPARATOR = ("SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1", "attempt-20260905T060424Z-2c5596")
TAIL_SECONDS = 2.0
RATE = 16000

CHECK_NAMES = (
    "rows",
    "id_has_ts2_suffix",
    "media_sha256_equals_supplement",
    "media_sha256_equals_runtime_view",
    "media_bytes_equal_supplement",
    "delivered_seconds_equal_sealed_plus_2",
    "delivered_samples_equal_sealed_plus_32000",
    "cost_seconds_equal_request_seconds",
    "packet_sha256_equals_promotion",
    "packet_id_carries_ts2",
    "mmproj_not_loaded",
    "media_path_inside_derived_root",
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def published_key(sample_id):
    return sample_id.split("@", 1)[0]


def trace_rows(path):
    rows = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        channel = record["channel"]
        payload = record["payload"]
        key = str(record["record_id"]).split("/", 1)[0]
        row = rows.setdefault(key, {})
        if channel == "MODEL_REQUEST":
            inner = payload["payload"]
            row["sample_id"] = inner["sample_id"]
            row["audio_seconds"] = float(inner["audio_seconds"])
            row["media_relpath"] = inner.get("media_relpath")
            row["packet_sha256"] = inner.get("speech_packet_sha256")
            parts = inner.get("speech_feature_parts") or [{}]
            row["packet_id"] = parts[0].get("packet_id")
            row["mmproj_loaded"] = inner.get("mmproj_loaded")
        elif channel == "COST":
            row["prompt_tokens"] = int(payload["prompt_tokens"])
            row["completion_tokens"] = int(payload["completion_tokens"])
            row["cost_audio_seconds"] = float(payload["audio_seconds"])
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--dataset-fragment", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    attempt_dir = DATA / "runs" / args.run_id / args.attempt_id
    manifest = read_json(attempt_dir / (args.run_id + ".run-manifest.json"))
    trace = trace_rows(Path(manifest["raw_trace"]["path"]))

    fragment = read_json(REPO / "configs/dataset" / (args.dataset_fragment + ".json"))
    view = {item["sample_id"]: item for item in fragment["items"]}

    supplement_rel = str(fragment["d1_media_supplement"])
    supplement_path = REPO / "docs" / supplement_rel
    supplement = read_json(supplement_path)
    supplement_digest, _ = sha256_file(supplement_path)
    supp = {entry["id"]: entry for entry in supplement["manifest"]}

    promotion = read_json(PROMOTION)
    packets = {entry["packet_id"]: entry for entry in promotion["packets"]}

    comparator_dir = DATA / "runs" / COMPARATOR[0] / COMPARATOR[1]
    comparator_manifest = read_json(comparator_dir / (COMPARATOR[0] + ".run-manifest.json"))
    comparator = trace_rows(Path(comparator_manifest["raw_trace"]["path"]))
    comparator_by_id = {row["sample_id"]: row for row in comparator.values()}

    checks = {name: 0 for name in CHECK_NAMES}
    disagreements = []
    token_deltas = []
    delivered_total = 0.0
    sealed_total = 0.0

    derived_root = str(fragment["derived_media_subdir"])
    for row in trace.values():
        checks["rows"] += 1
        sample_id = row["sample_id"]
        problems = []

        if sample_id.endswith("@ts2"):
            checks["id_has_ts2_suffix"] += 1
        else:
            problems.append("sample id has no @ts2 suffix")

        item = view.get(sample_id)
        entry = supp.get(sample_id)
        if item is None or entry is None:
            problems.append("id not in the frozen runtime view or the D1 supplement")
        else:
            media = DATA / entry["media_relpath"]
            digest, size = sha256_file(media)
            if digest == entry["sha256"]:
                checks["media_sha256_equals_supplement"] += 1
            else:
                problems.append("media sha256 " + digest + " != supplement " + entry["sha256"])
            if digest == item["audio_sha256"]:
                checks["media_sha256_equals_runtime_view"] += 1
            else:
                problems.append("media sha256 != runtime view record")
            if size == int(entry["bytes"]):
                checks["media_bytes_equal_supplement"] += 1
            else:
                problems.append("media bytes %d != supplement %d" % (size, int(entry["bytes"])))
            if str(row["media_relpath"]).startswith(derived_root + "/"):
                checks["media_path_inside_derived_root"] += 1
            else:
                problems.append("media path outside the derived root: " + str(row["media_relpath"]))

        sealed = comparator_by_id.get(published_key(sample_id))
        if sealed is None:
            problems.append("no sealed comparator row for the published key")
        else:
            delivered = row["audio_seconds"]
            expected = sealed["audio_seconds"] + TAIL_SECONDS
            delivered_total += delivered
            sealed_total += sealed["audio_seconds"]
            if abs(delivered - expected) <= 1e-9:
                checks["delivered_seconds_equal_sealed_plus_2"] += 1
            else:
                problems.append("delivered %r != sealed %r + 2.0" % (delivered, sealed["audio_seconds"]))
            if round(delivered * RATE) == round(sealed["audio_seconds"] * RATE) + RATE * 2:
                checks["delivered_samples_equal_sealed_plus_32000"] += 1
            else:
                problems.append("delivered sample count != sealed + 32,000")
            token_deltas.append(row["prompt_tokens"] - sealed["prompt_tokens"])

        if abs(row["cost_audio_seconds"] - row["audio_seconds"]) <= 1e-9:
            checks["cost_seconds_equal_request_seconds"] += 1
        else:
            problems.append("metered seconds != request seconds")

        packet = packets.get(row["packet_id"])
        if packet is None:
            problems.append("packet id not in the promotion receipt: " + str(row["packet_id"]))
        elif packet["packet_sha256"] != row["packet_sha256"]:
            problems.append("packet sha256 != promotion receipt")
        else:
            checks["packet_sha256_equals_promotion"] += 1
        if str(row["packet_id"]).endswith("@ts2"):
            checks["packet_id_carries_ts2"] += 1
        else:
            problems.append("packet id carries no @ts2 suffix")

        if row["mmproj_loaded"] is False:
            checks["mmproj_not_loaded"] += 1
        else:
            problems.append("mmproj_loaded is not False")

        if problems:
            disagreements.append({"sample_id": sample_id, "problems": problems})

    flown = set(published_key(row["sample_id"]) for row in trace.values())
    expected_population = set(published_key(sample_id) for sample_id in view)
    missing = sorted(expected_population - flown)
    extra = sorted(flown - expected_population)

    token_histogram = {}
    for delta in token_deltas:
        token_histogram[delta] = token_histogram.get(delta, 0) + 1

    passed = (
        not disagreements
        and not missing
        and not extra
        and all(count == checks["rows"] for name, count in checks.items() if name != "rows")
        and checks["rows"] == len(view)
    )

    document = {
        "schema": "saea-slurp-tail2s-media-falsifier-v1",
        "study": "speech-aware-evidence-acquisition",
        "rule": (
            "docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md "
            "section 4.4: every flown row's delivered audio seconds equal its sealed row's "
            "plus exactly 2.0 and its media SHA-256 equals the committed D1 supplement's "
            "entry for that @ts2 id; zero disagreeing rows, or the cell is void and no "
            "score is read"
        ),
        "run_id": args.run_id,
        "attempt_id": args.attempt_id,
        "dataset_fragment": args.dataset_fragment,
        "manifest_status": manifest["status"],
        "study_commit": manifest["study_commit"],
        "study_repo_dirt": manifest["study_repo_dirt"],
        "comparator": {"run_id": COMPARATOR[0], "attempt_id": COMPARATOR[1]},
        "d1_media_supplement": supplement_rel,
        "d1_media_supplement_sha256_declared": fragment["d1_media_supplement_sha256"],
        "d1_media_supplement_sha256_measured": supplement_digest,
        "promotion_receipt": str(PROMOTION),
        "checks": checks,
        "disagreeing_rows": disagreements,
        "population": {
            "flown": len(flown),
            "expected": len(expected_population),
            "missing": missing,
            "extra": extra,
        },
        "seconds": {
            "delivered_total": delivered_total,
            "sealed_total": sealed_total,
            "difference": delivered_total - sealed_total,
            "expected_difference": TAIL_SECONDS * len(trace),
            "manifest_metered": manifest["cost"]["audio_seconds_used"],
        },
        "prompt_tokens": {
            "cell_total": sum(row["prompt_tokens"] for row in trace.values()),
            "comparator_total_on_these_rows": sum(
                comparator_by_id[published_key(row["sample_id"])]["prompt_tokens"]
                for row in trace.values()
                if published_key(row["sample_id"]) in comparator_by_id
            ),
            "delta_histogram": {str(k): v for k, v in sorted(token_histogram.items())},
        },
        "passed": passed,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    printable = {k: v for k, v in document.items() if k != "disagreeing_rows"}
    print(json.dumps(printable, indent=2, sort_keys=True))
    if disagreements:
        print("DISAGREEING ROWS: %d" % len(disagreements))
        print(json.dumps(disagreements[:10], indent=2))
    print("FALSIFIER: %s" % ("PASS" if passed else "FAIL"))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
