#!/usr/bin/env python3
"""Cut the ESB Earnings-22 test utterances locally and receipt them.

The published "Earnings22" column of the Open ASR Leaderboard is not the
125-file corpus: it is the ESB partition by source file, whose TEST half is
the six calls ``4432298 4450488 4470290 4479741 4483338 4485244``, cut at
punctuation boundaries into short utterances. The segment boundaries live in
``sanchit-gandhi/earnings22_split`` (split ``test``); this study already owns
the six MP3s under the locked ``earnings22-original`` asset, so the
utterances are cut LOCALLY from those frozen bytes rather than downloaded.

What this script does, once, with zero model contact:

1. reads the hash-pinned segment table (metadata columns only -- the
   extractor never materializes the parquet ``audio`` column) and refuses
   any drift against the segment-table receipt;
2. decodes each of the six parent MP3s exactly once through
   ``reproduction.obs_loop.decode_parent_pcm`` -- the SAME librosa 16 kHz
   mono decode every earlier slice in this repository used (ffmpeg is absent
   and must stay absent, so a decoder change would move the bytes);
3. writes one 16 kHz mono WAV per utterance through
   ``reproduction.obs_audio.write_wav_bytes`` -- the same deterministic
   stdlib writer the OBS slicer uses -- under
   ``$SPEECHRL_DATA_DIR/derived/e22-esb-utterances/<version>/<call>/<id>.wav``;
4. emits a flight roster receipt carrying identifiers, media paths and
   MEASURED media identity only (no reference text: the roster is read by
   the flight entry point, which is a runtime path), and
5. emits a SEPARATE derived reference layer plus its own receipt. The
   reference file is written under the controlled data root, never into the
   locked carrier tree and never into Git; only its SHA-256 is committed.
   ``reproduction.esb_reference`` re-verifies that hash before a scorer may
   read a single reference word.

Two populations, one builder
----------------------------

``--profile test`` (the default) is the sealed 2026-09-04 six-call ESB TEST
subset; every value it produces is unchanged. ``--profile dev10`` cuts the ESB
**train**-split utterances of this study's own Earnings-22 ``dev`` subset10 --
the ten calls ``docs/receipts/splits.json`` already assigns that role -- for the
2026-09-05 prompt A/B experiment. Same decode, same writer, same receipts, a
different derived version directory (``dev-v1``) so the two populations' media
never share a root.

Usage::

    python scripts/build_e22_esb_utterance_roster.py --write
    python scripts/build_e22_esb_utterance_roster.py --profile dev10 --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

# ``reproduction.obs_loop`` is imported INSIDE the worker (see ``_cut_one_call``):
# ``core.policies`` imports it at ``core`` package import time, so importing it
# first from a bare script is a circular import. Importing the package the normal
# way round -- ``speech_aware_evidence_acquisition.core`` first, then the submodule --
# avoids it, and doing it in the worker keeps librosa out of the parent process.

CARRIER = "earnings22-original"
CARRIER_SUBDIR = "datasets/earnings21-22/earnings22"
ESB_TEST_CALLS = ("4432298", "4450488", "4470290", "4479741", "4483338", "4485244")
SAMPLE_RATE_HZ = 16000
VERSION = "v1"
UTTERANCE_SUBDIR = f"derived/e22-esb-utterances/{VERSION}"
SEGMENT_TABLE_SUBDIR = "derived/e22-esb-segment-table"
REFERENCE_RELPATH = f"{SEGMENT_TABLE_SUBDIR}/e22-esb-test-references.jsonl"

CHECK_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-e22-esb-shortform-alignment-400-v1"
)
DEFAULT_SEGMENT_RECEIPT = CHECK_DIR / "segment-table" / "segment-table-receipt.json"
DEFAULT_ROSTER_OUTPUT = CHECK_DIR / "roster" / "flight-roster-receipt.json"
DEFAULT_REFERENCE_OUTPUT = CHECK_DIR / "reference-layer" / "reference-layer-receipt.json"

ROSTER_SCHEMA = "saea-e22-esb-utterance-roster-receipt-v1"
REFERENCE_SCHEMA = "saea-e22-esb-reference-layer-receipt-v1"

# The ten Earnings-22 calls docs/receipts/splits.json assigns this study's own
# ``dev`` role. Their ESB utterance boundaries and cleaned reference sentences
# come from the TRAIN half of the same pinned segment table.
DEV10_CALLS = (
    "4453225",
    "4469088",
    "4470684",
    "4474506",
    "4479944",
    "4481952",
    "4482383",
    "4482613",
    "4483937",
    "4485192",
)
DEV10_VERSION = "dev-v1"
DEV10_UTTERANCE_SUBDIR = f"derived/e22-esb-utterances/{DEV10_VERSION}"
DEV10_REFERENCE_RELPATH = f"{SEGMENT_TABLE_SUBDIR}/e22-esb-dev10-references.jsonl"
DEV10_CHECK_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-05-e22-dev-esb-prompt-ab-v1"
)

PROFILES: dict[str, dict[str, object]] = {
    "test": {
        "calls": ESB_TEST_CALLS,
        "version": VERSION,
        "utterance_subdir": UTTERANCE_SUBDIR,
        "reference_relpath": REFERENCE_RELPATH,
        "split_name": "E22-ESB-TEST-UTTERANCES-2735",
        "segment_receipt": DEFAULT_SEGMENT_RECEIPT,
        "roster_output": DEFAULT_ROSTER_OUTPUT,
        "reference_output": DEFAULT_REFERENCE_OUTPUT,
        "upstream_split": "test",
        "split_role_basis": (
            "The owner decision of 2026-09-04 re-designates the six ESB test calls "
            "calibration-exposed after this one read. contracts.plan.STAGE2_SPLIT_ROLES "
            "carries only 'discovery' and 'dev'; 'dev' is the role whose semantics match "
            "calibration-exposed (usable for calibration, never for final reporting), and "
            "earnings22-original already carries this study's 'dev' role for its subset10. "
            "The 109 calls that remain confirmatory are not named, loaded or read."
        ),
    },
    "dev10": {
        "calls": DEV10_CALLS,
        "version": DEV10_VERSION,
        "utterance_subdir": DEV10_UTTERANCE_SUBDIR,
        "reference_relpath": DEV10_REFERENCE_RELPATH,
        "split_name": "E22-ESB-DEV10-UTTERANCES",
        "segment_receipt": DEV10_CHECK_DIR / "segment-table" / "segment-table-receipt.json",
        "roster_output": DEV10_CHECK_DIR / "roster" / "flight-roster-receipt.json",
        "reference_output": DEV10_CHECK_DIR / "reference-layer" / "reference-layer-receipt.json",
        "upstream_split": "train",
        "split_role_basis": (
            "These ten calls ARE this study's registered earnings22-original dev "
            "subset10 (docs/receipts/splits.json, split 'dev', identity "
            "89b178d6b1ef46d9ca820ae54349e3d2099c60cde6d6b753ef9f66137c310028). No owner "
            "allowance is needed and none is claimed: dev is the split this study may "
            "optimize on. No confirmatory call is named, loaded, decoded or scored, and "
            "the six ESB test calls this study calibrated on stay a separate population."
        ),
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(document: object) -> str:
    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_object(path: Path, label: str) -> Mapping[str, Any]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SystemExit(f"cannot read {label}: {error}")
    if not isinstance(document, Mapping):
        raise SystemExit(f"{label} must be a JSON object")
    return document


def load_segments(
    data_root: Path,
    segment_receipt: Mapping[str, Any],
    calls: Sequence[str] = ESB_TEST_CALLS,
) -> list[dict[str, Any]]:
    """The hash-pinned segment table, verified against its own receipt."""

    relpath = str(segment_receipt["extracted_table"]["relpath"])
    path = Path(data_root) / relpath
    measured = sha256_file(path)
    if measured != segment_receipt["extracted_table"]["sha256"]:
        raise SystemExit(
            f"segment table {path} hashes to {measured}, not the receipt's "
            f"{segment_receipt['extracted_table']['sha256']}"
        )
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != int(segment_receipt["extracted_table"]["rows"]):
        raise SystemExit("segment table row count disagrees with its receipt")
    seen: set[str] = set()
    for row in rows:
        if set(row) != {"source_id", "segment_id", "sentence", "start_ts", "end_ts", "id"}:
            raise SystemExit(f"segment row carries unexpected columns: {sorted(row)}")
        if row["source_id"] not in tuple(calls):
            raise SystemExit(
                f"segment row names a call this profile does not pin: {row['source_id']!r}"
            )
        if row["id"] != f"{row['source_id']}-{row['segment_id']}":
            raise SystemExit(f"segment id is not <source>-<segment>: {row['id']!r}")
        if row["id"] in seen:
            raise SystemExit(f"duplicate segment id {row['id']!r}")
        seen.add(row["id"])
        if not isinstance(row["sentence"], str) or not row["sentence"].strip():
            raise SystemExit(f"segment {row['id']!r} has an empty reference sentence")
        if float(row["end_ts"]) <= float(row["start_ts"]):
            raise SystemExit(f"segment {row['id']!r} has a non-positive span")
    return rows


def _cut_one_call(job: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Decode one parent call once and write every one of its utterances."""

    import speech_aware_evidence_acquisition.core as _core  # noqa: F401, PLC0415

    from speech_aware_evidence_acquisition.reproduction.obs_audio import (  # noqa: PLC0415
        write_wav_bytes,
    )
    from speech_aware_evidence_acquisition.reproduction.obs_loop import (  # noqa: PLC0415
        decode_parent_pcm,
    )

    parent_path = Path(job["parent_path"])
    out_dir = Path(job["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    pcm = decode_parent_pcm(parent_path, SAMPLE_RATE_HZ)
    frames = len(pcm)
    if frames <= 0:
        raise RuntimeError(f"decoded zero samples from {parent_path}")
    decoded_seconds = frames / SAMPLE_RATE_HZ
    parent_sha256 = sha256_file(parent_path)
    entries: list[dict[str, Any]] = []
    for row in job["rows"]:
        start = float(row["start_ts"])
        end = float(row["end_ts"])
        first = max(0, int(round(start * SAMPLE_RATE_HZ)))
        last = min(frames, int(round(end * SAMPLE_RATE_HZ)))
        clamped = last < int(round(end * SAMPLE_RATE_HZ))
        if last <= first:
            raise RuntimeError(
                f"utterance {row['id']!r} is empty after clamping to the decoded "
                f"parent ({decoded_seconds:.3f} s): [{start}, {end})"
            )
        payload = write_wav_bytes(pcm[first:last], SAMPLE_RATE_HZ)
        target = out_dir / f"{row['id']}.wav"
        target.write_bytes(payload)
        entries.append(
            {
                "sample_id": row["id"],
                "parent_sample_id": row["source_id"],
                "parent_media_relpath": job["parent_relpath"],
                "parent_sha256": parent_sha256,
                "parent_decoded_seconds": round(decoded_seconds, 9),
                "media_relpath": job["out_relpath"] + f"/{row['id']}.wav",
                "audio_sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
                "audio_seconds": round((last - first) / SAMPLE_RATE_HZ, 9),
                "sample_rate_hz": SAMPLE_RATE_HZ,
                "segment_start_seconds": start,
                "segment_end_seconds": end,
                "end_clamped_to_decoded_parent": clamped,
            }
        )
    return entries


def build(
    *,
    data_root: Path,
    segment_receipt_path: Path,
    workers: int,
    profile: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    if profile is None:
        profile = PROFILES["test"]
    calls = tuple(profile["calls"])
    utterance_subdir = str(profile["utterance_subdir"])
    segment_receipt = _load_object(segment_receipt_path, "segment-table receipt")
    rows = load_segments(data_root, segment_receipt, calls)
    root = Path(data_root)
    jobs = []
    for call in calls:
        parent_relpath = f"{CARRIER_SUBDIR}/media/{call}.mp3"
        parent_path = root / parent_relpath
        if not parent_path.is_file():
            raise SystemExit(f"parent media is missing: {parent_path}")
        out_relpath = f"{utterance_subdir}/{call}"
        jobs.append(
            {
                "parent_path": str(parent_path),
                "parent_relpath": parent_relpath,
                "out_dir": str(root / out_relpath),
                "out_relpath": out_relpath,
                "rows": [row for row in rows if row["source_id"] == call],
            }
        )
    entries: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=max(1, min(workers, len(jobs)))) as pool:
        for result in pool.map(_cut_one_call, jobs):
            entries.extend(result)
    entries.sort(key=lambda entry: entry["sample_id"])
    if len(entries) != len(rows):
        raise SystemExit("cut utterance count disagrees with the segment table")

    total_seconds = sum(float(entry["audio_seconds"]) for entry in entries)
    per_call = {
        call: {
            "utterances": sum(1 for e in entries if e["parent_sample_id"] == call),
            "audio_seconds": round(
                sum(float(e["audio_seconds"]) for e in entries if e["parent_sample_id"] == call), 6
            ),
        }
        for call in calls
    }
    roster = {
        "schema": ROSTER_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "carrier": CARRIER,
        "split_name": str(profile["split_name"]),
        "split_role": "dev",
        "split_role_basis": str(profile["split_role_basis"]),
        "version": str(profile["version"]),
        "source_segment_table": {
            "receipt": str(segment_receipt_path.relative_to(REPO)).replace("\\", "/"),
            "receipt_sha256": sha256_file(segment_receipt_path),
        },
        "sample_rate_hz": SAMPLE_RATE_HZ,
        "decoder": (
            "reproduction.obs_loop.decode_parent_pcm -> librosa.load(sr=16000, mono=True) "
            "then int16; ffmpeg is absent by design and was not used"
        ),
        "writer": "reproduction.obs_audio.write_wav_bytes (stdlib wave, 44-byte header)",
        "count": len(entries),
        "audio_seconds_total": round(total_seconds, 6),
        "audio_seconds_longest_item": round(
            max(float(entry["audio_seconds"]) for entry in entries), 6
        ),
        "audio_seconds_shortest_item": round(
            min(float(entry["audio_seconds"]) for entry in entries), 6
        ),
        "clamped_to_decoded_parent": sorted(
            entry["sample_id"] for entry in entries if entry["end_clamped_to_decoded_parent"]
        ),
        "per_call": per_call,
        "ids_sha256": hashlib.sha256(
            "\n".join(entry["sample_id"] for entry in entries).encode("utf-8")
        ).hexdigest(),
        "items": entries,
    }
    roster["items_sha256"] = canonical_sha256(entries)

    reference_rows = [
        {"sample_id": row["id"], "sentence": row["sentence"]}
        for row in sorted(rows, key=lambda r: r["id"])
    ]
    reference_payload = (
        "\n".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) for row in reference_rows
        )
        + "\n"
    )
    reference = {
        "schema": REFERENCE_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "carrier": CARRIER,
        "split_name": str(profile["split_name"]),
        "relpath": str(profile["reference_relpath"]),
        "sha256": hashlib.sha256(reference_payload.encode("utf-8")).hexdigest(),
        "rows": len(reference_rows),
        "reference_words_whitespace": sum(
            len(row["sentence"].split()) for row in reference_rows
        ),
        "source": (
            "the 'sentence' column of sanchit-gandhi/earnings22_split split "
            f"{str(profile['upstream_split'])!r}, verbatim -- the same field the "
            "leaderboard scores its 'text' against"
        ),
        "source_segment_table_receipt_sha256": sha256_file(segment_receipt_path),
        "boundary": (
            "RUNTIME-FORBIDDEN. These bytes live under the controlled data root, never in "
            "Git and never inside the locked carrier tree; only this receipt's SHA-256 is "
            "committed. reproduction.esb_reference re-verifies that hash before any scorer "
            "reads a reference word, and no runtime path resolves this file at all."
        ),
    }
    return roster, reference, reference_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="test")
    parser.add_argument("--segment-receipt", type=Path, default=None)
    parser.add_argument("--roster-output", type=Path, default=None)
    parser.add_argument("--reference-output", type=Path, default=None)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    profile = PROFILES[args.profile]
    segment_receipt = args.segment_receipt or profile["segment_receipt"]
    roster_output = Path(args.roster_output or profile["roster_output"])
    reference_output = Path(args.reference_output or profile["reference_output"])
    root = args.data_root
    if root is None:
        value = os.environ.get("SPEECHRL_DATA_DIR")
        if not value:
            raise SystemExit("--data-root or SPEECHRL_DATA_DIR is required")
        root = Path(value)
    roster, reference, reference_rows = build(
        data_root=root,
        segment_receipt_path=Path(segment_receipt),
        workers=args.workers,
        profile=profile,
    )
    if args.write:
        reference_path = Path(root) / reference["relpath"]
        reference_path.parent.mkdir(parents=True, exist_ok=True)
        payload = (
            "\n".join(
                json.dumps(row, ensure_ascii=False, sort_keys=True) for row in reference_rows
            )
            + "\n"
        )
        reference_path.write_text(payload, encoding="utf-8", newline="\n")
        for path, document in (
            (roster_output, roster),
            (reference_output, reference),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
    print(
        json.dumps(
            {
                "count": roster["count"],
                "audio_seconds_total": roster["audio_seconds_total"],
                "audio_seconds_longest_item": roster["audio_seconds_longest_item"],
                "audio_seconds_shortest_item": roster["audio_seconds_shortest_item"],
                "clamped_to_decoded_parent": roster["clamped_to_decoded_parent"],
                "ids_sha256": roster["ids_sha256"],
                "items_sha256": roster["items_sha256"],
                "per_call": roster["per_call"],
                "reference_rows": reference["rows"],
                "reference_sha256": reference["sha256"],
                "reference_words_whitespace": reference["reference_words_whitespace"],
                "profile": args.profile,
                "reference_output": str(reference_output),
                "reference_output_sha256": (
                    sha256_file(reference_output) if args.write else canonical_sha256(reference)
                ),
                "roster_output": str(roster_output),
                "roster_output_sha256": (
                    sha256_file(roster_output)
                    if args.write
                    else canonical_sha256(roster)
                ),
                "speech_seconds_ceil": math.ceil(roster["audio_seconds_total"]),
                "written": args.write,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
