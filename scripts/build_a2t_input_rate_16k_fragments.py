#!/usr/bin/env python3
"""Emit the config fragments the two Audio2Tool input-rate cells compose from.

Model-free, zero contacts. Under the media row
``SAEA-SN-MF-A2T-CAL400-16K-MEDIA-V1``, whose artifacts this reads and whose
scope already covers writing the fragments that name them. **No cell is flown
and no request is built here**; each cell still needs its own preregistration
clause, its own owner GO and its own exposure row.

Four dataset fragments and four experiment fragments
----------------------------------------------------
Two populations -- ``@16k`` (cell a) and ``@16k+ts2`` (cell b) -- each with its
full 400 rows and a 4-row smoke. The smoke rows are DERIVED, not drawn: one row
per tier in sorted order, the first four tiers, so the same probe view always
yields the same four ids.

No model fragment is emitted, and that is the point
---------------------------------------------------
Both cells serve on ``q4km-featcache-a2t-official-04ccc72a`` -- the sealed
comparator's own fragment, byte for byte, ``-c 49152 -np 3`` included. The
media is the single factor and the serving path is not. Cell (a) does not even
move the token budget: it changes each clip's sample count by at most one
sample, so ``13 * (n_samples // 16000 + 1)`` is unchanged on all but a clip
sitting exactly on a 100-frame boundary. Cell (b) adds 2.0 s = 2 blocks =
26 tokens, worst request 4,333 against a 16,384-token slot.

Usage (WSL2)::

    python scripts/build_a2t_input_rate_16k_fragments.py
    python scripts/build_a2t_input_rate_16k_fragments.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import speech_aware_evidence_acquisition.core as _core  # noqa: E402, F401

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash,
)

CHECKS = REPO / "docs/checks/speech-aware-evidence-acquisition"
PREREGISTRATION = (
    "docs/readiness/2026-09-07-a2t-input-rate-standardization-v1-preregistration.md"
)
AUDIT = "docs/readiness/2026-09-07-a2t-input-rate-audit-v1.md"
MEDIA_ROW = "SAEA-SN-MF-A2T-CAL400-16K-MEDIA-V1"

#: The four rows each cell's dry run flies, fixed HERE and in the committed
#: fragment rather than on a command line, so a smoke can never quietly fly four
#: different rows than the ones its exposure row names.
SMOKE_SIZE = 4

COMPARATOR: dict[str, Any] = {
    "run_id": "SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1",
    "attempt_id": "attempt-20260904T135250Z-rofficialraw",
    "cell_id": "R-official-raw",
    "config_hash": "0e56ce8f2e71d1e4e8702433ae7c997aacf4e548414100bad5a1d9b9c8ef5165",
    "protocol_hash": "6da614b22de0001760b0263f6026483373ce190d801cc8dd9008e34bb595aa8a",
    "split_identity_hash": (
        "e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c"
    ),
    "paper_facing_scorer": "a2t-toolcall-official",
    "what_the_comparator_sends": (
        "the sealed 24 kHz bytes verbatim; the 24 -> 16 kHz conversion happens inside "
        "llama.cpp's miniaudio linear resampler, which is the arm under test"
    ),
    "sealed_official_tool_accuracy": {
        "tier1_direct": 60.0,
        "tier2_parametric": 74.0,
        "tier3_multi_intent": 72.0,
        "tier4_implicit": 28.0,
        "tier5_needle": 78.0,
        "tier6_correction": 84.0,
        "tier7_multiturn": 58.0,
        "tier8_intent_blending": 34.0,
        "overall": 61.0,
        "exact_match": 20.25,
        "parse_rate": 99.75,
        "rows_with_multiple_call_matches": 52,
        "n": 400,
    },
}

#: The two populations. Everything that differs between cell (a) and cell (b)
#: lives here and nowhere else.
CELLS: dict[str, dict[str, Any]] = {
    "16k": {
        "view": CHECKS / "2026-09-07-a2t-calibration-400-16k-media/roster/flight-roster-receipt.json",
        "build_receipt": (
            "docs/checks/speech-aware-evidence-acquisition/"
            "2026-09-07-a2t-calibration-400-16k-media/build-receipt.json"
        ),
        "supplement": "docs/receipts/artifacts/d1-a2t-calibration-400-16k.json",
        "derived_subdir": "derived/a2t-calibration-400-16k-v1",
        "split_id": "A2T-CALIBRATION-400-16K",
        "split_name": "A2T-CALIBRATION-400-16K",
        "dataset": "audio2tool-calibration-400-16k",
        "experiment": "a2t-official-protocol-16k-400",
        "run_id": "SAEA-A2T-OFFICIAL-PROTOCOL-16K-V1",
        "cell_id": "R-official-16k",
        "planned_speech_audio_seconds": 2400,
        "factor": (
            "the media, and only the media: the SAME clips resampled 24 -> 16 kHz by "
            "librosa soxr_hq instead of by llama.cpp's miniaudio linear resampler"
        ),
        "purpose": (
            "Cell (a) of the Audio2Tool input-rate standardization. ONE factor, the "
            "MEDIA: every sealed 24 kHz release wav resampled to 16 kHz mono int16 "
            "through the study's own pinned decoder (reproduction.obs_loop."
            "decode_parent_pcm, librosa soxr_hq), so the study performs the rate "
            "conversion that llama.cpp's miniaudio linear resampler performs today. The "
            "published system message, the compact 152-row registry, the user turn, the "
            "geometry, the decoding and the official scorer are the sealed "
            "SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1 cell R-official-raw's, byte for "
            "byte. Durations equal the sealed clips within one 16 kHz sample on 400 of "
            "400 and every deviation is positive, so nothing is truncated. This "
            "fragment authorizes NOTHING."
        ),
    },
    "16k+ts2": {
        "view": CHECKS
        / "2026-09-07-a2t-calibration-400-16k-tail2s-media/roster/flight-roster-receipt.json",
        "build_receipt": (
            "docs/checks/speech-aware-evidence-acquisition/"
            "2026-09-07-a2t-calibration-400-16k-tail2s-media/build-receipt.json"
        ),
        "supplement": "docs/receipts/artifacts/d1-a2t-calibration-400-16k-tail2s.json",
        "derived_subdir": "derived/a2t-calibration-400-16k-tail2s-v1",
        "split_id": "A2T-CALIBRATION-400-16K-TS2",
        "split_name": "A2T-CALIBRATION-400-16K-TAIL2S",
        "dataset": "audio2tool-calibration-400-16k-tail2s",
        "experiment": "a2t-official-protocol-16k-tail2s-400",
        "run_id": "SAEA-A2T-OFFICIAL-PROTOCOL-16K-TAIL2S-V1",
        "cell_id": "R-official-16k-tail2s",
        "planned_speech_audio_seconds": 3100,
        "factor": (
            "two changes together and stated as such: the librosa 16 kHz "
            "standardization, plus exactly 2.0 s of digital silence after the sealed "
            "samples"
        ),
        "purpose": (
            "Cell (b) of the Audio2Tool input-rate standardization: the 2.0 s silence "
            "tail on STANDARDIZED media. It REPLACES the cross-carrier "
            "preregistration's R-official-tail2s cell, whose tail sits on 24 kHz bytes, "
            "if and only if cell (a) admits the standardization. Its comparator is the "
            "same sealed 24 kHz run, so it measures the tail and the standardization "
            "TOGETHER; the tail's own effect is the difference against cell (a) and is "
            "reported but is not an admission criterion. It does not fly until cell (a) "
            "has flown and been read. This fragment authorizes NOTHING."
        ),
    },
}


class FragmentError(RuntimeError):
    """An input drifted or a derived identity did not reproduce."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dumps(document: object) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def load_view(path: Path) -> Mapping[str, Any]:
    view = json.loads(path.read_text(encoding="utf-8"))
    if view["schema"] != "saea-a2t-input-rate-16k-probe-view-v1":
        raise FragmentError(f"{path} is not an input-rate 16k probe view")
    ids = [str(item["sample_id"]) for item in view["items"]]
    if hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest() != view["ids_sha256"]:
        raise FragmentError(f"{path} ids_sha256 does not reproduce")
    if int(view["sample_rate_hz"]) != 16000:
        raise FragmentError(f"{path} is not a 16 kHz population")
    return view


