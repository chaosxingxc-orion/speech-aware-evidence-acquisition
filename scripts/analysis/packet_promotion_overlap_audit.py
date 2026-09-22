#!/usr/bin/env python3
"""packet_promotion_overlap_audit.py -- which of a roster's packets are already
promoted, and is the difference provenance or a real conflict?

Item E40. A preprocessing roster drawn months after the packet root was first
populated overlaps earlier rosters: some of its rows are already promoted under
another receipt's name. Whether the driver may promote that roster at all turns
on ONE question per overlapping packet -- is the existing packet's identity the
same one this pass would write, different in exactly ``encoder_receipt_sha256``
(a provenance-only difference over byte-identical evidence: SHAREABLE), or
different in something that changes the evidence (CONFLICTING)?

This driver answers it before anything is written.

STRICTLY READ-ONLY and model-free. It reads a roster document, the promotion
receipts sitting at the packet root, and the packet manifests themselves; it
writes nothing under the packet root, never opens the legacy feature cache,
never reads a media file, and never contacts a model, tokenizer, encoder or
server. Only counts, ids and hashes are printed: no utterance text, no label.

Chunk hashes are re-verified against the packet's OWN files by
``load_speech_feature_packet`` (that is what loading a packet means here), but
a packet's chunks can only be compared against a FRESH encode of the same audio
when a freshly materialized packet is supplied -- ``--fresh-packet-root``. The
promotion path itself always does that comparison; this audit without that flag
answers the identity question alone, and says so in its verdict names.

Usage::

    python scripts/analysis/packet_promotion_overlap_audit.py \\
        --roster configs/dataset/slurp-speech-native-stage3-construction-r01.json \\
        --packet-root /home/chao/feat-cache/slurp-q4km-packets-04ccc72a
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Mapping, Sequence

REPO = Path(__file__).resolve().parent.parent.parent
if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if Path(_pkg.__file__ or "") != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py":
    raise SystemExit("package resolves to %s, not this checkout" % (_pkg.__file__,))

from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    FrozenCoreError, load_speech_feature_packet)

SCHEMA = "saea-packet-promotion-overlap-audit-v1"
DEFAULT_PACKET_ROOT = Path("/home/chao/feat-cache/slurp-q4km-packets-04ccc72a")
DEFAULT_RUNTIME_RECEIPT = REPO / "docs" / "receipts" / "runtime-q4km-preprocess.json"
PROMOTION_GLOB = "*-promotion.json"

# The identity a promotion pass declares, in the order a reader should read it.
IDENTITY_FIELDS = (
    "audio_sha256",
    "encoder_receipt_sha256",
    "decoder_gguf_sha256",
    "mmproj_sha256",
    "position_mode",
    "causal_attention",
)
PROVENANCE_FIELD = "encoder_receipt_sha256"


def canonical_sha256(document: object) -> str:
    """The hash the preprocessing drivers use as ``encoder_receipt_sha256``."""

    return hashlib.sha256(
        json.dumps(document, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def read_json(path: Path) -> Mapping[str, object]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SystemExit("cannot read %s: %s" % (path, error))
    if not isinstance(document, Mapping):
        raise SystemExit("%s is not a JSON object" % path)
    return document


def roster_rows(document: Mapping[str, object], path: Path) -> dict[str, dict[str, str]]:
    """packet_id -> the identity facts the roster itself pins (no labels)."""

    items = document.get("items")
    if not isinstance(items, list) or not items:
        raise SystemExit("%s carries no items list" % path)
    rows: dict[str, dict[str, str]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise SystemExit("roster item %d is not an object" % index)
        sample_id = item.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise SystemExit("roster item %d has no sample_id" % index)
        packet_id = item.get("packet_id")
        if not isinstance(packet_id, str) or not packet_id:
            packet_id = sample_id.replace(":", "/")
        if packet_id in rows:
            raise SystemExit("duplicate roster packet id %r" % packet_id)
        row = {"sample_id": sample_id}
        audio = item.get("audio_sha256")
        if isinstance(audio, str) and audio:
            row["audio_sha256"] = audio
        rows[packet_id] = row
    return rows


def promotion_index(packet_root: Path) -> dict[str, list[str]]:
    """packet_id -> the promotion receipts at the root that already name it."""

    index: dict[str, list[str]] = {}
    for receipt_path in sorted(Path(packet_root).glob(PROMOTION_GLOB)):
        document = read_json(receipt_path)
        packets = document.get("packets")
        if not isinstance(packets, list):
            raise SystemExit("%s carries no packets list" % receipt_path)
        for entry in packets:
            if not isinstance(entry, Mapping):
                raise SystemExit("%s has a malformed packet entry" % receipt_path)
            packet_id = str(entry.get("packet_id"))
            index.setdefault(packet_id, []).append(receipt_path.name)
    return index


def expected_identity(runtime_receipt: Mapping[str, object]) -> dict[str, object]:
    gguf = runtime_receipt.get("gguf_files")
    if not isinstance(gguf, list):
        raise SystemExit("runtime receipt carries no gguf_files list")
    decoder = [e for e in gguf if "mmproj" not in Path(str(e["path"])).name.lower()]
    mmproj = [e for e in gguf if "mmproj" in Path(str(e["path"])).name.lower()]
    if len(decoder) != 1 or len(mmproj) != 1:
        raise SystemExit("runtime receipt must bind exactly one decoder and one mmproj")
    return {
        "encoder_receipt_sha256": canonical_sha256(runtime_receipt),
        "decoder_gguf_sha256": str(decoder[0]["sha256"]),
        "mmproj_sha256": str(mmproj[0]["sha256"]),
        "position_mode": "mrope_1d",
        "causal_attention": True,
    }


def classify(
    *, packet_id: str, packet_root: Path, expected: Mapping[str, object],
    roster_row: Mapping[str, str], fresh_root: Path | None,
) -> dict[str, object]:
    """Load one existing packet read-only and name its difference, if any."""

    try:
        packet = load_speech_feature_packet(packet_root, packet_id)
    except FrozenCoreError as error:
        return {"packet_id": packet_id, "verdict": "unreadable", "detail": str(error)}
    wanted = dict(expected)
    if "audio_sha256" in roster_row:
        wanted["audio_sha256"] = roster_row["audio_sha256"]
    differing = sorted(
        field for field in IDENTITY_FIELDS
        if field in wanted and getattr(packet, field) != wanted[field]
    )
    row: dict[str, object] = {
        "packet_id": packet_id,
        "packet_sha256": packet.packet_sha256,
        "chunk_count": len(packet.chunks),
        "existing_encoder_receipt_sha256": packet.encoder_receipt_sha256,
        "expected_encoder_receipt_sha256": str(wanted[PROVENANCE_FIELD]),
        "differing_identity_fields": differing,
        "compared_identity_fields": sorted(field for field in IDENTITY_FIELDS if field in wanted),
    }
    if not differing:
        row["verdict"] = "identical"
    elif differing == [PROVENANCE_FIELD]:
        row["verdict"] = "shareable"
    else:
        row["verdict"] = "conflicting"
    if fresh_root is not None:
        row.update(_compare_chunks(packet, packet_id, fresh_root, row))
    return row


def _compare_chunks(packet, packet_id: str, fresh_root: Path, row: Mapping[str, object]) -> dict[str, object]:
    """Compare chunk hashes against a FRESH packet of the same id, if supplied."""

    try:
        fresh = load_speech_feature_packet(fresh_root, packet_id)
    except FrozenCoreError as error:
        return {"chunks_verified": False, "chunk_detail": str(error)}
    same = len(fresh.chunks) == len(packet.chunks) and all(
        (left.feature_sha256, left.position_sha256) == (right.feature_sha256, right.position_sha256)
        for left, right in zip(packet.chunks, fresh.chunks)
    )
    result: dict[str, object] = {"chunks_verified": True, "chunks_identical": same}
    if not same:
        result["verdict"] = "conflicting"
    elif row.get("verdict") == "shareable":
        result["verdict"] = "shareable-chunks-verified"
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roster", type=Path, required=True,
                        help="a roster / runtime-view JSON whose items carry sample_id")
    parser.add_argument("--packet-root", type=Path, default=DEFAULT_PACKET_ROOT)
    parser.add_argument("--runtime-receipt", type=Path, default=DEFAULT_RUNTIME_RECEIPT,
                        help="the receipt whose canonical hash this pass would write")
    parser.add_argument("--fresh-packet-root", type=Path, default=None,
                        help="a SEPARATE root holding freshly materialized packets; "
                             "only then can chunk hashes be compared")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    packet_root = args.packet_root.resolve()
    if not packet_root.is_dir():
        raise SystemExit("packet root is unavailable: %s" % packet_root)
    fresh_root = args.fresh_packet_root.resolve() if args.fresh_packet_root else None
    if fresh_root is not None and fresh_root == packet_root:
        raise SystemExit("--fresh-packet-root must differ from --packet-root")
    if args.output is not None and packet_root in args.output.resolve().parents:
        raise SystemExit("this audit never writes under the packet root")
    if not 1 <= args.workers <= 64:
        raise SystemExit("--workers must be in [1, 64]")

    rows = roster_rows(read_json(args.roster), args.roster)
    index = promotion_index(packet_root)
    overlap = sorted(set(rows) & set(index))
    expected = expected_identity(read_json(args.runtime_receipt))

    def one(packet_id: str) -> dict[str, object]:
        record = classify(
            packet_id=packet_id, packet_root=packet_root, expected=expected,
            roster_row=rows[packet_id], fresh_root=fresh_root)
        record["promotion_receipts"] = sorted(index[packet_id])
        return record

    with ThreadPoolExecutor(max_workers=min(args.workers, max(1, len(overlap)))) as pool:
        records = list(pool.map(one, overlap)) if overlap else []

    counts: dict[str, int] = {}
    for record in records:
        counts[str(record["verdict"])] = counts.get(str(record["verdict"]), 0) + 1
    receipts: dict[str, int] = {}
    for record in records:
        for name in record["promotion_receipts"]:
            receipts[name] = receipts.get(name, 0) + 1

    report = {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "execution_profile": "model-free-check",
        "roster": str(args.roster),
        "roster_rows": len(rows),
        "packet_root": str(packet_root),
        "runtime_receipt": str(args.runtime_receipt),
        "expected_encoder_receipt_sha256": expected["encoder_receipt_sha256"],
        "expected_decoder_gguf_sha256": expected["decoder_gguf_sha256"],
        "expected_mmproj_sha256": expected["mmproj_sha256"],
        "promotion_receipts_scanned": len(sorted(packet_root.glob(PROMOTION_GLOB))),
        "packets_promoted_at_root": len(index),
        "overlap_count": len(overlap),
        "fresh_packet_root": str(fresh_root) if fresh_root else None,
        "chunk_comparison": (
            "chunk hashes compared against the supplied fresh packets"
            if fresh_root else
            "identity only: chunk hashes are re-verified against each packet's own "
            "files, and can be compared against a fresh encode only when "
            "--fresh-packet-root supplies one"
        ),
        "verdict_counts": counts,
        "overlap_by_promotion_receipt": dict(sorted(receipts.items())),
        "overlap": records,
    }
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
