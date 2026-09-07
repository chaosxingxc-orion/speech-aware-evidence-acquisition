#!/usr/bin/env python3
"""Build the three Earnings-22 dev1500 probe MEDIA VARIANTS (model-free, CPU only).

Exposure row ``SAEA-SN-MF-E22-DEV1500-ENCODING-VARIANTS-V1``
(``model-free-check``), registered before the first byte was written.

The variants, and the single rule they share
--------------------------------------------

Each is a deterministic transformation of the **sealed ``dev-v1`` WAV bytes** of
the registered 1,500-row roster ``E22-DEV-ESB-1500-V1``. **No parent MP3 is
opened and no decoder runs**: librosa is never called, ffmpeg stays absent, and
the parent decode cannot drift between the sealed population and a variant.
Every source file is re-hashed against the committed D1 media supplement before
it is read, and every written file is re-read and re-hashed off disk before it
is recorded.

``tail-silence-2s`` (``@ts2``)
    Exactly 2.0 s = 32,000 zero samples appended. The frame residue
    ``(n_samples // 160) % 100`` is unchanged (200 whole mel frames are added),
    so the encoder's zero-pad block keeps its size and simply stops abutting the
    speech.

``pad-30s`` (``@p30``)
    Zero samples appended up to exactly 30.0 s = 480,000 samples. **A clip
    already at or past 30.0 s is copied byte-identical** and counted: no clip is
    ever truncated, because truncating speech would be a second factor.

``boundary-exact`` (``@bx1``)
    Section 1.1 of ``docs/readiness/2026-09-06-e22-dev-boundary-exact-v1-
    preregistration.md``, restricted to these 1,500 rows: the midpoint of the
    overlap, and only of the overlap. Because that rule is strictly
    SUBTRACTIVE -- every sample of a re-cut clip is inside the old clip for the
    same segment -- it is a SLICE of the sealed clip, exact to the sample, and
    needs no second decode. The neighbours come from the full published order of
    each call (all 6,038 dev10 segments), not from the drawn subset.

    The media root here is ``dev1500-bx-v1``, NOT the ``dev-bx-v1`` root that
    preregistration reserved for a full 6,038-row build; the ``@bx1`` id suffix
    is kept verbatim so a later full build shares the identity convention.

The segment table is read for ``source_id`` / ``start_ts`` / ``end_ts`` only:
the gold ``sentence`` column is projected away at load and never reaches a
document, a receipt or a log line.

Usage (WSL2)::

    python scripts/build_e22_dev1500_media_variants.py --variant tail-silence-2s
    python scripts/build_e22_dev1500_media_variants.py --variant pad-30s --write
    python scripts/build_e22_dev1500_media_variants.py --variant all --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import wave
from array import array
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import speech_aware_evidence_acquisition.core as _core  # noqa: E402, F401

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.analysis.e22_error_taxonomy import (  # noqa: E402
    load_segment_table,
)
from speech_aware_evidence_acquisition.analysis.e22_short_clip_encoding import (  # noqa: E402
    QWEN3A,
    describe_clip,
)
from speech_aware_evidence_acquisition.core.roster import (  # noqa: E402
    EVALUATION_ROSTER_ROLE,
    RosterItem,
    canonical_receipt_bytes,
    freeze_roster,
    write_roster,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.obs_audio import (  # noqa: E402
    write_wav_bytes,
)

CARRIER = "earnings22-original"
SAMPLE_RATE_HZ = QWEN3A.sample_rate_hz
ROSTER_SCHEMA = "saea-e22-esb-utterance-roster-receipt-v1"
SUPPLEMENT_SCHEMA = "saea-d1-media-supplement-v1"
PER_CALL = 150
#: Freezing the ALREADY drawn ids, not drawing again: the candidate pool is
#: exactly 150 per call, so ``per_stratum=150`` selects all of them and the seed
#: cannot change the membership. It is recorded for reproducibility only.
FREEZE_SEED = 20260907

SOURCE_VIEW_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-06-e22-dev-esb-1500-v1/roster/flight-roster-receipt.json"
)
SOURCE_VIEW_SHA256 = "fe9528be3ad62c27b95da61e7397fda5e19c0fe711fda07db6731c2d6fcccf9f"
SOURCE_SUPPLEMENT_RELPATH = "docs/receipts/artifacts/d1-e22-esb-dev1500-utterances.json"
SOURCE_SUPPLEMENT_SHA256 = (
    "6a3d247208ab027e76b742b35cd4f84bc916f1db05d55444e8e040d05f2ca19f"
)

OUT_ROOT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-07-e22-dev1500-encoding-variants"
)

VARIANTS: dict[str, dict[str, Any]] = {
    "tail-silence-2s": {
        "suffix": "ts2",
        "subdir": "derived/e22-esb-utterances/dev1500-tail2s-v1",
        "roster_id": "E22-DEV-ESB-1500-TAIL2S-V1",
        "split_name": "E22-ESB-DEV1500-TAIL2S-UTTERANCES",
        "roster_receipt": "docs/receipts/rosters/e22-dev-esb-1500-tail2s-v1.json",
        "supplement": "docs/receipts/artifacts/d1-e22-esb-dev1500-tail2s.json",
        "rule": (
            "exactly 2.0 s (32,000 zero samples) appended to the sealed dev-v1 "
            "clip; nothing is removed and nothing is re-decoded"
        ),
    },
    "pad-30s": {
        "suffix": "p30",
        "subdir": "derived/e22-esb-utterances/dev1500-pad30s-v1",
        "roster_id": "E22-DEV-ESB-1500-PAD30S-V1",
        "split_name": "E22-ESB-DEV1500-PAD30S-UTTERANCES",
        "roster_receipt": "docs/receipts/rosters/e22-dev-esb-1500-pad30s-v1.json",
        "supplement": "docs/receipts/artifacts/d1-e22-esb-dev1500-pad30s.json",
        "rule": (
            "zero samples appended up to exactly 480,000 (30.0 s); a clip already "
            "at or past 30.0 s is copied byte-identical and is NEVER truncated"
        ),
    },
    "boundary-exact": {
        "suffix": "bx1",
        "subdir": "derived/e22-esb-utterances/dev1500-bx-v1",
        "roster_id": "E22-DEV-ESB-1500-BX-V1",
        "split_name": "E22-ESB-DEV1500-BX-UTTERANCES",
        "roster_receipt": "docs/receipts/rosters/e22-dev-esb-1500-bx-v1.json",
        "supplement": "docs/receipts/artifacts/d1-e22-esb-dev1500-bx.json",
        "rule": (
            "the midpoint-of-overlap re-cut of section 1.1 of the 2026-09-06 "
            "boundary-exact preregistration, applied as a strictly subtractive "
            "SLICE of the sealed dev-v1 clip"
        ),
    },
}

TAIL_SILENCE_SAMPLES = 2 * SAMPLE_RATE_HZ
PAD30_TARGET_SAMPLES = 30 * SAMPLE_RATE_HZ


class BuildError(RuntimeError):
    """An input drifted, a property failed, or a written byte did not reproduce."""


def canonical_sha256(document: object) -> str:
    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def ids_sha256(ids: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_pinned(relpath: str, expected: str, label: str) -> Mapping[str, Any]:
    path = REPO / relpath
    measured = sha256_file(path)
    if measured != expected:
        raise BuildError(
            f"{label} identity drift: pinned {expected[:12]}..., {path} now hashes "
            f"to {measured[:12]}..."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def read_clip(path: Path) -> array:
    """The sealed clip's int16 samples. 16 kHz mono is asserted, not assumed."""

    with wave.open(str(path), "rb") as handle:
        if (handle.getframerate(), handle.getnchannels(), handle.getsampwidth()) != (
            SAMPLE_RATE_HZ,
            1,
            2,
        ):
            raise BuildError(f"{path} is not 16 kHz mono int16")
        payload = handle.readframes(handle.getnframes())
    return array("h", payload)