def smoke_ids(view: Mapping[str, Any]) -> list[str]:
    """One row per tier, the first ``SMOKE_SIZE`` tiers in sorted order.

    Deterministic and derived, never drawn: the strata are visited in sorted
    order and each contributes its own first id, so the same view always yields
    the same four rows.
    """

    by_stratum: dict[str, list[str]] = {}
    for item in view["items"]:
        by_stratum.setdefault(str(item["stratum"]), []).append(str(item["sample_id"]))
    picked = [sorted(by_stratum[stratum])[0] for stratum in sorted(by_stratum)][:SMOKE_SIZE]
    if len(picked) != SMOKE_SIZE:
        raise FragmentError("the view carries fewer strata than the smoke needs")
    return sorted(picked)


def dataset_fragment(
    name: str, view: Mapping[str, Any], *, subset: Sequence[str] | None
) -> dict[str, Any]:
    cell = CELLS[name]
    wanted = set(subset) if subset is not None else None
    items = [
        item for item in view["items"] if wanted is None or str(item["sample_id"]) in wanted
    ]
    if wanted is not None and len(items) != len(wanted):
        raise FragmentError("the smoke subset names an id the view does not carry")
    ids = [str(item["sample_id"]) for item in items]
    suffix = "-SMOKE-4" if subset else ""
    return {
        "carrier_lock_key": "audio2tool",
        "split_id": str(cell["split_id"]) + ("-SMOKE-4" if subset else ""),
        "a2t_calibration_subset_receipt": str(
            Path(cell["view"]).relative_to(REPO).as_posix()
        ),
        "a2t_calibration_subset_receipt_sha256": sha256_file(Path(cell["view"])),
        "a2t_calibration_split_name": str(cell["split_name"]) + suffix,
        "a2t_calibration_split_role": "discovery",
        "a2t_calibration_split_identity_hash": hashlib.sha256(
            "\n".join(sorted(ids)).encode("utf-8")
        ).hexdigest(),
        "a2t_calibration_flight_split_identity_hash": split_identity_hash(
            prefixed("audio2tool", ids)
        ),
        "a2t_calibration_identity_hash_conventions": (
            "a2t_calibration_split_identity_hash is SHA-256 over the LF-joined sorted "
            "sample ids of THIS variant; a2t_calibration_flight_split_identity_hash is "
            "data.splits.split_identity_hash(prefixed('audio2tool', sample_ids)), the "
            "value core.flight.FlightRuntime.preflight computes at flight time. Both "
            "differ from the sealed frozen 400's and from the other variant's, which is "
            "the identity separation the '@' suffix exists to guarantee."
        ),
        "a2t_calibration_count": len(items),
        "a2t_calibration_audio_seconds_total": round(
            sum(float(item["audio_seconds"]) for item in items), 6
        ),
        "a2t_calibration_audio_seconds_longest_item": round(
            max(float(item["audio_seconds"]) for item in items), 6
        ),
        "a2t_calibration_sample_rate_hz": 16000,
        "a2t_calibration_source_sample_rate_hz": 24000,
        # The variant lives under its own derived root, so payload confinement
        # binds to that root instead of datasets/audio2tool. The runner reads
        # this key through the carrier_root_resolver seam FlightRuntime already
        # exposes.
        "a2t_calibration_derived_subdir": str(cell["derived_subdir"]),
        # BOTH SPELLINGS, AND THEY MUST AGREE. The carrier-prefixed pair is
        # what ``core.base.declared_derived_media_roots`` reads to vouch for
        # the derived root above; the PLAIN pair is what ``core.config.
        # d1_media_supplement_relpath`` -- and therefore the media IDENTITY
        # gate ``core.flight.FlightRuntime.preflight`` constructs -- reads.
        # Emitting only the prefixed pair satisfied confinement and left the
        # identity gate seeing no supplement, so every roster id was refused
        # as outside D1's closure at the first real request (2026-09-09,
        # docs/readiness/2026-09-09-a2t-derived-media-d1-declaration-fix-v1.md).
        # ``core.config.assert_d1_media_supplement_spellings_agree`` now
        # refuses any fragment where these four values disagree.
        "a2t_calibration_d1_media_supplement": str(cell["supplement"]).removeprefix("docs/"),
        "a2t_calibration_d1_media_supplement_sha256": sha256_file(
            REPO / str(cell["supplement"])
        ),
        "d1_media_supplement": str(cell["supplement"]).removeprefix("docs/"),
        "d1_media_supplement_sha256": sha256_file(REPO / str(cell["supplement"])),
        "a2t_calibration_d1_basis": (
            "Unlike the sealed frozen 400 -- whose ids are inside the base D1 closure and "
            "which therefore declares NO supplement -- these ids are new media that "
            "duplicate nothing in that closure, so an additive supplement is both needed "
            "and legal under contracts.gate_media_identity."
        ),
        "a2t_calibration_rate_rule": (
            "16 kHz mono int16, produced by reproduction.obs_loop.decode_parent_pcm "
            "(librosa.load(sr=16000, mono=True), res_type 'soxr_hq', librosa 0.11.0 / "
            "soxr 1.1.0), then clip(rint(float32 * 32767), -32768, 32767). The decoder "
            "is pinned by the SHA-256 of its own source text and the build refuses if "
            "ffmpeg appears on PATH, because decode_parent_pcm would prefer it."
        ),
        "a2t_calibration_exposure": (
            "The same frozen 400 discovery split, re-encoded. Nothing is drawn. Media "
            f"row {MEDIA_ROW}. This fragment grants no contact authority."
        ),
        "a2t_calibration_media_build_receipt": str(cell["build_receipt"]),
    }


