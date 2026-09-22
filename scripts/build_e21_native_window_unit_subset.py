#!/usr/bin/env python3
"""Item E35 (owner decision 89, 2026-09-21): derive a small, named subset of
the shared Earnings21 native-window execution-unit inventory
(``analysis/SAEA-E21-DR-SHARED-EXACT-WINDOW-INVENTORY-V1/window-inventory.json``)
for a small registered cell (the four-row smoke, the sub10 paired read),
model-free.

WHY A SEPARATE ARTIFACT, NOT A SLICE DECLARATION: the runtime's own execution-
unit loader (``core.preparation_windows.load_raw_execution_unit_roster``)
requires ``prepared_execution_units.unit_count`` to equal the COMPLETE
request count of the named batch inside the referenced file -- a partial
read of the shared 1,593-row batch is refused, by design (no filtering seam
at that layer). A cell that wants fewer rows therefore needs its OWN batch,
under its OWN name, containing ONLY the rows it flies.

WHAT THIS SCRIPT DOES NOT DO: it never reads, decodes, or writes any audio
byte. Every field a kept row needs (payload_sha256, encoding_key_sha256,
source_provenance, and each unique audio's audio_byte_count) is already
present, verbatim, in the shared inventory's own rows and its own
``encoding_inputs`` table -- this script only re-partitions that already-
computed, already-verified metadata under a new batch name, exactly
reproducing ``core.preparation_windows.build_window_feature_inventory``'s own
wrapper shape and ``core.preparation.digest``'s own canonicalisation, so the
result is byte-identical to what the real preparation pipeline would have
produced had it been run against this smaller roster directly.

SELECTION RULE (kept simple and auditable): for each requested sample id,
keep that call's OWN windows in their ORIGINAL order, either all of them
(``--per-call-limit`` omitted) or the FIRST N of them (``--per-call-limit
N``) -- never a scattered pick. The runtime's own per-parent contiguity
check (``load_raw_execution_unit_roster``: "execution units are duplicated,
missing or out of order") requires each call's kept windows to start at
w0001 and run without gaps, and a prefix of the call's own original window
sequence is the only selection shape that ever satisfies that check without
renumbering a single ``request_key`` (which would silently break the
per-window ``payload_sha256``/``encoding_key_sha256`` binding to the wrong
audio).

USAGE (run by root once this item is admitted; NEVER writes under
SPEECHRL_DATA_DIR without the person running it choosing that path -- pass
``--dry-run`` to compute and print the resulting file's sha256 without
writing anything, exactly as this item's own registration did to pin the
hashes below before any file existed):

    python scripts/build_e21_native_window_unit_subset.py \\
        --source /path/to/window-inventory.json \\
        --batch-name SAEA-E21-NATIVE-WINDOW-FOUR-ROW-V1 \\
        --sample-id 4320211 --per-call-limit 4 \\
        --output /path/to/analysis/SAEA-E21-NATIVE-WINDOW-FOUR-ROW-V1/window-inventory.json

    python scripts/build_e21_native_window_unit_subset.py \\
        --source /path/to/window-inventory.json \\
        --batch-name SAEA-E21-NATIVE-WINDOW-SUB10-V1 \\
        --sample-id 4330115 --sample-id 4365024 --sample-id 4365948 \\
        --sample-id 4366429 --sample-id 4366522 --sample-id 4384964 \\
        --sample-id 4385072 --sample-id 4387383 --sample-id 4389907 \\
        --sample-id 4397829 \\
        --output /path/to/analysis/SAEA-E21-NATIVE-WINDOW-SUB10-V1/window-inventory.json

Pinned expectations this item registered (2026-09-22, computed model-free
against the committed shared inventory's own ``output_sha256``
``09a154a65b83171920b834e706558e75f1a661593cea1ef2ecf1f5503982573d``):

* FOUR-ROW (sample 4320211, ``--per-call-limit 4``): unit_count 4,
  file sha256 e5f3cfbcbc407fbb3a7b59469b86ab9d405f7b43963cb2d18b655790c5f4a32b.
* SUB10 (the ten ids in ``docs/receipts/probe-samples/r4-e21-sub10-sample.json``,
  no per-call limit): unit_count 342,
  file sha256 57ee023e4c1e38a79f99418c9e9dd5e4f87233a2162eac213ac070a73a31bba5.

A run that reproduces a different hash than the one a registered config
pins means the shared inventory changed, or the selection changed, since
this item registered it -- refuse and re-check before flying.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def build_subset(
    source_path: Path, *, sample_ids: list[str], per_call_limit: int | None, batch_name: str
) -> tuple[dict, bytes, str]:
    source = json.loads(Path(source_path).read_text(encoding="utf-8"))
    src_output = source["output"]
    src_requests = src_output["batches"][0]["requests"]
    sample_set = set(sample_ids)

    kept = []
    per_call_seen: dict[str, int] = {}
    for row in src_requests:
        sid = row["source_provenance"]["sample_id"]
        if sid not in sample_set:
            continue
        n = per_call_seen.get(sid, 0)
        if per_call_limit is not None and n >= per_call_limit:
            continue
        kept.append(row)
        per_call_seen[sid] = n + 1

    missing = sample_set - set(per_call_seen)
    if missing:
        raise SystemExit(f"sample ids not found in source inventory: {sorted(missing)}")
    if per_call_limit is not None:
        short = {sid: n for sid, n in per_call_seen.items() if n < per_call_limit}
        if short:
            raise SystemExit(f"calls with fewer than {per_call_limit} windows: {short}")

    src_by_sha = {e["audio_sha256"]: e for e in src_output["encoding_inputs"]}
    unique: dict[str, dict[str, object]] = {}
    for row in kept:
        audio_sha256 = row["source_provenance"]["sha256"]
        reference = {"batch": batch_name, "request_key": row["request_key"]}
        if audio_sha256 in unique:
            unique[audio_sha256]["requests"].append(reference)
        else:
            unique[audio_sha256] = {
                "audio_sha256": audio_sha256,
                "audio_byte_count": src_by_sha[audio_sha256]["audio_byte_count"],
                "encoding_key_sha256": row["encoding_key_sha256"],
                "requests": [reference],
            }

    output = {
        "schema": src_output["schema"],
        "state": src_output["state"],
        "encoder_identity": src_output["encoder_identity"],
        "request_count": len(kept),
        "unique_audio_count": len(unique),
        "batches": [{"name": batch_name, "requests": kept}],
        "encoding_inputs": [unique[key] for key in sorted(unique)],
    }
    inputs = {
        "encoder_identity": output["encoder_identity"],
        "window_sources_sha256": digest(output["batches"]),
    }
    artifact = {
        "schema": "saea-prepared-artifact-v1",
        "kind": "exact-window-feature-inventory-v1",
        "contact_class": "model-free",
        "inputs": inputs,
        "output": output,
        "output_sha256": digest(output),
    }
    raw = canonical_bytes(artifact)
    return artifact, raw, hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--batch-name", required=True)
    parser.add_argument("--sample-id", action="append", required=True, dest="sample_ids")
    parser.add_argument("--per-call-limit", type=int, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="compute and print unit_count/sha256 without writing --output",
    )
    args = parser.parse_args()

    artifact, raw, file_sha256 = build_subset(
        args.source,
        sample_ids=args.sample_ids,
        per_call_limit=args.per_call_limit,
        batch_name=args.batch_name,
    )
    print(f"unit_count: {artifact['output']['request_count']}")
    print(f"file_sha256: {file_sha256}")
    print(f"bytes: {len(raw)}")

    if args.dry_run or args.output is None:
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    print(f"written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