# ---------------------------------------------------------------------------
# The boundary-exact rule (preregistration section 1.1), and its properties
# ---------------------------------------------------------------------------


def _segment_index(sample_id: str) -> int:
    return int(sample_id.rsplit("-", 1)[1])


def boundary_exact_spans(
    segments: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, tuple[float, float]], dict[str, Any]]:
    """``{sample_id -> (start', end')}`` plus the properties, asserted not assumed.

    ``start'_i = max(start_i, (end_{i-1} + start_i)/2)`` for ``i > 0`` and
    ``end'_i = min(end_i, (end_i + start_{i+1})/2)`` for ``i < n-1``; the first
    and last segment of a call keep their outer boundary. A POSITIVE gap is
    never closed because of the ``max`` / ``min``.
    """

    by_call: dict[str, list[str]] = {}
    for sample_id, row in segments.items():
        by_call.setdefault(str(row["source_id"]), []).append(sample_id)

    spans: dict[str, tuple[float, float]] = {}
    overlapping_pairs_before = 0
    overlapping_pairs_after = 0
    gaps_closed = 0
    for call in sorted(by_call):
        ordered = sorted(by_call[call], key=_segment_index)
        starts = [float(segments[sid]["start_ts"]) for sid in ordered]
        ends = [float(segments[sid]["end_ts"]) for sid in ordered]
        if any(starts[i] > starts[i + 1] for i in range(len(starts) - 1)):
            raise BuildError(f"call {call}: segment order is not by start_ts")
        for index, sample_id in enumerate(ordered):
            start = starts[index]
            end = ends[index]
            if index > 0:
                start = max(start, (ends[index - 1] + starts[index]) / 2.0)
            if index < len(ordered) - 1:
                end = min(end, (ends[index] + starts[index + 1]) / 2.0)
            if end <= start:
                raise BuildError(f"{sample_id}: re-cut span is empty")
            spans[sample_id] = (start, end)
        for index in range(len(ordered) - 1):
            if starts[index + 1] < ends[index]:
                overlapping_pairs_before += 1
            else:
                if spans[ordered[index]][1] != ends[index]:
                    gaps_closed += 1
            if spans[ordered[index + 1]][0] < spans[ordered[index]][1]:
                overlapping_pairs_after += 1
    if overlapping_pairs_after:
        raise BuildError(
            f"{overlapping_pairs_after} adjacent pairs still overlap after the re-cut"
        )
    if gaps_closed:
        raise BuildError(f"{gaps_closed} positive gaps were closed by the re-cut")
    return spans, {
        "calls": len(by_call),
        "segments": len(spans),
        "overlapping_pairs_before": overlapping_pairs_before,
        "overlapping_pairs_after": 0,
        "positive_gaps_closed": 0,
    }