def experiment_fragment(
    name: str, *, smoke: bool, smoke_ids_: Sequence[str]
) -> dict[str, Any]:
    cell = CELLS[name]
    dataset = str(cell["dataset"]) + ("-smoke4" if smoke else "")
    run_id = str(cell["run_id"]).replace("-V1", "-SMOKE-V1") if smoke else str(cell["run_id"])
    doc: dict[str, Any] = {
        "experiment_id": run_id,
        "schema": "saea-a2t-direct-calibration-experiment-v1",
        "date": "2026-09-07",
        "execution_profile": "baseline-reproduction",
        "purpose": str(cell["purpose"])
        + (" This is the 4-row dry run that must pass before the 400 contacts." if smoke else ""),
        "population": {
            "carrier": "audio2tool",
            "split_name": str(cell["split_name"]) + ("-SMOKE-4" if smoke else ""),
            "split_role": "discovery",
            "dataset_fragment": dataset,
            "count": SMOKE_SIZE if smoke else 400,
            "media_exposure_row": MEDIA_ROW,
        },
        "cells": [
            {
                "cell_id": str(cell["cell_id"]) + ("-smoke-4" if smoke else ""),
                "factor": str(cell["factor"]),
                "arm": "bare-core",
                "baseline_fragment": "a2t-direct-official-protocol",
                # The sealed comparator's OWN model fragment, unchanged: same
                # -c 49152 -np 3, same decoding, same prompt order, same
                # runtime receipt. The media is the single factor.
                "model_fragment": "q4km-featcache-a2t-official-04ccc72a",
                "dataset_fragment": dataset,
            }
        ],
        "execution_plan": {
            "execution_profile": "baseline-reproduction",
            "split_role": "discovery",
            "planned_model_calls": 8 if smoke else 408,
            "planned_gpu_hours": 0.05 if smoke else 0.20,
            "planned_speech_audio_seconds": 60
            if smoke
            else int(cell["planned_speech_audio_seconds"]),
        },
        "comparator": dict(COMPARATOR),
        "preregistration": PREREGISTRATION,
        "resampler_audit": AUDIT,
        "media": {
            "build_receipt": str(cell["build_receipt"]),
            "exposure_row": MEDIA_ROW,
            "count": SMOKE_SIZE if smoke else 400,
            "derived_subdir": str(cell["derived_subdir"]),
        },
        "serving_geometry_unchanged": (
            "the sealed comparator's own -c 49152 -np 3, unchanged. Cell (a) changes "
            "each clip's sample count by at most one sample, so the measured worst "
            "request (3,581 registry text + 468 speech + 256 completion + 2 special = "
            "4,307 tokens) is unchanged; cell (b) adds 2 blocks = 26 speech tokens, "
            "worst request 4,333, both far under the 16,384-token slot. The feature "
            "cache is a MISS by construction -- the legacy key is FNV-1a over the "
            "original media bytes -- which is correct here, because a hit would return "
            "features computed from the 24 kHz bytes that are the arm under test."
        ),
        "open_preconditions": [
            "SCORER ID RAIL: rails/adapters/audio2tool.py::gold resolves gold by EXACT "
            "sample_id (expected_by_id.get(sample.sample_id)), so an @16k id fails "
            "closed with 'is not in the frozen audio2tool probe receipt'. Earnings-22 "
            "already solved the same problem with reproduction.esb_reference."
            "published_segment_key, which splits on the FIRST '@' and is provably inert "
            "for unsuffixed ids. The equivalent one-line rail is NOT applied by the "
            "preparation that wrote this fragment; it is a named, reviewed change to a "
            "paper-facing path, and one rail unblocks @ts2, @16k and @16k+ts2 at once.",
        ],
        "authorizes": (
            "nothing. No contact, no server, no scoring and no Stage-3 activity. "
            "Composition and FlightRuntime.wire_check only."
        ),
    }
    if name == "16k+ts2":
        doc["open_preconditions"].append(
            "ORDER: cell (b) does not fly until cell (a) has flown and been read. Its "
            "comparator is the sealed 24 kHz run, so flown alone it confounds the tail "
            "with the standardization and neither factor can be separated."
        )
        doc["supersedes"] = {
            "experiment": "a2t-official-protocol-tail2s-400-v1",
            "cell_id": "R-official-tail2s",
            "condition": (
                "only if cell (a) R-official-16k admits the 16 kHz standardization; "
                "otherwise the 24 kHz-based @ts2 cell stands as written"
            ),
            "preregistration": (
                "docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md"
            ),
        }
    if smoke:
        doc["populations"] = [{"dataset_fragment": dataset, "ids": list(smoke_ids_)}]
    return doc


