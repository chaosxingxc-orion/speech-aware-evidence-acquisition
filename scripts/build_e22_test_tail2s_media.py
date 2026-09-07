#!/usr/bin/env python3
"""Build the Earnings-22 ESB TEST ``tail-silence-2s`` media variant (model-free, CPU only).

Exposure row ``SAEA-SN-MF-E22-TEST-TS2-MEDIA-V1`` (``model-free-check``),
registered before the first byte was written.

What this builds, and why it is a separate script
-------------------------------------------------
``scripts/build_e22_dev1500_media_variants.py`` built three probe media
variants of the 1,500-row Earnings-22 **DEV** subset. This script builds the
**one** variant the Earnings-22 completion path needs on the **TEST**
population: exactly 2.0 s (32,000 zero samples) appended to each of the 2,735
published ESB test utterances of the six calibration-exposed calls.

The transformation is not re-implemented here. ``transform`` and ``read_clip``
are imported from the dev builder itself, whose file is pinned by SHA-256
below, so "built exactly as the dev variant was" is a machine-checked property
of this run rather than a claim in a document. The rest of this file is the
population's own identity: which source view and supplement are pinned, which
derived root the bytes land in, and which receipts they land beside.

What is READ, and what is never opened
--------------------------------------
**Media bytes only.** The inputs are the committed test probe view (identifiers,
media paths, measured media identity and segment spans) and the committed test
D1 media supplement (ids, relpaths, digests, byte counts). Every source WAV is
re-hashed against that supplement before it is read, and only its int16 samples
are used. **No reference sentence, no segment-table column, no sealed output, no
hypothesis text and no score is opened**, and the build receipt records each of
those as zero. The six test calls' parent MP3s are never opened either: this is a
transformation of the sealed derived clips, so ``librosa`` never runs and the
pinned absence of ``ffmpeg`` is preserved.

This row therefore touches a calibration-exposed population, and it says so:
``test_split_read`` is ``true`` with ``test_split_read_scope`` naming media bytes
only. Building the media is not a read of the evaluation surface and it is not a
model contact; the SECOND READ of these six calls is the flight this media
enables, which needs its own owner GO and its own exposure row.

Usage::

    python scripts/build_e22_test_tail2s_media.py            # print only
    python scripts/build_e22_test_tail2s_media.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import speech_aware_evidence_acquisition.core as _core  # noqa: E402, F401

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
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
EXPOSURE_ROW = "SAEA-SN-MF-E22-TEST-TS2-MEDIA-V1"
VARIANT = "tail-silence-2s"
ID_SUFFIX = "ts2"

#: The dev builder is the ONE implementation of the rule. It is pinned by
#: content: if that file changes, this build refuses rather than quietly
#: producing bytes some other rule wrote.
DEV_BUILDER_RELPATH = "scripts/build_e22_dev1500_media_variants.py"
DEV_BUILDER_SHA256 = "49e5d91095c061d167688bd4dea35fc7503d3a09caa3066db68fde9807d196e6"

#: The committed TEST population, both pinned by content.
SOURCE_VIEW_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-04-e22-esb-shortform-alignment-400-v1/roster/flight-roster-receipt.json"
)
SOURCE_VIEW_SHA256 = "72be506b01c69e30097e25e836595b261dffa826bb8d31ccf8188fdbbd879ecb"
SOURCE_SUPPLEMENT_RELPATH = "docs/receipts/artifacts/d1-e22-esb-utterances-2735.json"
SOURCE_SUPPLEMENT_SHA256 = (
    "caa221ec512736f0dfad338d92e290e76b0663e188de89f97d9cbe1bb1ee906e"
)
SOURCE_SPLIT_IDENTITY = (
    "9285b32127c684ca7edd3a0f842e772f0a308a3c5021759e8381c5c45221189d"
)
SOURCE_AUDIO_SECONDS = 19494.608437
SOURCE_MEDIA_SUBDIR = "derived/e22-esb-utterances/v1"

#: The six ESB test calls, and nothing else, may appear in this build.
TEST_CALLS = (
    "4432298",
    "4450488",
    "4470290",
    "4479741",
    "4483338",
    "4485244",
)

SUBDIR = "derived/e22-esb-utterances/test2735-tail2s-v1"
ROSTER_ID = "E22-ESB-TEST-2735-TS2-V1"
SPLIT_NAME = "E22-ESB-TEST2735-TAIL2S-UTTERANCES"
ROSTER_RECEIPT_RELPATH = "docs/receipts/rosters/e22-esb-test-2735-ts2-v1.json"
SUPPLEMENT_RELPATH = "docs/receipts/artifacts/d1-e22-esb-test2735-tail2s.json"
RULE = (
    "exactly 2.0 s (32,000 zero samples) appended to the sealed test v1 clip; "
    "nothing is removed and nothing is re-decoded"
)

#: Freezing the ALREADY complete population, not drawing from it: the quota for
#: every call equals that call's own published utterance count, so the seed
#: cannot change the membership. It is recorded for reproducibility only.
FREEZE_SEED = 20260907

OUT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-07-e22-test2735-tail2s-media"
)


class BuildError(RuntimeError):
    """An input drifted, a property failed, or a written byte did not reproduce."""


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


def ids_sha256(ids: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def load_pinned(relpath: str, expected: str, label: str) -> Mapping[str, Any]:
    path = REPO / relpath
    measured = sha256_file(path)
    if measured != expected:
        raise BuildError(
            f"{label} identity drift: pinned {expected[:12]}..., {path} now hashes "
            f"to {measured[:12]}..."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def load_dev_builder() -> Any:
    """The dev builder module, pinned by content, for its rule and its reader."""

    path = REPO / DEV_BUILDER_RELPATH
    measured = sha256_file(path)
    if measured != DEV_BUILDER_SHA256:
        raise BuildError(
            "the dev variant builder drifted: pinned "
            f"{DEV_BUILDER_SHA256[:12]}..., {path} now hashes to {measured[:12]}.... "
            "This build reuses that file's transform, so a changed rule must be an "
            "explicit re-pin, never a silent inheritance."
        )
    spec = importlib.util.spec_from_file_location("e22_dev1500_media_variants", path)
    if spec is None or spec.loader is None:
        raise BuildError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.VARIANTS[VARIANT]["suffix"] != ID_SUFFIX:
        raise BuildError("the dev builder's tail-silence-2s suffix is not 'ts2'")
    if module.TAIL_SILENCE_SAMPLES != 2 * SAMPLE_RATE_HZ:
        raise BuildError("the dev builder's tail length is not 2.0 s")
    return module


def build_one(
    dev: Any,
    item: Mapping[str, Any],
    source_digest: str,
    root: Path,
    *,
    write: bool,
) -> dict[str, Any]:
    """One clip, through the dev builder's own transform and the shared writer."""

    if str(item["parent_sample_id"]) not in TEST_CALLS:
        raise BuildError(
            "%s is not one of the six ESB test calls" % (item["parent_sample_id"],)
        )
    source_relpath = str(item["media_relpath"])
    if not source_relpath.startswith(SOURCE_MEDIA_SUBDIR + "/"):
        raise BuildError(f"source media path escapes the sealed test root: {source_relpath}")
    source_path = root / source_relpath
    measured = sha256_file(source_path)
    if measured != source_digest:
        raise BuildError(
            f"source media drift on {item['sample_id']}: supplement records "
            f"{source_digest[:12]}..., disk hashes to {measured[:12]}..."
        )
    samples = dev.read_clip(source_path)
    if len(samples) != int(round(float(item["audio_seconds"]) * SAMPLE_RATE_HZ)):
        raise BuildError(f"{item['sample_id']}: sealed clip length disagrees with roster")

    produced = dev.transform(VARIANT, samples, item, None)
    if len(produced) != len(samples) + 2 * SAMPLE_RATE_HZ:
        raise BuildError(f"{item['sample_id']}: the tail is not exactly 2.0 s")
    if produced[: len(samples)] != samples:
        raise BuildError(f"{item['sample_id']}: the published samples were altered")
    if any(produced[len(samples) :]):
        raise BuildError(f"{item['sample_id']}: the appended tail is not digital silence")

    payload = write_wav_bytes(produced, SAMPLE_RATE_HZ)
    # Determinism is checked rather than assumed: the same inputs are pushed
    # through the same writer twice and the bytes must agree.
    if write_wav_bytes(dev.transform(VARIANT, samples, item, None), SAMPLE_RATE_HZ) != payload:
        raise BuildError(f"{item['sample_id']}: the writer is not deterministic")

    new_id = f"{item['sample_id']}@{ID_SUFFIX}"
    relpath = f"{SUBDIR}/{item['parent_sample_id']}/{new_id}.wav"
    target = root / relpath
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        if sha256_file(target) != hashlib.sha256(payload).hexdigest():
            raise BuildError(f"{new_id}: written bytes do not match the payload")

    encoding = describe_clip(len(produced))
    return {
        "sample_id": new_id,
        "published_segment_id": str(item["sample_id"]),
        "parent_sample_id": str(item["parent_sample_id"]),
        "parent_media_relpath": str(item["parent_media_relpath"]),
        "parent_sha256": str(item["parent_sha256"]),
        "parent_decoded_seconds": item["parent_decoded_seconds"],
        "source_media_relpath": source_relpath,
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
        "samples_added": len(produced) - len(samples),
        "samples_removed": 0,
        "unchanged": False,
        "audio_tokens": encoding.llamacpp_tokens,
        "encoder_windows": len(encoding.windows),
        "zero_pad_frames": encoding.zero_pad_frames,
    }