def boundary_exact_slice(
    item: Mapping[str, Any], span: tuple[float, float], clip_len: int
) -> tuple[int, int]:
    """Offsets into the SEALED clip that reproduce a re-cut of the parent.

    The original cut is ``[first, last)`` with ``first = max(0, round(start*sr))``
    and ``last = min(parent_frames, round(end*sr))``. For ``start' >= start`` and
    ``end' <= end`` the new absolute cut is ``[max(0, round(start'*sr)),
    min(parent_frames, round(end'*sr)))``, and since ``round(end'*sr) <=
    round(end*sr)`` that upper bound equals ``min(last, round(end'*sr))``
    whether or not the original was clamped to the decoded parent. Both offsets
    are therefore computable from the sealed clip alone.
    """

    start = float(item["segment_start_seconds"])
    new_start, new_end = span
    if new_start < start - 1e-9 or new_end > float(item["segment_end_seconds"]) + 1e-9:
        raise BuildError(f"{item['sample_id']}: the re-cut is not subtractive")
    first = max(0, int(round(start * SAMPLE_RATE_HZ)))
    offset_start = max(0, int(round(new_start * SAMPLE_RATE_HZ))) - first
    offset_end = min(clip_len, int(round(new_end * SAMPLE_RATE_HZ)) - first)
    if offset_start < 0 or offset_end > clip_len or offset_end <= offset_start:
        raise BuildError(
            f"{item['sample_id']}: bad slice [{offset_start}, {offset_end}) of "
            f"{clip_len} samples"
        )
    return offset_start, offset_end


# ---------------------------------------------------------------------------
# The build
# ---------------------------------------------------------------------------


