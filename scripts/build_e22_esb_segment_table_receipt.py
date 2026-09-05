#!/usr/bin/env python3
"""Pin the ESB Earnings-22 segment table this study cuts its utterances at.

``sanchit-gandhi/earnings22_split`` is the published partition of the
Earnings-22 corpus by source file that the Open ASR Leaderboard's
"Earnings22" column is computed over. This study needs exactly six of its
columns -- ``source_id``, ``segment_id``, ``sentence``, ``start_ts``,
``end_ts``, ``id`` -- to cut the six ESB TEST calls it already owns into the
published utterances.

**This table is a derived-split REFERENCE pinned by hash, not a new umbrella
lock asset.** It adds no entry to ``docs/datasets.lock.json``, materializes
no new audio, and is never resolved through ``data.lock``/``data.carriers``.
The only audio this study sends stays the locked ``earnings22-original``
MP3 bytes D1 already closed over.

Identity, in three independent layers:

1. **The upstream repository.** Pinned at commit
   ``f9fb35f4134e32b9c8100199d949398fd6d08a5f`` -- a content hash, not a
   branch name. Each of the four ``test-*`` parquet files is pinned by the
   repository's own git-LFS ``oid``, which IS the SHA-256 of the file's
   bytes.
2. **A local re-hash.** All four test shards (1.10 GB) were fetched with a
   resumable ranged GET -- a single unranged stream broke twice with
   ``IncompleteRead`` on this link -- and every one of them is re-hashed here
   and compared with the published LFS oid; a disagreement is a hard refusal.
   The receipt records, per file, whether the pin was confirmed locally or
   rests on the published oid alone, so a future rebuild on a machine that
   never fetched the bytes still produces an honest receipt rather than a
   silently weaker one.
3. **The extracted table.** The six metadata columns are read with a pyarrow
   COLUMN PROJECTION so the ``audio`` column is never materialized, written
   to one JSONL under the controlled data root, and hash-pinned here. That
   file -- not the parquet -- is what the roster builder and the ESB scorers
   actually consume, and it is what every downstream receipt binds to.

Row count: this table carries **2,735** test rows. The leaderboard config
``hf-audio/open-asr-leaderboard`` reports **2,741** for the same column. The
six-row gap is unexplained and is recorded here as unresolved rather than
reconciled by guesswork.

Zero model contact, zero tokenizer contact, no audio decode.

Usage::

    python scripts/build_e22_esb_segment_table_receipt.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]

DATASET_REPO_ID = "sanchit-gandhi/earnings22_split"
DATASET_REVISION = "f9fb35f4134e32b9c8100199d949398fd6d08a5f"
COLUMNS = ("source_id", "segment_id", "sentence", "start_ts", "end_ts", "id")
ESB_TEST_CALLS = ("4432298", "4450488", "4470290", "4479741", "4483338", "4485244")
ESB_VALIDATION_CALLS = ("4420696", "4448760", "4461799", "4469836", "4473238", "4482110")
LEADERBOARD_ROW_COUNT = 2741

SEGMENT_TABLE_SUBDIR = "derived/e22-esb-segment-table"
EXTRACTED_RELPATH = f"{SEGMENT_TABLE_SUBDIR}/segments-test.jsonl"
PARQUET_SUBDIR = f"{SEGMENT_TABLE_SUBDIR}/parquet"

# (repo-relative path, git-LFS oid == SHA-256 of the file bytes, size in bytes,
# xet hash) exactly as https://huggingface.co/api/datasets/<repo>/tree/main
# reports them at the pinned revision.
PARQUET_FILES = (
    (
        "data/test-00000-of-00004-d1f708ede2712e90.parquet",
        "59c6dda0a955fd2435ff186ff675954b14dd84ef3716dc4190844ddfa6c6622c",
        383221699,
        "8e5cd221d86ce4ebda9f55585b6d566c6ea4e1c4f0addda07d4b98e9d7aab80b",
    ),
    (
        "data/test-00001-of-00004-f75446185bfca385.parquet",
        "99f92bdeb3965ee02a289100c4085d1024a0bfdb9045bcfb6c19e171c81e73ca",
        304147076,
        "a5108eff5925eb781299f265ca2986652ee5537f902f92848b74b95c0e231353",
    ),
    (
        "data/test-00002-of-00004-0090a7442c459172.parquet",
        "f2f5cf44af8264547646e3e26131e993a705fc1d7adb3770a6ffecd45e13d059",
        218834748,
        "abe269d53baa5ad2891e76822d1569718cd6b3fdcf37bca9ec48462b6f3612c2",
    ),
    (
        "data/test-00003-of-00004-c18462f0ad18104e.parquet",
        "427a0c400efd66f351a1bbba2713c1255e2cb875679a84ea8262dbf39611bf8b",
        194875805,
        "14f400c9d375bdf3423687f8db77626fe1a4f61e1d8717093c158f69e1cb5551",
    ),
)

# The parquet schema the extractor saw, recorded so a future re-extraction
# that silently changes a column type is visible.
PARQUET_SCHEMA = (
    "source_id:string",
    "audio:struct<bytes: binary, path: string>",
    "segment_id:string",
    "sentence:string",
    "start_ts:float",
    "end_ts:float",
    "id:string",
)

DEFAULT_OUTPUT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-e22-esb-shortform-alignment-400-v1"
    / "segment-table"
    / "segment-table-receipt.json"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract(data_root: Path) -> Path:
    """Re-run the column projection against the pinned revision.

    Heavy imports stay inside this function (repo convention): a plain
    receipt rebuild from an already-extracted table needs neither pyarrow nor
    the hub client, and must not require network.
    """

    import pyarrow.parquet as pq  # noqa: PLC0415
    from huggingface_hub import HfFileSystem  # noqa: PLC0415

    filesystem = HfFileSystem()
    rows: list[dict[str, Any]] = []
    for relpath, _oid, _size, _xet in PARQUET_FILES:
        remote = f"datasets/{DATASET_REPO_ID}@{DATASET_REVISION}/{relpath}"
        with filesystem.open(remote, "rb") as handle:
            table = pq.ParquetFile(handle).read(columns=list(COLUMNS))
        rows.extend(table.to_pylist())
    target = Path(data_root) / EXTRACTED_RELPATH
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return target


def build(data_root: Path) -> dict[str, Any]:
    root = Path(data_root)
    table_path = root / EXTRACTED_RELPATH
    if not table_path.is_file():
        raise SystemExit(f"extracted segment table is missing: {table_path}")
    rows = [
        json.loads(line)
        for line in table_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise SystemExit("extracted segment table is empty")
    for row in rows:
        if set(row) != set(COLUMNS):
            raise SystemExit(f"extracted row carries unexpected columns: {sorted(row)}")
    sources = sorted({str(row["source_id"]) for row in rows})
    if tuple(sources) != tuple(sorted(ESB_TEST_CALLS)):
        raise SystemExit(
            f"extracted table names {sources}, not the six ESB test calls "
            f"{sorted(ESB_TEST_CALLS)}"
        )
    ids = [str(row["id"]) for row in rows]
    if len(set(ids)) != len(ids):
        raise SystemExit("extracted table carries duplicate segment ids")
    counts = Counter(str(row["source_id"]) for row in rows)
    spans = [float(row["end_ts"]) - float(row["start_ts"]) for row in rows]

    parquet: list[dict[str, Any]] = []
    for relpath, lfs_oid, size, xet in PARQUET_FILES:
        local = root / PARQUET_SUBDIR / Path(relpath).name
        entry: dict[str, Any] = {
            "path": relpath,
            "bytes": size,
            "sha256": lfs_oid,
            "sha256_source": "git-lfs oid at the pinned revision (the file's own SHA-256)",
            "xet_hash": xet,
            "locally_rehashed": False,
        }
        if local.is_file() and local.stat().st_size == size:
            measured = sha256_file(local)
            entry["locally_rehashed"] = True
            entry["local_sha256"] = measured
            entry["local_matches_lfs_oid"] = measured == lfs_oid
            entry["local_relpath"] = f"{PARQUET_SUBDIR}/{Path(relpath).name}"
            if measured != lfs_oid:
                raise SystemExit(
                    f"{relpath}: local SHA-256 {measured} disagrees with the published "
                    f"LFS oid {lfs_oid}"
                )
        parquet.append(entry)

    payload = table_path.read_bytes()
    document = {
        "schema": "saea-e22-esb-segment-table-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "what_this_is": (
            "A derived-split reference pinned by hash, NOT a new umbrella lock asset. "
            "It adds no entry to docs/datasets.lock.json, materializes no new audio, and "
            "is never resolved through data.lock or data.carriers. The only audio this "
            "study sends stays the locked earnings22-original MP3 bytes D1 already closed "
            "over; this table supplies the published segment BOUNDARIES those bytes are "
            "cut at, and the published reference SENTENCES they are scored against."
        ),
        "upstream": {
            "repo_id": DATASET_REPO_ID,
            "repo_type": "dataset",
            "revision": DATASET_REVISION,
            "split": "test",
            "url": f"https://huggingface.co/datasets/{DATASET_REPO_ID}/tree/{DATASET_REVISION}",
            "license_note": (
                "the split is a repartition of the Rev Earnings-22 corpus this study "
                "already licenses under its earnings22-original lock entry"
            ),
            "esb_test_calls": list(ESB_TEST_CALLS),
            "esb_validation_calls": list(ESB_VALIDATION_CALLS),
            "esb_validation_note": (
                "recorded for completeness only; the validation calls are NOT read by "
                "this study and stay confirmatory"
            ),
        },
        "parquet_files": parquet,
        "parquet_schema": list(PARQUET_SCHEMA),
        "extraction": {
            "method": (
                "pyarrow ParquetFile.read(columns=[...]) over huggingface_hub.HfFileSystem "
                "at the pinned revision -- a COLUMN PROJECTION, so the 'audio' column is "
                "never materialized"
            ),
            "columns": list(COLUMNS),
            "audio_column_materialized": False,
        },
        "extracted_table": {
            "relpath": EXTRACTED_RELPATH,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
            "rows": len(rows),
            "format": "JSONL, one object per segment, sort_keys, LF, UTF-8",
            "location_basis": (
                "under the controlled data root, never in Git and never inside the locked "
                "carrier tree: the 'sentence' column is gold reference text"
            ),
        },
        "population": {
            "calls": len(sources),
            "segments": len(rows),
            "segments_per_call": dict(sorted(counts.items())),
            "segment_seconds_total": round(sum(spans), 6),
            "segment_seconds_longest": round(max(spans), 6),
            "segment_seconds_shortest": round(min(spans), 6),
            "segment_seconds_mean": round(sum(spans) / len(spans), 6),
            "segments_longer_than_20s": sum(1 for span in spans if span > 20.0),
            "segments_longer_than_30s": sum(1 for span in spans if span > 30.0),
        },
        "unresolved": {
            "row_count_discrepancy": (
                f"this table carries {len(rows)} test rows; the leaderboard config "
                f"hf-audio/open-asr-leaderboard reports {LEADERBOARD_ROW_COUNT} for the same "
                "Earnings22 column, and the NVIDIA NeMo AutoModel post that publishes the "
                f"9.79 target states N = {LEADERBOARD_ROW_COUNT}. The "
                f"{LEADERBOARD_ROW_COUNT - len(rows)}-row gap is UNEXPLAINED. It is recorded, "
                "not reconciled: no row is invented, dropped or re-cut to close it, and every "
                "number this study reports is over the 2,735 rows this pinned table actually "
                "contains."
            ),
            "timestamp_precision": (
                "start_ts/end_ts are float32 in the upstream parquet, so a boundary carries "
                "about 1e-4 s of representation error at these magnitudes; the cut is made at "
                "the float32 value verbatim rather than at a re-rounded one"
            ),
        },
    }
    return document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--extract",
        action="store_true",
        help=(
            "re-run the column-projected read against the pinned revision and rewrite "
            "the extracted JSONL before receipting it (requires network)"
        ),
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = args.data_root
    if root is None:
        value = os.environ.get("SPEECHRL_DATA_DIR")
        if not value:
            raise SystemExit("--data-root or SPEECHRL_DATA_DIR is required")
        root = Path(value)
    if args.extract:
        extract(root)
    document = build(root)
    text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "rows": document["extracted_table"]["rows"],
                "extracted_sha256": document["extracted_table"]["sha256"],
                "segments_per_call": document["population"]["segments_per_call"],
                "segment_seconds_total": document["population"]["segment_seconds_total"],
                "parquet_locally_rehashed": [
                    entry["path"] for entry in document["parquet_files"] if entry["locally_rehashed"]
                ],
                "output": str(args.output),
                "output_sha256": (
                    sha256_file(args.output)
                    if args.write
                    else hashlib.sha256(text.encode("utf-8")).hexdigest()
                ),
                "written": args.write,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
