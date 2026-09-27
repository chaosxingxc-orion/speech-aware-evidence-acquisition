#!/usr/bin/env python3
"""Derive the SLURP test SAMPLE's label-free preparation inputs from committed bytes alone.

Owner decision 156 of 2026-09-27 (``docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md``,
row 156): the three label-free preparations of ``SLURP-TEST-SAMPLE-3010-V1`` may run ahead of the
dev-admitted composed arm; the milestone reads keep row 151's gate. This tool produces the two
inputs those preparations bind that cannot be copied from the FULL registration of 2026-09-23:

``runtime-view``
    ``configs/dataset/slurp-speech-native-test-sample-3010.json`` -- the
    ``saea-speech-native-runtime-view-v1`` RESTRICTION of the committed FULL view
    ``configs/dataset/slurp-speech-native-test-full.json`` to the 3,010 ids of the committed sample
    roster receipt, which is exactly what that receipt's own ``media_identity`` field says a runtime
    view of the sample would be. The item records are copied value for value from the FULL view;
    the signature fields are recomputed with the FULL builder's own conventions
    (``scripts/build_slurp_test_full_runtime_view.py``: ``source_binding_sha256`` is the canonical
    SHA-256 of the roster receipt, ``runtime_view_sha256`` the canonical SHA-256 of the unsigned
    view). The FULL view's D1 media-supplement triple is carried unchanged: the supplement closes
    over all 13,078 test recordings, a strict superset of the sample, and the gate reader
    (``contracts.gate_media_identity``) looks each sample id up in it.

``inventory``
    The step-2a ``saea-speech-query-source-inventory-v1`` of the speech-query encoding. The FULL
    registration built its inventory with ``scripts/build_speech_query_source_inventory.py``, which
    re-hashes every media file and reads every container header -- that opens test media, which a
    registration may not do. This derivation instead reads the committed runtime view: ``id``,
    ``media_relpath`` and ``audio_sha256`` are copied, and ``source_frames`` is recovered EXACTLY as
    ``audio_seconds x sample_rate_hz`` (every SLURP duration is a whole number of frames; the tool
    refuses a row whose product is not an integer to 1e-6 frames). The document carries no
    timestamp and no commit, so it is byte-reproducible and its SHA-256 is pinned in the committed
    encoding protocol before any contact. Nothing is weakened: ``core.preparation_speech_queries``
    re-hashes every media file and re-reads every header against these rows before the first
    encoder forward, and refuses on any difference.

MODEL-FREE, LABEL-FREE AND MEDIA-FREE: no model, tokenizer, encoder, embedder, scorer, server,
network or GPU is reached, no media byte is opened, and the only roster fields read are
``items[].sample_id`` / ``items[].audio_seconds`` and the receipt's identity fields (the whole
receipt is hashed for ``source_binding_sha256``, as the FULL builder does). The sample roster
receipt carries per-intent AGGREGATES (the stratified draw of owner decision 141); none of them is
copied anywhere by this tool.

Usage (WSL, the shared venv, from the study root)::

    python -B scripts/flights/testsample/derive_test_sample_preparations.py runtime-view --check
    python -B scripts/flights/testsample/derive_test_sample_preparations.py inventory --print-sha256
    python -B scripts/flights/testsample/derive_test_sample_preparations.py inventory \\
        --out "$SPEECHRL_DATA_DIR/coordination/slurp-test-sample-3010-speech-query-source-inventory-v1.json"
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[3]

CARRIER = "slurp"
FULL_VIEW_RELPATH = "configs/dataset/slurp-speech-native-test-full.json"
SAMPLE_VIEW_RELPATH = "configs/dataset/slurp-speech-native-test-sample-3010.json"
SAMPLE_ROSTER_RELPATH = "docs/receipts/rosters/slurp-test-sample-3010-v1.json"
SAMPLE_ROSTER_ID = "SLURP-TEST-SAMPLE-3010-V1"
SAMPLE_SPLIT_IDENTITY = (
    "0164dabf7b30f8e06f830ba28af849cef7459e8c8821cfbea7a56cabb32470f9"
)
SAMPLE_ROWS = 3010
INVENTORY_SCHEMA = "saea-speech-query-source-inventory-v1"
GENERATOR = "scripts/flights/testsample/derive_test_sample_preparations.py"
VIEW_ITEM_KEYS = frozenset(
    {
        "sample_id",
        "media_relpath",
        "audio_sha256",
        "audio_seconds",
        "sample_rate_hz",
        "packet_id",
    }
)
FRAME_TOLERANCE = 1e-6


class DerivationError(RuntimeError):
    """Refuse a derivation whose committed inputs disagree."""


def canonical_sha256(document: object) -> str:
    """The FULL builder's canonical digest (sorted keys, compact separators)."""

    return hashlib.sha256(
        json.dumps(
            document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def render_view(document: Mapping[str, object]) -> bytes:
    """The FULL builder's ``write_json`` bytes."""

    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def render_inventory(document: Mapping[str, object]) -> bytes:
    """``scripts/build_speech_query_source_inventory.py``'s bytes."""

    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def split_identity(ids: Sequence[str]) -> str:
    return hashlib.sha256(
        "\n".join(sorted(f"{CARRIER}/{value}" for value in ids)).encode("utf-8")
    ).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise DerivationError(f"{path} is not a JSON object")
    return document


def build_runtime_view(
    full_view: Mapping[str, object], roster: Mapping[str, object]
) -> dict:
    """Restrict the FULL runtime view to the sample roster's ids."""

    if full_view.get("schema") != "saea-speech-native-runtime-view-v1":
        raise DerivationError(
            "the FULL dataset fragment is not a speech-native runtime view"
        )
    if roster.get("schema") != "saea-roster-receipt-v1":
        raise DerivationError(
            "the sample roster receipt schema is not saea-roster-receipt-v1"
        )
    if roster.get("roster_id") != SAMPLE_ROSTER_ID:
        raise DerivationError(f"roster receipt names {roster.get('roster_id')!r}")
    if (
        roster.get("carrier_lock_key") != CARRIER
        or full_view.get("carrier_lock_key") != CARRIER
    ):
        raise DerivationError(
            "carrier mismatch between the FULL view and the sample roster"
        )
    if not roster.get("split_role") == full_view.get("split_role") == "final-report":
        raise DerivationError(
            "the sample roster and the FULL view must both be final-report"
        )
    roster_seconds = {
        str(item["sample_id"]): float(item["audio_seconds"]) for item in roster["items"]
    }
    if (
        len(roster_seconds) != len(roster["items"])
        or len(roster_seconds) != SAMPLE_ROWS
    ):
        raise DerivationError(
            f"the sample roster must carry {SAMPLE_ROWS} distinct ids, found {len(roster_seconds)}"
        )
    if split_identity(list(roster_seconds)) != roster.get("split_identity_hash"):
        raise DerivationError(
            "the sample roster's ids do not reproduce its split identity hash"
        )
    if roster.get("split_identity_hash") != SAMPLE_SPLIT_IDENTITY:
        raise DerivationError(
            "the sample roster's split identity is not the allowance's"
        )

    items = []
    for item in full_view["items"]:
        if str(item["sample_id"]) not in roster_seconds:
            continue
        if set(item) != VIEW_ITEM_KEYS:
            raise DerivationError(
                f"FULL view item {item.get('sample_id')!r} is not label-free"
            )
        declared = roster_seconds[str(item["sample_id"])]
        if abs(float(item["audio_seconds"]) - declared) > 1e-6:
            raise DerivationError(
                f"audio duration drift for {item['sample_id']!r}: roster {declared} vs "
                f"FULL view {item['audio_seconds']}"
            )
        items.append({key: item[key] for key in sorted(VIEW_ITEM_KEYS)})
    items.sort(key=lambda entry: str(entry["sample_id"]))
    found = {str(entry["sample_id"]) for entry in items}
    if found != set(roster_seconds):
        missing = sorted(set(roster_seconds) - found)[:3]
        raise DerivationError(
            f"sample ids absent from the FULL view (first: {missing})"
        )

    unsigned = {
        "schema": full_view["schema"],
        "study": full_view["study"],
        "status": full_view["status"],
        "carrier_lock_key": CARRIER,
        "split_name": roster["split_name"],
        "split_role": roster["split_role"],
        "seed": roster["seed"],
        "split_identity_hash": roster["split_identity_hash"],
        "source_binding_sha256": canonical_sha256(roster),
        "d1_media_supplement": full_view["d1_media_supplement"],
        "d1_media_supplement_sha256": full_view["d1_media_supplement_sha256"],
        "d1_manifest_sha256": full_view["d1_manifest_sha256"],
        "count": len(items),
        "audio_seconds_total": round(
            sum(float(entry["audio_seconds"]) for entry in items), 9
        ),
        "items": items,
    }
    if (
        abs(
            float(unsigned["audio_seconds_total"])
            - float(roster["audio_seconds_total"])
        )
        > 1e-6
    ):
        raise DerivationError(
            "the restricted view's audio total differs from the roster's"
        )
    return {**unsigned, "runtime_view_sha256": canonical_sha256(unsigned)}


def exact_frames(sample_id: str, audio_seconds: float, sample_rate_hz: int) -> int:
    product = float(audio_seconds) * int(sample_rate_hz)
    frames = round(product)
    if frames <= 0 or abs(product - frames) > FRAME_TOLERANCE:
        raise DerivationError(
            f"{sample_id!r}: {audio_seconds} s x {sample_rate_hz} Hz is not a whole frame count"
        )
    return int(frames)


def build_source_inventory(
    view: Mapping[str, object],
    roster: Mapping[str, object],
    *,
    view_relpath: str,
    view_raw_sha256: str,
    roster_relpath: str,
    roster_raw_sha256: str,
) -> dict:
    """The step-2a source inventory, from the committed runtime view alone."""

    if view["split_identity_hash"] != roster["split_identity_hash"]:
        raise DerivationError(
            "runtime view and roster receipt disagree on the split identity"
        )
    roster_ids = {str(item["sample_id"]) for item in roster["items"]}
    rows = []
    for item in view["items"]:
        sample_id = str(item["sample_id"])
        if sample_id not in roster_ids:
            raise DerivationError(
                f"runtime view row {sample_id} is not on the roster receipt"
            )
        rate = int(item["sample_rate_hz"])
        rows.append(
            {
                "id": sample_id,
                "media_relpath": str(item["media_relpath"]),
                "audio_sha256": str(item["audio_sha256"]),
                "source_frames": exact_frames(
                    sample_id, float(item["audio_seconds"]), rate
                ),
                "source_sample_rate_hz": rate,
            }
        )
    if len(rows) != len(roster_ids) or len(rows) != view["count"]:
        raise DerivationError(
            "row count differs between the runtime view and the roster receipt"
        )
    rows.sort(key=lambda row: row["id"])
    identity = split_identity([row["id"] for row in rows])
    if identity != view["split_identity_hash"]:
        raise DerivationError(
            "the inventory rows do not reproduce the split identity hash"
        )
    return {
        "schema": INVENTORY_SCHEMA,
        "status": "MODEL-FREE SOURCE INPUT; NO ENCODER OR TOKENIZER CONTACT",
        "generator": GENERATOR,
        "derivation": (
            "restriction of the committed runtime view: id, media_relpath and audio_sha256 copied; "
            "source_frames = audio_seconds x sample_rate_hz, exact; no media byte and no container "
            "header was opened to build this file -- core.preparation_speech_queries re-hashes "
            "every media file and re-reads every header against these rows before the first "
            "encoder forward and refuses on any difference"
        ),
        "carrier_lock_key": view["carrier_lock_key"],
        "split_name": view["split_name"],
        "split_role": view["split_role"],
        "split_identity_hash": identity,
        "dataset_config": {
            "relpath": view_relpath,
            "sha256": view_raw_sha256,
            "canonical_runtime_view_sha256": view.get("runtime_view_sha256"),
        },
        "roster_receipt": {"relpath": roster_relpath, "sha256": roster_raw_sha256},
        "roster_sha256": roster_raw_sha256,
        "count": len(rows),
        "audio_seconds_total": sum(
            row["source_frames"] / row["source_sample_rate_hz"] for row in rows
        ),
        "audio_decodes": 0,
        "media_bytes_opened": 0,
        "model_contacts": 0,
        "tokenizer_contacts": 0,
        "network_contacts": 0,
        "rows": rows,
    }


def derive_view_bytes(repo_root: Path) -> bytes:
    full_view = load_json(repo_root / FULL_VIEW_RELPATH)
    roster = load_json(repo_root / SAMPLE_ROSTER_RELPATH)
    return render_view(build_runtime_view(full_view, roster))


def derive_inventory_bytes(repo_root: Path) -> bytes:
    view_path = repo_root / SAMPLE_VIEW_RELPATH
    roster_path = repo_root / SAMPLE_ROSTER_RELPATH
    if derive_view_bytes(repo_root) != view_path.read_bytes():
        raise DerivationError(
            f"{SAMPLE_VIEW_RELPATH} no longer derives from the committed inputs"
        )
    document = build_source_inventory(
        load_json(view_path),
        load_json(roster_path),
        view_relpath=SAMPLE_VIEW_RELPATH,
        view_raw_sha256=raw_sha256(view_path),
        roster_relpath=SAMPLE_ROSTER_RELPATH,
        roster_raw_sha256=raw_sha256(roster_path),
    )
    return render_inventory(document)


def write_create_only(path: Path, raw: bytes) -> str:
    """Write once; an existing file must already hold exactly these bytes."""

    path = Path(path)
    if path.exists():
        if path.read_bytes() != raw:
            raise DerivationError(
                f"{path} exists with different bytes; refusing to change it"
            )
        return "unchanged"
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(path, "xb") as handle:
        handle.write(raw)
    return "written"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    view = sub.add_parser("runtime-view")
    mode = view.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    inventory = sub.add_parser("inventory")
    target = inventory.add_mutually_exclusive_group(required=True)
    target.add_argument("--out", type=Path)
    target.add_argument("--print-sha256", action="store_true")
    inventory.add_argument("--expect-sha256", default=None)
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    try:
        if args.command == "runtime-view":
            raw = derive_view_bytes(repo_root)
            path = repo_root / SAMPLE_VIEW_RELPATH
            if args.write:
                state = (
                    "unchanged"
                    if path.is_file() and path.read_bytes() == raw
                    else "written"
                )
                if state == "written":
                    with io.open(path, "wb") as handle:
                        handle.write(raw)
            else:
                if not path.is_file() or path.read_bytes() != raw:
                    raise DerivationError(
                        f"{SAMPLE_VIEW_RELPATH} differs from its derivation"
                    )
                state = "verified"
            digest = hashlib.sha256(raw).hexdigest()
            print(f"runtime-view {state} {SAMPLE_VIEW_RELPATH} sha256 {digest}")
            return 0
        raw = derive_inventory_bytes(repo_root)
        digest = hashlib.sha256(raw).hexdigest()
        if args.expect_sha256 is not None and digest != args.expect_sha256:
            raise DerivationError(
                f"the derived inventory hashes to {digest}, not the pinned {args.expect_sha256}"
            )
        if args.print_sha256:
            print(f"inventory sha256 {digest} rows {SAMPLE_ROWS} (not written)")
            return 0
        state = write_create_only(args.out, raw)
        print(f"inventory {state} {args.out} sha256 {digest} rows {SAMPLE_ROWS}")
        return 0
    except DerivationError as error:
        print(f"REFUSED: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