def transform(
    variant: str,
    samples: array,
    item: Mapping[str, Any],
    spans: Mapping[str, tuple[float, float]] | None,
) -> array:
    if variant == "tail-silence-2s":
        return samples + array("h", bytes(2 * TAIL_SILENCE_SAMPLES))
    if variant == "pad-30s":
        missing = PAD30_TARGET_SAMPLES - len(samples)
        if missing <= 0:
            return samples
        return samples + array("h", bytes(2 * missing))
    if variant == "boundary-exact":
        assert spans is not None
        key = str(item["sample_id"])
        first, last = boundary_exact_slice(item, spans[key], len(samples))
        return samples[first:last]
    raise BuildError(f"unknown variant {variant!r}")


def build_one(
    variant: str,
    item: Mapping[str, Any],
    source_digest: str,
    spans: Mapping[str, tuple[float, float]] | None,
    root: Path,
    *,
    write: bool,
) -> dict[str, Any]:
    spec = VARIANTS[variant]
    source_path = root / str(item["media_relpath"])
    measured = sha256_file(source_path)
    if measured != source_digest:
        raise BuildError(
            f"source media drift on {item['sample_id']}: supplement records "
            f"{source_digest[:12]}..., disk hashes to {measured[:12]}..."
        )
    samples = read_clip(source_path)
    if len(samples) != int(round(float(item["audio_seconds"]) * SAMPLE_RATE_HZ)):
        raise BuildError(f"{item['sample_id']}: sealed clip length disagrees with roster")
    produced = transform(variant, samples, item, spans)
    if len(produced) <= 0:
        raise BuildError(f"{item['sample_id']}: variant clip is empty")
    payload = write_wav_bytes(produced, SAMPLE_RATE_HZ)
    # Determinism is checked rather than assumed: the same inputs are pushed
    # through the same writer twice and the bytes must agree.
    if write_wav_bytes(transform(variant, samples, item, spans), SAMPLE_RATE_HZ) != payload:
        raise BuildError(f"{item['sample_id']}: the writer is not deterministic")

    new_id = f"{item['sample_id']}@{spec['suffix']}"
    relpath = f"{spec['subdir']}/{item['parent_sample_id']}/{new_id}.wav"
    target = root / relpath
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        on_disk = sha256_file(target)
        if on_disk != hashlib.sha256(payload).hexdigest():
            raise BuildError(f"{new_id}: written bytes do not match the payload")

    encoding = describe_clip(len(produced))
    return {
        "sample_id": new_id,
        "published_segment_id": str(item["sample_id"]),
        "parent_sample_id": str(item["parent_sample_id"]),
        "parent_media_relpath": str(item["parent_media_relpath"]),
        "parent_sha256": str(item["parent_sha256"]),
        "parent_decoded_seconds": item["parent_decoded_seconds"],
        "source_media_relpath": str(item["media_relpath"]),
        "source_audio_sha256": source_digest,
        "source_audio_seconds": float(item["audio_seconds"]),
        "media_relpath": relpath,
        "audio_sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "audio_seconds": round(len(produced) / SAMPLE_RATE_HZ, 9),
        "n_samples": len(produced),
        "sample_rate_hz": SAMPLE_RATE_HZ,
        "segment_start_seconds": item["segment_start_seconds"],
        "segment_end_seconds": item["segment_end_seconds"],
        "end_clamped_to_decoded_parent": bool(item["end_clamped_to_decoded_parent"]),
        "samples_added": max(0, len(produced) - len(samples)),
        "samples_removed": max(0, len(samples) - len(produced)),
        "unchanged": len(produced) == len(samples) and variant == "pad-30s",
        "audio_tokens": encoding.llamacpp_tokens,
        "encoder_windows": len(encoding.windows),
        "zero_pad_frames": encoding.zero_pad_frames,
    }


