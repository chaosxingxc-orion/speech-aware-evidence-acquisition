"""Build a model-free speech-query SOURCE INVENTORY from a committed runtime view and its roster receipt.

`core.speech_preparation_runtime.run_preparation` binds its query rows through `protocol["sources"]`, which must be
a `saea-speech-query-source-inventory-v1` file (the Fold A / Fold B precedent under
`SPEECHRL_DATA_DIR/coordination/*-speech-query-source-inventory-v3.json`): a `roster_sha256` that equals the
protocol's, and one row per recording with `id`, `media_relpath`, `audio_sha256`, `source_frames` and
`source_sample_rate_hz`. A runtime view (`saea-speech-native-runtime-view-v1`) carries seconds, not frames, so it
cannot stand in for the inventory; this tool derives the inventory from the view, verifying every media file's
bytes against the view's `audio_sha256` and reading the frame geometry from the audio HEADER only (no decode, no
encoder, no tokenizer, no network).

Usage (WSL, the shared venv, from the study root):

    python scripts/build_speech_query_source_inventory.py \
        --runtime-view configs/dataset/slurp-speech-native-dev2000-added.json \
        --roster-receipt docs/receipts/rosters/slurp-dev-2000-added-v1.json \
        --data-root "$SPEECHRL_DATA_DIR" \
        --out "$SPEECHRL_DATA_DIR/coordination/slurp-dev2000-added-speech-query-source-inventory-v1.json"

The tool prints the inventory's raw sha256 (the value to pin under `protocol.sources.sha256`), the split identity
hash it reproduces, and the exact audio seconds the preparation plan must cover.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "saea-speech-query-source-inventory-v1"
ROW_FIELDS = ("id", "media_relpath", "audio_sha256", "source_frames", "source_sample_rate_hz")


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roster_sample_ids(receipt: dict) -> set[str]:
    """The roster receipt's own sample identities, however the receipt spells them.

    A receipt frozen by ``core.roster.freeze_roster`` always carries
    ``sample_id`` (the schema's identity field); the ``id`` extra is optional
    and only some rosters declare it. ``SLURP-DEV-2000-ADDED-V1`` carries both
    and they are equal on all 1,000 rows, so reading ``id`` first keeps every
    already-sealed inventory reproducible byte for byte;
    ``SLURP-STAGE3-CONSTRUCTION-R01`` carries the draw extras
    (``draw_rank``, ``min_cosine_to_selected``, ``stratum``) and no ``id``,
    which used to raise ``KeyError: 'id'`` here before a single byte was read.
    """

    ids: set[str] = set()
    for index, item in enumerate(receipt["items"]):
        value = item.get("id", item.get("sample_id"))
        if not isinstance(value, str) or not value:
            raise SystemExit(f"roster receipt items[{index}] carries no sample identity")
        ids.add(value)
    return ids


def split_identity(carrier_lock_key: str, ids: list[str]) -> str:
    return hashlib.sha256(
        "\n".join(sorted(f"{carrier_lock_key}/{sample_id}" for sample_id in ids)).encode("utf-8")
    ).hexdigest()


def build(runtime_view: Path, roster_receipt: Path, data_root: Path, source_root: Path) -> dict:
    import soundfile  # header reads only

    view = json.loads(runtime_view.read_text(encoding="utf-8"))
    receipt = json.loads(roster_receipt.read_text(encoding="utf-8"))
    if view.get("schema") != "saea-speech-native-runtime-view-v1":
        raise SystemExit(f"runtime view schema is not a speech-native runtime view: {view.get('schema')!r}")
    if receipt.get("schema") != "saea-roster-receipt-v1":
        raise SystemExit(f"roster receipt schema is invalid: {receipt.get('schema')!r}")
    if view["split_identity_hash"] != receipt["split_identity_hash"]:
        raise SystemExit("runtime view and roster receipt disagree on the split identity hash")
    receipt_ids = roster_sample_ids(receipt)
    rows = []
    seconds_total = 0.0
    for item in view["items"]:
        sample_id = item["sample_id"]
        if sample_id not in receipt_ids:
            raise SystemExit(f"runtime view row {sample_id} is not on the roster receipt")
        rel = item["media_relpath"]
        path = (data_root / rel).resolve()
        if not path.is_relative_to(data_root.resolve()):
            raise SystemExit(f"media path escapes the data root: {rel}")
        actual = raw_sha256(path)
        if actual != item["audio_sha256"]:
            raise SystemExit(f"audio bytes differ from the runtime view for {sample_id}")
        info = soundfile.info(str(path))
        if info.samplerate != item["sample_rate_hz"]:
            raise SystemExit(f"sample rate differs from the runtime view for {sample_id}")
        if abs(info.frames / info.samplerate - item["audio_seconds"]) > 0.01:
            raise SystemExit(f"header duration differs from the runtime view by more than 10 ms for {sample_id}")
        seconds_total += info.frames / info.samplerate
        rows.append(
            {
                "id": sample_id,
                "media_relpath": rel,
                "audio_sha256": actual,
                "source_frames": int(info.frames),
                "source_sample_rate_hz": int(info.samplerate),
            }
        )
    if len(rows) != len(receipt_ids) or len(rows) != view["count"]:
        raise SystemExit("row count differs between the runtime view and the roster receipt")
    rows.sort(key=lambda row: row["id"])
    identity = split_identity(view["carrier_lock_key"], [row["id"] for row in rows])
    if identity != view["split_identity_hash"]:
        raise SystemExit("the inventory rows do not reproduce the split identity hash")
    try:
        commit = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    return {
        "schema": SCHEMA,
        "status": "MODEL-FREE SOURCE INPUT; NO ENCODER OR TOKENIZER CONTACT",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/build_speech_query_source_inventory.py",
        "source_commit": commit,
        "carrier_lock_key": view["carrier_lock_key"],
        "split_name": view["split_name"],
        "split_role": view["split_role"],
        "split_identity_hash": identity,
        "dataset_config": {
            "relpath": str(runtime_view.relative_to(source_root)).replace("\\", "/"),
            "sha256": raw_sha256(runtime_view),
            "canonical_runtime_view_sha256": view.get("runtime_view_sha256"),
        },
        "roster_receipt": {
            "relpath": str(roster_receipt.relative_to(source_root)).replace("\\", "/"),
            "sha256": raw_sha256(roster_receipt),
        },
        "roster_sha256": raw_sha256(roster_receipt),
        "count": len(rows),
        "audio_seconds_total": seconds_total,
        "audio_decodes": 0,
        "model_contacts": 0,
        "tokenizer_contacts": 0,
        "network_contacts": 0,
        "rows": rows,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runtime-view", required=True, type=Path)
    parser.add_argument("--roster-receipt", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    source_root = args.source_root.resolve()
    inventory = build(
        args.runtime_view.resolve(), args.roster_receipt.resolve(), args.data_root.resolve(), source_root
    )
    if args.out.exists():
        raise SystemExit(f"refusing to overwrite an existing inventory: {args.out}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(inventory, indent=2, sort_keys=True) + "\n"
    with io.open(args.out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(raw)
    print(f"inventory {args.out}")
    print(f"sha256 {hashlib.sha256(raw.encode('utf-8')).hexdigest()}")
    print(f"rows {inventory['count']} split_identity_hash {inventory['split_identity_hash']}")
    print(f"roster_sha256 {inventory['roster_sha256']}")
    print(f"audio_seconds_total {inventory['audio_seconds_total']:.6f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