def emit(*, write: bool) -> list[tuple[str, str]]:
    products: list[tuple[str, dict[str, Any]]] = []
    for name, cell in CELLS.items():
        view = load_view(Path(cell["view"]))
        smoke = smoke_ids(view)
        dataset = str(cell["dataset"])
        experiment = str(cell["experiment"])
        products.extend(
            [
                (
                    f"configs/dataset/{dataset}.json",
                    dataset_fragment(name, view, subset=None),
                ),
                (
                    f"configs/dataset/{dataset}-smoke4.json",
                    dataset_fragment(name, view, subset=smoke),
                ),
                (
                    f"configs/experiment/{experiment}-v1.json",
                    experiment_fragment(name, smoke=False, smoke_ids_=()),
                ),
                (
                    f"configs/experiment/{experiment}-smoke-v1.json",
                    experiment_fragment(name, smoke=True, smoke_ids_=smoke),
                ),
            ]
        )
    emitted: list[tuple[str, str]] = []
    for relpath, document in products:
        payload = dumps(document)
        if write:
            (REPO / relpath).parent.mkdir(parents=True, exist_ok=True)
            (REPO / relpath).write_bytes(payload)
        emitted.append((relpath, hashlib.sha256(payload).hexdigest()))
    return emitted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the fragments")
    args = parser.parse_args()
    attempts = arm_offline_guard()
    if attempts.count:
        raise SystemExit("the offline guard recorded an outbound connection attempt")
    for relpath, digest in emit(write=args.write):
        print("%s  %s" % (digest[:16], relpath))
    if not args.write:
        print("(print only; pass --write to land the fragments)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
