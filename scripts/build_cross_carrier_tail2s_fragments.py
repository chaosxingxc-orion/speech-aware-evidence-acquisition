#!/usr/bin/env python3
"""Emit the config fragments the cross-carrier ``@ts2`` cells compose from.

Model-free, zero contacts. Under the media rows
``SAEA-SN-MF-SLURP-DEV1000-TS2-MEDIA-V1`` and
``SAEA-SN-MF-A2T-CAL400-TS2-MEDIA-V1``, whose artifacts this reads and whose
scope already covers writing the fragments that name them. **No cell is flown
and no request is built here**; each cell still needs its own preregistration,
its own owner GO and its own exposure row.

Two carriers, not three
-----------------------
SLURP and Audio2Tool both fly through ``core.flight.FlightRuntime``, so both get
a dataset fragment, an experiment fragment and a 4-row smoke, and both can be
driven end to end by ``FlightRuntime.wire_check`` with zero sockets.

**Earnings-21 deliberately gets none.** Its 90-second windows are cut at RUNTIME
by ``reproduction.obs_loop`` from each whole call, nothing in the harness
consumes pre-cut slices, and the full-44 baseline flies through
``core.driver.run_experiment_bundled`` rather than ``FlightRuntime``. A dataset
fragment naming the ``@ts2`` window media would compose and could not fly, which
is worse than none. What Earnings-21 needs is stated in the preregistration and
is one named obs knob, for which the committed ``@ts2`` media is the byte-exact
oracle.

The SLURP runtime view's ``split_identity_hash`` is the value ``load_split``
returns -- ``data.splits.split_identity_hash`` over ``slurp/<sample_id>`` --
computed here rather than copied, exactly as ``scripts/build_dev1000_runtime_
view.py`` computes it for the sealed view.

Usage (WSL2)::

    python scripts/build_cross_carrier_tail2s_fragments.py
    python scripts/build_cross_carrier_tail2s_fragments.py --write
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
SLURP_VIEW = CHECKS / "2026-09-07-slurp-dev1000-tail2s-media/roster/flight-roster-receipt.json"
A2T_VIEW = CHECKS / "2026-09-07-a2t-calibration-400-tail2s-media/roster/flight-roster-receipt.json"

#: The four rows each carrier's dry run flies, fixed HERE and in the committed
#: fragment rather than on a command line, so a smoke can never quietly fly four
#: different rows than the ones its exposure row names.
SMOKE_SIZE = 4


class FragmentError(RuntimeError):
    """An input drifted or a derived identity did not reproduce."""


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


def dumps(document: object) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def load_view(path: Path) -> Mapping[str, Any]:
    view = json.loads(path.read_text(encoding="utf-8"))
    if view["schema"] != "saea-cross-carrier-ts2-probe-view-v1":
        raise FragmentError(f"{path} is not a cross-carrier @ts2 probe view")
    ids = [str(item["sample_id"]) for item in view["items"]]
    if hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest() != view["ids_sha256"]:
        raise FragmentError(f"{path} ids_sha256 does not reproduce")
    return view


def smoke_ids(view: Mapping[str, Any]) -> list[str]:
    """One row per stratum where possible, else the first ``SMOKE_SIZE`` ids.

    Deterministic and derived, never drawn: the strata are visited in sorted
    order and each contributes its own first id, so the same view always yields
    the same four rows.
    """

    by_stratum: dict[str, list[str]] = {}
    for item in view["items"]:
        by_stratum.setdefault(str(item["stratum"]), []).append(str(item["sample_id"]))
    picked: list[str] = []
    for stratum in sorted(by_stratum):
        picked.append(sorted(by_stratum[stratum])[0])
        if len(picked) == SMOKE_SIZE:
            return sorted(picked)
    # Fewer strata than rows wanted (SLURP has one): top up from the whole
    # population in id order until exactly SMOKE_SIZE distinct ids are held.
    chosen = list(dict.fromkeys(picked))
    for sample_id in sorted(str(item["sample_id"]) for item in view["items"]):
        if len(chosen) == SMOKE_SIZE:
            break
        if sample_id not in chosen:
            chosen.append(sample_id)
    if len(chosen) != SMOKE_SIZE:
        raise FragmentError("the view carries fewer rows than the smoke needs")
    return sorted(chosen)


# ---------------------------------------------------------------------------
# SLURP
# ---------------------------------------------------------------------------


def slurp_runtime_view(view: Mapping[str, Any], *, subset: Sequence[str] | None) -> dict:
    """The ``saea-speech-native-runtime-view-v1`` shape the SLURP flight hydrates."""

    wanted = set(subset) if subset is not None else None
    items = [
        {
            "audio_seconds": float(item["audio_seconds"]),
            "audio_sha256": str(item["audio_sha256"]),
            "media_relpath": str(item["media_relpath"]),
            "packet_id": str(item["packet_id"]),
            "sample_id": str(item["sample_id"]),
            "sample_rate_hz": int(item["sample_rate_hz"]),
        }
        for item in view["items"]
        if wanted is None or str(item["sample_id"]) in wanted
    ]
    if wanted is not None and len(items) != len(wanted):
        raise FragmentError("the smoke subset names an id the view does not carry")
    identity = split_identity_hash(
        prefixed("slurp", [str(row["sample_id"]) for row in items])
    )
    supplement = "docs/receipts/artifacts/d1-slurp-dev1000-tail2s.json"
    unsigned = {
        "audio_seconds_total": round(
            sum(float(row["audio_seconds"]) for row in items), 7
        ),
        "carrier_lock_key": "slurp",
        "count": len(items),
        # Unlike the sealed DEV-1000 view, this population DOES need a
        # supplement: the @ts2 files are new media outside the base D1 SLURP
        # closure that covers the sealed 1,000.
        "d1_manifest_sha256": None,
        "d1_media_supplement": supplement.removeprefix("docs/"),
        "d1_media_supplement_sha256": sha256_file(REPO / supplement),
        # The variant lives under its own derived root, so payload confinement
        # binds to that root instead of datasets/slurp. The runner reads this
        # key through the carrier_root_resolver seam FlightRuntime already
        # exposes and run_e22_esb_cell.py already uses.
        "derived_media_subdir": "derived/slurp-dev1000-tail2s-v1",
        "items": items,
        "schema": "saea-speech-native-runtime-view-v1",
        # Recorded for reproducibility only: this view freezes an ALREADY
        # complete population, so no seed can change its membership.
        "seed": 20260907,
        "source_binding_sha256": str(view["items_sha256"]),
        "split_identity_hash": identity,
        "split_name": "DEV-1000-TAIL2S" if subset is None else "DEV-1000-TAIL2S-SMOKE-4",
        "split_role": "dev",
        "status": (
            "MODEL-FREE, LABEL-FREE ENGINEERING INPUT; NOT AN EXPOSURE REGISTRATION. "
            "The @ts2 media of the sealed DEV-1000 comparator population. This view "
            "grants no contact authority and the cell it names is not authorized; the "
            "packets it points at do not exist until a separately registered CPU-only "
            "encode pass materializes them."
        ),
        "study": "speech-aware-evidence-acquisition",
        "variant_of": {
            "sealed_view": "configs/dataset/slurp-speech-native-dev1000.json",
            "sealed_view_sha256": (
                "f92846760b3657ba50009e52f98fcec96df27c16ac66ea57467b4f8fa42f288d"
            ),
            "sealed_split_identity_hash": (
                "8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84"
            ),
            "rule": str(view["rule"]),
            "media_build_receipt": (
                "docs/checks/speech-aware-evidence-acquisition/"
                "2026-09-07-slurp-dev1000-tail2s-media/build-receipt.json"
            ),
        },
    }
    return {**unsigned, "runtime_view_sha256": canonical_sha256(unsigned)}


SLURP_PACKET_ROOT = "/home/chao/feat-cache/slurp-dev1000-ts2-packets-04ccc72a"


def slurp_model_fragment() -> dict:
    """The comparator's own geometry, pointed at the variant's packet root.

    Every server argument, the decoding block, the prompt order and the slot
    count are the sealed comparator's byte for byte. The ONLY difference is
    which packet root the decoder reads, which is the whole point: the media is
    the single factor and the serving path is not.
    """

    sealed = json.loads(
        (
            REPO
            / "configs/model"
            / "q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64.json"
        ).read_text(encoding="utf-8")
    )
    fragment = dict(sealed)
    fragment["speech_feature_root"] = SLURP_PACKET_ROOT
    fragment["server_env"] = {
        **dict(sealed["server_env"]),
        "LLAMA_SPEECH_FEATURE_ROOT": SLURP_PACKET_ROOT,
    }
    fragment["variant_basis"] = (
        "IDENTICAL to q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-"
        "max64 except speech_feature_root / LLAMA_SPEECH_FEATURE_ROOT, which point at "
        "the @ts2 packet root instead of the comparator's. Same -c 65536 -np 8, same "
        "decoding, same prompt order, same decoder sha256. The packets in that root do "
        "NOT exist yet: they are produced by the separately registered CPU-only encode "
        "pass the media build receipt's packet_promotion_plan specifies."
    )
    return fragment


def slurp_experiment(*, smoke: bool, smoke_ids_: Sequence[str]) -> dict:
    dataset = (
        "slurp-speech-native-dev1000-tail2s-smoke4"
        if smoke
        else "slurp-speech-native-dev1000-tail2s"
    )
    run_id = (
        "SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-SMOKE-V1"
        if smoke
        else "SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-V1"
    )
    count = SMOKE_SIZE if smoke else 1000
    doc: dict[str, Any] = {
        "experiment_id": run_id,
        "purpose": (
            "SLURP arm of the cross-carrier silence-tail probe. ONE factor, the MEDIA: "
            "exactly 2.0 s of digital silence appended to every one of the 1,000 sealed "
            "devel recordings. The prompt, the roster membership, the build, the "
            "geometry and the decoding are the sealed "
            "SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1 comparator's, byte for byte; the "
            "only other difference is which packet root the mmproj-free decoder reads, "
            "which is forced by the media change because the legacy feature-cache key "
            "is FNV-1a over the original media bytes. This fragment authorizes NOTHING: "
            "the cell needs its own owner GO, its own exposure row, and a separately "
            "registered CPU-only encode pass to materialize its packets."
            + (
                " This is the 4-row dry run that must pass before the 1,000 contacts."
                if smoke
                else ""
            )
        ),
        "split_id": "DEV-1000-TAIL2S" + ("-SMOKE-4" if smoke else ""),
        "execution_plan": {
            "execution_profile": "baseline-reproduction",
            "split_role": "dev",
            "planned_model_calls": 8 if smoke else 1050,
            "planned_gpu_hours": 0.05 if smoke else 0.30,
            "planned_speech_audio_seconds": 60 if smoke else 5000,
        },
        "cells": [
            {
                "cell_id": "closed-list-tail2s" + ("-smoke-4" if smoke else ""),
                "arm": "speech-feature-query",
                # NOT the comparator's own "slurp-direct-closed-list" (which is
                # what this generator first emitted): the @ts2 packets exist
                # now, and c1f63599 pinned their promotion receipt into a
                # dedicated baseline fragment -- byte for byte the sealed
                # DEV-1000 closed-list arm except that receipt (+sha256) and
                # two per-cell speech-feature identity ids. Pointing the cells
                # at it is what keeps the media contrast single-factor. That
                # was a hand edit to the two committed fragments; re-pointing
                # the generator is what makes --write reproduce them again.
                "baseline_fragment": "slurp-direct-closed-list-tail2s",
                "model_fragment": "q4km-mmproj-free-speech-native-np8-ts2-packets-max64",
                "dataset_fragment": dataset,
            }
        ],
        "comparator": {
            "run_id": "SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1",
            "attempt_id": "attempt-20260905T060424Z-2c5596",
            "config_hash": (
                "6be064ba49d4b3b8b430aa063b4fef46a898ce5a0b3702fe35c4896d5d1b894f"
            ),
            "protocol_hash": (
                "7e83a70508068d1a1c2512cabbc91b8417821ae5796038c2bc6fa4950bb951b2"
            ),
            "split_identity_hash": (
                "8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84"
            ),
            "paper_facing_scorer": "slurp-slu-official-projected-v2",
            "sealed_official_projected_v2": {
                "scenario": 82.60,
                "action": 74.60,
                "intent_scen_act": 73.10,
                "entities_strict": 21.91,
                "word_f1": 33.69,
                "char_f1": 38.20,
                "slu_f1": 35.80,
                "unparsed": 3,
                "n": 1000,
            },
        },
        "preregistration": (
            "docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md"
        ),
        "media": {
            "build_receipt": (
                "docs/checks/speech-aware-evidence-acquisition/"
                "2026-09-07-slurp-dev1000-tail2s-media/build-receipt.json"
            ),
            "exposure_row": "SAEA-SN-MF-SLURP-DEV1000-TS2-MEDIA-V1",
            "count": count,
        },
        "open_preconditions": [
            "PACKETS: the @ts2 packet root does not exist. A separately registered "
            "bounded-discovery-probe row must run the CPU-only sidecar encode (1,000 "
            "contacts, 0 GPU-h) and promote the packets before this cell can serve.",
            "SCORER ID RAIL: core.scorers 'slurp-slu-official-projected-v2' resolves "
            "gold by EXACT sample_id, so an @ts2 id fails closed at scoring. Earnings-22 "
            "already solved the same problem with reproduction.esb_reference."
            "published_segment_key, which splits on '@' and is provably inert for "
            "unsuffixed ids. The equivalent one-line rail for SLURP is NOT applied by "
            "the preparation that wrote this fragment; it is a named, reviewed change to "
            "a paper-facing scorer.",
        ],
        "authorizes": (
            "nothing. No contact, no server, no scoring and no Stage-3 activity. "
            "Composition and FlightRuntime.wire_check only."
        ),
    }
    if smoke:
        doc["populations"] = [
            {"dataset_fragment": dataset, "ids": list(smoke_ids_)},
        ]
    return doc


# ---------------------------------------------------------------------------
# Audio2Tool
# ---------------------------------------------------------------------------


def a2t_dataset(view: Mapping[str, Any], *, subset: Sequence[str] | None) -> dict:
    supplement = "docs/receipts/artifacts/d1-a2t-calibration-400-tail2s.json"
    wanted = set(subset) if subset is not None else None
    items = [
        item for item in view["items"] if wanted is None or str(item["sample_id"]) in wanted
    ]
    if wanted is not None and len(items) != len(wanted):
        raise FragmentError("the smoke subset names an id the view does not carry")
    ids = [str(item["sample_id"]) for item in items]
    return {
        "carrier_lock_key": "audio2tool",
        "split_id": "A2T-CALIBRATION-400-TS2" + ("-SMOKE-4" if subset else ""),
        "a2t_calibration_subset_receipt": str(A2T_VIEW.relative_to(REPO).as_posix()),
        "a2t_calibration_subset_receipt_sha256": sha256_file(A2T_VIEW),
        "a2t_calibration_split_name": "A2T-CALIBRATION-400-TAIL2S"
        + ("-SMOKE-4" if subset else ""),
        "a2t_calibration_split_role": "discovery",
        "a2t_calibration_split_identity_hash": hashlib.sha256(
            "\n".join(sorted(ids)).encode("utf-8")
        ).hexdigest(),
        "a2t_calibration_flight_split_identity_hash": split_identity_hash(
            prefixed("audio2tool", ids)
        ),
        "a2t_calibration_identity_hash_conventions": (
            "a2t_calibration_split_identity_hash is SHA-256 over the LF-joined sorted "
            "@ts2 sample ids of THIS variant; a2t_calibration_flight_split_identity_hash "
            "is data.splits.split_identity_hash(prefixed('audio2tool', sample_ids)), the "
            "value core.flight.FlightRuntime.preflight computes at flight time. Both "
            "differ from the sealed frozen 400's, which is the identity separation the "
            "@ts2 suffix exists to guarantee."
        ),
        "a2t_calibration_count": len(items),
        "a2t_calibration_audio_seconds_total": round(
            sum(float(item["audio_seconds"]) for item in items), 6
        ),
        "a2t_calibration_audio_seconds_longest_item": round(
            max(float(item["audio_seconds"]) for item in items), 6
        ),
        "a2t_calibration_sample_rate_hz": 24000,
        # The variant lives under its own derived root, so payload confinement
        # binds to that root instead of datasets/audio2tool. The runner reads
        # this key through the carrier_root_resolver seam FlightRuntime already
        # exposes and run_e22_esb_cell.py already uses.
        "a2t_calibration_derived_subdir": "derived/a2t-calibration-400-tail2s-v1",
        # BOTH SPELLINGS, AND THEY MUST AGREE. The carrier-prefixed pair is
        # what ``core.base.declared_derived_media_roots`` reads to vouch for
        # the derived root above; the PLAIN pair is what ``core.config.
        # d1_media_supplement_relpath`` -- and therefore the media IDENTITY
        # gate ``core.flight.FlightRuntime.preflight`` constructs -- reads.
        # The SLURP view above has always carried the plain pair; this
        # Audio2Tool fragment carried only the prefixed one, which satisfied
        # confinement and left the identity gate seeing no supplement at all
        # (2026-09-09, docs/readiness/
        # 2026-09-09-a2t-derived-media-d1-declaration-fix-v1.md).
        # ``core.config.assert_d1_media_supplement_spellings_agree`` now
        # refuses any fragment where these four values disagree.
        "a2t_calibration_d1_media_supplement": supplement.removeprefix("docs/"),
        "a2t_calibration_d1_media_supplement_sha256": sha256_file(REPO / supplement),
        "d1_media_supplement": supplement.removeprefix("docs/"),
        "d1_media_supplement_sha256": sha256_file(REPO / supplement),
        "a2t_calibration_d1_basis": (
            "Unlike the sealed frozen 400 -- whose ids are inside the base D1 closure and "
            "which therefore declares NO supplement -- the @ts2 ids are new media that "
            "duplicate nothing in that closure, so an additive supplement is both needed "
            "and legal under contracts.gate_media_identity."
        ),
        "a2t_calibration_exposure": (
            "The same frozen 400 discovery split, re-encoded. Nothing is drawn. Media row "
            "SAEA-SN-MF-A2T-CAL400-TS2-MEDIA-V1. This fragment grants no contact authority."
        ),
        "a2t_calibration_media_build_receipt": (
            "docs/checks/speech-aware-evidence-acquisition/"
            "2026-09-07-a2t-calibration-400-tail2s-media/build-receipt.json"
        ),
    }


def a2t_experiment(*, smoke: bool, smoke_ids_: Sequence[str]) -> dict:
    dataset = (
        "audio2tool-calibration-400-tail2s-smoke4"
        if smoke
        else "audio2tool-calibration-400-tail2s"
    )
    run_id = (
        "SAEA-A2T-OFFICIAL-PROTOCOL-TAIL2S-SMOKE-V1"
        if smoke
        else "SAEA-A2T-OFFICIAL-PROTOCOL-TAIL2S-V1"
    )
    doc: dict[str, Any] = {
        "experiment_id": run_id,
        "schema": "saea-a2t-direct-calibration-experiment-v1",
        "date": "2026-09-07",
        "execution_profile": "baseline-reproduction",
        "purpose": (
            "Audio2Tool arm of the cross-carrier silence-tail probe. ONE factor, the "
            "MEDIA: exactly 2.0 s of digital silence appended to every one of the 400 "
            "sealed frozen-400 wavs (48,000 zero samples at the release's own 24 kHz). "
            "The published system message, the compact 152-row registry, the user turn, "
            "the geometry, the decoding and the official scorer are the sealed "
            "SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1 cell R-official-raw's, byte for "
            "byte. This fragment authorizes NOTHING: the cell needs its own owner GO and "
            "its own exposure row."
            + (
                " This is the 4-row dry run that must pass before the 400 contacts."
                if smoke
                else ""
            )
        ),
        "population": {
            "carrier": "audio2tool",
            "split_name": "A2T-CALIBRATION-400-TAIL2S" + ("-SMOKE-4" if smoke else ""),
            "split_role": "discovery",
            "dataset_fragment": dataset,
            "count": SMOKE_SIZE if smoke else 400,
            "media_exposure_row": "SAEA-SN-MF-A2T-CAL400-TS2-MEDIA-V1",
        },
        "cells": [
            {
                "cell_id": "R-official-tail2s" + ("-smoke-4" if smoke else ""),
                "factor": (
                    "the media, and only the media: +2.0 s of digital silence after the "
                    "sealed samples"
                ),
                "arm": "bare-core",
                "baseline_fragment": "a2t-direct-official-protocol",
                "model_fragment": "q4km-featcache-a2t-official-04ccc72a",
                "dataset_fragment": dataset,
            }
        ],
        "execution_plan": {
            "execution_profile": "baseline-reproduction",
            "split_role": "discovery",
            "planned_model_calls": 8 if smoke else 408,
            "planned_gpu_hours": 0.05 if smoke else 0.20,
            "planned_speech_audio_seconds": 120 if smoke else 3100,
        },
        "comparator": {
            "run_id": "SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1",
            "attempt_id": "attempt-20260904T135250Z-rofficialraw",
            "cell_id": "R-official-raw",
            "config_hash": (
                "0e56ce8f2e71d1e4e8702433ae7c997aacf4e548414100bad5a1d9b9c8ef5165"
            ),
            "protocol_hash": (
                "6da614b22de0001760b0263f6026483373ce190d801cc8dd9008e34bb595aa8a"
            ),
            "split_identity_hash": (
                "e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c"
            ),
            "paper_facing_scorer": "a2t-toolcall-official",
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
        },
        "preregistration": (
            "docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md"
        ),
        "open_preconditions": [
            "SCORER ID RAIL: reproduction.a2t_scorer resolves gold by EXACT sample_id "
            "(expected_by_id.get(sample_id)), so an @ts2 id fails closed at scoring with "
            "'is not in the frozen audio2tool ...'. Earnings-22 already solved the same "
            "problem with reproduction.esb_reference.published_segment_key, which splits "
            "on '@' and is provably inert for unsuffixed ids. The equivalent one-line "
            "rail for Audio2Tool is NOT applied by the preparation that wrote this "
            "fragment; it is a named, reviewed change to a paper-facing scorer."
        ],
        "authorizes": (
            "nothing. No contact, no server, no scoring and no Stage-3 activity. "
            "Composition and FlightRuntime.wire_check only."
        ),
    }
    if smoke:
        doc["populations"] = [{"dataset_fragment": dataset, "ids": list(smoke_ids_)}]
    return doc


# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------


def emit(*, write: bool) -> list[tuple[str, str]]:
    slurp = load_view(SLURP_VIEW)
    a2t = load_view(A2T_VIEW)
    slurp_smoke = smoke_ids(slurp)
    a2t_smoke = smoke_ids(a2t)

    products: list[tuple[str, dict]] = [
        (
            "configs/dataset/slurp-speech-native-dev1000-tail2s.json",
            slurp_runtime_view(slurp, subset=None),
        ),
        (
            "configs/dataset/slurp-speech-native-dev1000-tail2s-smoke4.json",
            slurp_runtime_view(slurp, subset=slurp_smoke),
        ),
        (
            "configs/model/q4km-mmproj-free-speech-native-np8-ts2-packets-max64.json",
            slurp_model_fragment(),
        ),
        (
            "configs/experiment/slurp-dev1000-closed-list-tail2s-v1.json",
            slurp_experiment(smoke=False, smoke_ids_=()),
        ),
        (
            "configs/experiment/slurp-dev1000-closed-list-tail2s-smoke-4-v1.json",
            slurp_experiment(smoke=True, smoke_ids_=slurp_smoke),
        ),
        (
            "configs/dataset/audio2tool-calibration-400-tail2s.json",
            a2t_dataset(a2t, subset=None),
        ),
        (
            "configs/dataset/audio2tool-calibration-400-tail2s-smoke4.json",
            a2t_dataset(a2t, subset=a2t_smoke),
        ),
        (
            "configs/experiment/a2t-official-protocol-tail2s-400-v1.json",
            a2t_experiment(smoke=False, smoke_ids_=()),
        ),
        (
            "configs/experiment/a2t-official-protocol-tail2s-400-smoke-v1.json",
            a2t_experiment(smoke=True, smoke_ids_=a2t_smoke),
        ),
    ]
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