def probe_view(
    source: Mapping[str, Any], entries: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """The ``saea-e22-esb-utterance-roster-receipt-v1`` shape a flight hydrates."""

    ids = [str(entry["sample_id"]) for entry in entries]
    if ids != sorted(ids):
        raise BuildError("the variant items are not in sample-id order")
    calls = sorted({str(entry["parent_sample_id"]) for entry in entries})
    view: dict[str, Any] = {
        "schema": ROSTER_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "carrier": CARRIER,
        "split_name": SPLIT_NAME,
        "split_role": "dev",
        "split_role_basis": (
            "The SAME 2,735 published ESB test utterances the sealed 2026-09-05 "
            "SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1 flight already read, re-encoded by one "
            "deterministic rule from the sealed v1 bytes. The 2026-09-04 owner decision "
            "re-designated these six calls calibration-exposed after that one read, and "
            "contracts.plan.STAGE2_SPLIT_ROLES admits only 'discovery' and 'dev', so 'dev' "
            "-- the role that means usable for calibration and never for final reporting -- "
            "is how calibration-exposed reaches the machine, exactly as the sealed test "
            "roster already expresses it. Building this media is NOT the second read: the "
            "flight that sends it needs the owner's explicit GO and its own exposure row. "
            "The 109 remaining confirmatory calls are not named, loaded, decoded or read."
        ),
        "version": str(source["version"]),
        "source_segment_table": dict(source["source_segment_table"]),
        "derived_from": {
            "roster_receipt": SOURCE_VIEW_RELPATH,
            "roster_receipt_sha256": SOURCE_VIEW_SHA256,
            "d1_media_supplement": SOURCE_SUPPLEMENT_RELPATH,
            "d1_media_supplement_sha256": SOURCE_SUPPLEMENT_SHA256,
            "variant": VARIANT,
            "rule": RULE,
            "rule_implementation": {
                "module": DEV_BUILDER_RELPATH,
                "sha256": DEV_BUILDER_SHA256,
                "function": "transform('tail-silence-2s', ...)",
                "note": (
                    "the dev1500 builder's own transform, imported and pinned by content, "
                    "so this population's bytes are produced by the same rule and the same "
                    "code as the dev1500 tail-silence-2s variant"
                ),
            },
            "built_from": (
                "the SEALED v1 test WAV bytes, each re-hashed against the committed D1 "
                "media supplement before it was read; no parent MP3 was opened and no "
                "decoder ran"
            ),
            "id_rule": (
                f"<call>-<segment>@{ID_SUFFIX}; the published segment key is recovered by "
                "splitting on '@', so the reference layer and the paired join against the "
                "sealed test arm are both exact and no id collides with the v1 population's"
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


def build(*, write: bool, workers: int, attempts_count: int) -> dict[str, Any]:
    dev = load_dev_builder()
    root = Path(data_root())
    source_view = load_pinned(SOURCE_VIEW_RELPATH, SOURCE_VIEW_SHA256, "test probe view")
    source_supplement = load_pinned(
        SOURCE_SUPPLEMENT_RELPATH, SOURCE_SUPPLEMENT_SHA256, "test D1 supplement"
    )
    if str(source_view["split_name"]) != "E22-ESB-TEST-UTTERANCES-2735":
        raise BuildError("the pinned source view is not the ESB test population")
    digests = {
        str(entry["id"]): str(entry["sha256"])
        for entry in source_supplement["manifest"]
    }
    items = list(source_view["items"])
    if len(items) != 2735 or len(digests) != 2735:
        raise BuildError("the pinned test population is not 2,735 rows")

    def one(item: Mapping[str, Any]) -> dict[str, Any]:
        return build_one(dev, item, digests[str(item["sample_id"])], root, write=write)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        entries = list(pool.map(one, items))
    entries.sort(key=lambda entry: str(entry["sample_id"]))

    per_call = {
        call: sum(1 for entry in entries if str(entry["parent_sample_id"]) == call)
        for call in TEST_CALLS
    }
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
        per_stratum=per_call,
        seed=FREEZE_SEED,
        split_role="dev",
        roster_id=ROSTER_ID,
        roster_role=EVALUATION_ROSTER_ROLE,
    )
    if len(receipt["items"]) != len(entries):
        raise BuildError("freezing the variant roster dropped rows")

    view = probe_view(source_view, entries)
    view_bytes = (
        json.dumps(view, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    view_sha256 = hashlib.sha256(view_bytes).hexdigest()
    media = supplement(entries, source_supplement, view_sha256=view_sha256)
    media_bytes = (
        json.dumps(media, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")

    build_receipt = {
        "schema": "saea-e22-test2735-media-variant-build-receipt-v1",
        "exposure_row": EXPOSURE_ROW,
        "execution_profile": "model-free-check",
        "variant": VARIANT,
        "rule": RULE,
        "rule_implementation": {
            "module": DEV_BUILDER_RELPATH,
            "sha256": DEV_BUILDER_SHA256,
            "function": "transform('tail-silence-2s', ...)",
        },
        "id_suffix": ID_SUFFIX,
        "media_root": SUBDIR,
        "roster_id": ROSTER_ID,
        "split_name": SPLIT_NAME,
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
            "samples_removed_total": 0,
            "clips_left_unchanged": 0,
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
            "split_identity_hash": SOURCE_SPLIT_IDENTITY,
            "audio_seconds_total": SOURCE_AUDIO_SECONDS,
            "media_root": SOURCE_MEDIA_SUBDIR,
            "files_rehashed_before_reading": len(entries),
            "all_source_digests_matched": True,
        },
        "outputs": {
            "roster_receipt": ROSTER_RECEIPT_RELPATH,
            "roster_receipt_sha256": hashlib.sha256(
                canonical_receipt_bytes(receipt)
            ).hexdigest(),
            "probe_view": (OUT_DIR / "roster" / "flight-roster-receipt.json")
            .relative_to(REPO)
            .as_posix(),
            "probe_view_sha256": view_sha256,
            "d1_media_supplement": SUPPLEMENT_RELPATH,
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
            "sealed_outputs": 0,
            "segment_table_columns": [],
            "note": (
                "MEDIA BYTES ONLY. The build reads the committed probe view and D1 "
                "supplement (identifiers, media paths, measured media identity, segment "
                "spans) and the int16 samples of the sealed test WAVs. No reference "
                "sentence, no segment-table column, no sealed output, no hypothesis and "
                "no score is opened, and no test-side text of any kind is reachable from "
                "this process."
            ),
        },
        "test_split_read": True,
        "test_split_read_scope": (
            "MEDIA ONLY, on a calibration-exposed population. The six ESB test calls were "
            "re-designated calibration-exposed by the 2026-09-04 owner decision after the "
            "sealed SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1 read. This row transforms the "
            "derived clip bytes of that same population and opens nothing else; it is not "
            "a model contact and it is not the second read of the evaluation surface, "
            "which is the flight this media enables and which needs its own owner GO and "
            "its own exposure row."
        ),
    }

    if write:
        (REPO / ROSTER_RECEIPT_RELPATH).parent.mkdir(parents=True, exist_ok=True)
        write_roster(receipt, REPO / ROSTER_RECEIPT_RELPATH)
        (OUT_DIR / "roster").mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "roster" / "flight-roster-receipt.json").write_bytes(view_bytes)
        (REPO / SUPPLEMENT_RELPATH).write_bytes(media_bytes)
        write_json_artifact(OUT_DIR / "build-receipt.json", build_receipt)
        write_manifest(OUT_DIR)
        write_manifest(OUT_DIR / "roster")
    return build_receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write media and receipts")
    parser.add_argument(
        "--workers", type=int, default=8, help="CPU workers (campaign cap is 8)"
    )
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 8:
        raise SystemExit("workers must be between 1 and 8 (the campaign cap)")

    attempts = arm_offline_guard()
    receipt = build(write=args.write, workers=args.workers, attempts_count=attempts.count)
    media = receipt["measured_media"]
    print(
        "%s: %d clips, %.3f s (%.4f h), %d audio tokens, longest %.6f s / %d tokens, "
        "identity %s"
        % (
            receipt["variant"],
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
        "  +%d samples, -%d samples, %d bytes on disk, strata %s"
        % (
            media["samples_added_total"],
            media["samples_removed_total"],
            media["total_bytes"],
            receipt["strata_counts"],
        )
    )
    if not args.write:
        print("(print only; pass --write to land the media and the receipts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