def probe_view(
    variant: str, source: Mapping[str, Any], entries: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """The ``saea-e22-esb-utterance-roster-receipt-v1`` shape a flight hydrates."""

    spec = VARIANTS[variant]
    ids = [str(entry["sample_id"]) for entry in entries]
    if ids != sorted(ids):
        raise BuildError("the variant items are not in sample-id order")
    calls = sorted({str(entry["parent_sample_id"]) for entry in entries})
    view: dict[str, Any] = {
        "schema": ROSTER_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "carrier": CARRIER,
        "split_name": spec["split_name"],
        "split_role": "dev",
        "split_role_basis": (
            "The SAME 1,500 published segments the sealed 2026-09-05 arm A already "
            "read, re-encoded by one deterministic rule from the sealed dev-v1 bytes. "
            "No owner allowance is involved and none is claimed: dev is the split this "
            "study may optimize on. No confirmatory call is named, loaded, decoded or "
            "scored, and the six calibration-exposed ESB test calls stay a separate "
            "population with a separate roster, reference layer and derived media root."
        ),
        "version": str(source["version"]),
        "source_segment_table": dict(source["source_segment_table"]),
        "derived_from": {
            "roster_receipt": SOURCE_VIEW_RELPATH,
            "roster_receipt_sha256": SOURCE_VIEW_SHA256,
            "d1_media_supplement": SOURCE_SUPPLEMENT_RELPATH,
            "d1_media_supplement_sha256": SOURCE_SUPPLEMENT_SHA256,
            "variant": variant,
            "rule": spec["rule"],
            "built_from": (
                "the SEALED dev-v1 WAV bytes, each re-hashed against the committed D1 "
                "media supplement before it was read; no parent MP3 was opened and no "
                "decoder ran"
            ),
            "id_rule": (
                f"<call>-<segment>@{spec['suffix']}; the published segment key is "
                "recovered by splitting on '@', so the reference layer, the neighbour "
                "lookup and the paired join against the sealed arm are all exact and "
                "no id collides with the dev-v1 population's"
            ),
        },
        "sample_rate_hz": SAMPLE_RATE_HZ,
        "decoder": str(source["decoder"]),
        "writer": str(source["writer"]),
        "count": len(entries),
        "audio_seconds_total": round(
            sum(float(entry["audio_seconds"]) for entry in entries), 6
        ),
        "audio_seconds_longest_item": round(
            max(float(entry["audio_seconds"]) for entry in entries), 6
        ),
        "audio_seconds_shortest_item": round(
            min(float(entry["audio_seconds"]) for entry in entries), 6
        ),
        "audio_tokens_longest_item": max(int(entry["audio_tokens"]) for entry in entries),
        "clamped_to_decoded_parent": sorted(
            str(entry["sample_id"])
            for entry in entries
            if bool(entry["end_clamped_to_decoded_parent"])
        ),
        "per_call": {
            call: {
                "utterances": sum(
                    1 for entry in entries if str(entry["parent_sample_id"]) == call
                ),
                "audio_seconds": round(
                    sum(
                        float(entry["audio_seconds"])
                        for entry in entries
                        if str(entry["parent_sample_id"]) == call
                    ),
                    6,
                ),
            }
            for call in calls
        },
        "ids_sha256": ids_sha256(ids),
        "items": list(entries),
    }
    view["items_sha256"] = canonical_sha256(list(entries))
    return view


def supplement(
    entries: Sequence[Mapping[str, Any]],
    source_supplement: Mapping[str, Any],
    *,
    view_sha256: str,
) -> dict[str, Any]:
    manifest = [
        {
            "id": str(entry["sample_id"]),
            "media_relpath": str(entry["media_relpath"]),
            "sha256": str(entry["audio_sha256"]),
            "bytes": int(entry["bytes"]),
            "audio_seconds": round(float(entry["audio_seconds"]), 6),
            "sample_rate_hz": SAMPLE_RATE_HZ,
            "roles": ["query"],
        }
        for entry in entries
    ]
    ids = [str(row["id"]) for row in manifest]
    return {
        "schema": SUPPLEMENT_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "carrier_lock_key": CARRIER,
        "parent_d1_sha256": str(source_supplement["parent_d1_sha256"]),
        "source_binding_sha256": view_sha256,
        "count": len(manifest),
        "ids_sha256": ids_sha256(ids),
        "manifest": manifest,
        "manifest_sha256": canonical_sha256(manifest),
        "total_bytes": sum(int(row["bytes"]) for row in manifest),
    }


def write_manifest(directory: Path) -> None:
    lines = sorted(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()} *{path.name}"
        for path in directory.iterdir()
        if path.is_file() and path.name != "MANIFEST.sha256"
    )
    (directory / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_variant(
    variant: str, *, write: bool, workers: int, attempts_count: int
) -> dict[str, Any]:
    spec = VARIANTS[variant]
    root = Path(data_root())
    source_view = load_pinned(SOURCE_VIEW_RELPATH, SOURCE_VIEW_SHA256, "dev1500 probe view")
    source_supplement = load_pinned(
        SOURCE_SUPPLEMENT_RELPATH, SOURCE_SUPPLEMENT_SHA256, "dev1500 D1 supplement"
    )
    digests = {
        str(entry["id"]): str(entry["sha256"])
        for entry in source_supplement["manifest"]
    }

    spans: Mapping[str, tuple[float, float]] | None = None
    recut_properties: dict[str, Any] = {}
    if variant == "boundary-exact":
        table = load_segment_table(root, REPO)
        projected = {
            key: {
                "source_id": row["source_id"],
                "start_ts": row["start_ts"],
                "end_ts": row["end_ts"],
            }
            for key, row in table.items()
        }
        del table
        spans, recut_properties = boundary_exact_spans(projected)

    items = list(source_view["items"])

    def one(item: Mapping[str, Any]) -> dict[str, Any]:
        return build_one(
            variant,
            item,
            digests[str(item["sample_id"])],
            spans,
            root,
            write=write,
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        entries = list(pool.map(one, items))
    entries.sort(key=lambda entry: str(entry["sample_id"]))

    receipt = freeze_roster(
        carrier_lock_key=CARRIER,
        candidates=[
            RosterItem(
                sample_id=str(entry["sample_id"]),
                stratum=str(entry["parent_sample_id"]),
                extra={
                    "audio_seconds": float(entry["audio_seconds"]),
                    "media_relpath": str(entry["media_relpath"]),
                },
            )
            for entry in entries
        ],
        per_stratum=PER_CALL,
        seed=FREEZE_SEED,
        split_role="dev",
        roster_id=str(spec["roster_id"]),
        roster_role=EVALUATION_ROSTER_ROLE,
    )
    if len(receipt["items"]) != len(entries):
        raise BuildError("freezing the variant roster dropped rows")

    view = probe_view(variant, source_view, entries)
    view_bytes = (json.dumps(view, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )
    view_sha256 = hashlib.sha256(view_bytes).hexdigest()
    media = supplement(entries, source_supplement, view_sha256=view_sha256)
    media_bytes = (
        json.dumps(media, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")

    out_dir = OUT_ROOT / variant
    build_receipt = {
        "schema": "saea-e22-dev1500-media-variant-build-receipt-v1",
        "exposure_row": "SAEA-SN-MF-E22-DEV1500-ENCODING-VARIANTS-V1",
        "execution_profile": "model-free-check",
        "variant": variant,
        "rule": spec["rule"],
        "id_suffix": spec["suffix"],
        "media_root": spec["subdir"],
        "roster_id": spec["roster_id"],
        "split_name": spec["split_name"],
        "split_role": "dev",
        "split_identity_hash": receipt["split_identity_hash"],
        "count": len(entries),
        "strata_counts": receipt["strata_counts"],
        "deterministic": (
            "this receipt carries no timestamp: two back-to-back writes reproduce "
            "the same MANIFEST.sha256"
        ),
        "measured_media": {
            "audio_seconds_total": view["audio_seconds_total"],
            "audio_seconds_longest_item": view["audio_seconds_longest_item"],
            "audio_seconds_shortest_item": view["audio_seconds_shortest_item"],
            "audio_hours_total": round(view["audio_seconds_total"] / 3600.0, 6),
            "total_bytes": media["total_bytes"],
            "n_samples_total": sum(int(entry["n_samples"]) for entry in entries),
            "samples_added_total": sum(int(entry["samples_added"]) for entry in entries),
            "samples_removed_total": sum(
                int(entry["samples_removed"]) for entry in entries
            ),
            "clips_left_unchanged": sum(1 for entry in entries if entry["unchanged"]),
            "audio_tokens_total": sum(int(entry["audio_tokens"]) for entry in entries),
            "audio_tokens_longest_item": view["audio_tokens_longest_item"],
            "zero_pad_frames_total": sum(
                int(entry["zero_pad_frames"]) for entry in entries
            ),
            "encoder_windows_max": max(int(entry["encoder_windows"]) for entry in entries),
        },
        "source_population": {
            "roster_receipt": SOURCE_VIEW_RELPATH,
            "roster_receipt_sha256": SOURCE_VIEW_SHA256,
            "d1_media_supplement": SOURCE_SUPPLEMENT_RELPATH,
            "d1_media_supplement_sha256": SOURCE_SUPPLEMENT_SHA256,
            "split_identity_hash": (
                "c626e62f8876bf52a2904a0d2ec91807a530f3195c10facc8c036f661b2bf88a"
            ),
            "audio_seconds_total": 9948.983,
            "files_rehashed_before_reading": len(entries),
            "all_source_digests_matched": True,
        },
        "recut_properties": recut_properties,
        "outputs": {
            "roster_receipt": str(spec["roster_receipt"]),
            "roster_receipt_sha256": hashlib.sha256(
                canonical_receipt_bytes(receipt)
            ).hexdigest(),
            "probe_view": (out_dir / "roster" / "flight-roster-receipt.json")
            .relative_to(REPO)
            .as_posix(),
            "probe_view_sha256": view_sha256,
            "d1_media_supplement": str(spec["supplement"]),
            "d1_media_supplement_sha256": hashlib.sha256(media_bytes).hexdigest(),
        },
        "contacts": {
            "frozen_core": 0,
            "tokenizer": 0,
            "embedder": 0,
            "retriever": 0,
            "scorer": 0,
            "network": 0,
            "gpu_hours": 0,
            "paid_api_spend": 0,
            "parent_mp3_decodes": 0,
            "librosa_calls": 0,
            "outbound_connection_attempts": attempts_count,
        },
        "opened": {
            "reference_sentences": 0,
            "hypothesis_text": 0,
            "scores": 0,
            "test_split_artifacts": 0,
            "segment_table_columns": (
                ["source_id", "start_ts", "end_ts"] if spans is not None else []
            ),
        },
        "test_split_read": False,
    }

    if write:
        (REPO / str(spec["roster_receipt"])).parent.mkdir(parents=True, exist_ok=True)
        write_roster(receipt, REPO / str(spec["roster_receipt"]))
        (out_dir / "roster").mkdir(parents=True, exist_ok=True)
        (out_dir / "roster" / "flight-roster-receipt.json").write_bytes(view_bytes)
        (REPO / str(spec["supplement"])).write_bytes(media_bytes)
        write_json_artifact(out_dir / "build-receipt.json", build_receipt)
        write_manifest(out_dir)
        write_manifest(out_dir / "roster")
    return build_receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--variant",
        choices=[*VARIANTS, "all"],
        required=True,
        help="which probe media variant to build",
    )
    parser.add_argument("--write", action="store_true", help="write media and receipts")
    parser.add_argument(
        "--workers", type=int, default=8, help="CPU workers (campaign cap is 8)"
    )
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 8:
        raise SystemExit("workers must be between 1 and 8 (the campaign cap)")

    attempts = arm_offline_guard()
    chosen = list(VARIANTS) if args.variant == "all" else [args.variant]
    for variant in chosen:
        receipt = build_variant(
            variant,
            write=args.write,
            workers=args.workers,
            attempts_count=attempts.count,
        )
        media = receipt["measured_media"]
        print(
            "%s: %d clips, %.3f s (%.4f h), %d audio tokens, longest %.6f s / %d tokens, "
            "identity %s"
            % (
                variant,
                receipt["count"],
                media["audio_seconds_total"],
                media["audio_hours_total"],
                media["audio_tokens_total"],
                media["audio_seconds_longest_item"],
                media["audio_tokens_longest_item"],
                receipt["split_identity_hash"],
            )
        )
        print(
            "  +%d samples, -%d samples, %d clips unchanged, %d bytes on disk"
            % (
                media["samples_added_total"],
                media["samples_removed_total"],
                media["clips_left_unchanged"],
                media["total_bytes"],
            )
        )
        if receipt["recut_properties"]:
            print("  re-cut properties: %s" % (receipt["recut_properties"],))
    if not args.write:
        print("(print only; pass --write to land the media and the receipts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
