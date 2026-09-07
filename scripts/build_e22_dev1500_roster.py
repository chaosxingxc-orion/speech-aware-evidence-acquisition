#!/usr/bin/env python3
"""Build ``E22-DEV-ESB-1500-V1``: the Earnings-22 dev subset for the model-usage cells.

Exposure row ``SAEA-SN-MF-E22-DEV1500-ROSTER-V1`` (``model-free-check``),
registered before the draw. Identity only: no model, tokenizer, embedder,
retriever, scorer, network, GPU or audio-decode contact, and nothing is read
that is not already a committed receipt or a derived WAV's bytes.

Three artifacts, every one of them a SUBSET of a committed one:

1. ``docs/receipts/rosters/e22-dev-esb-1500-v1.json`` -- the carrier-agnostic
   ``saea-roster-receipt-v1`` from the one shared
   :func:`core.roster.freeze_roster`, carrying the ``split_identity_hash`` an
   exposure row and a ``contracts.ExecutionPlan`` must both quote.
2. ``docs/checks/.../2026-09-06-e22-dev-esb-1500-v1/roster/flight-roster-receipt.json``
   -- the PROBE VIEW, in the ``saea-e22-esb-utterance-roster-receipt-v1`` shape
   ``scripts/flights/run_e22_esb_cell.py`` actually hydrates. Two receipt
   conventions coexist in this repository and neither can be retired: the
   roster receipt is the identity, this view is what a flight can load. It is
   produced by filtering the sealed dev10 receipt's own items to the drawn ids
   and recomputing every derived field by that receipt's own conventions.
3. ``docs/receipts/artifacts/d1-e22-esb-dev1500-utterances.json`` -- the D1
   media supplement in the shape ``contracts.gate_media_identity`` reads,
   filtered from the dev10 supplement with ``source_binding_sha256`` repointed
   at the new probe view.

**The media root is unchanged** (``derived/e22-esb-utterances/dev-v1/``). These
are the same bytes the sealed 2026-09-05 arms were served, which is exactly
what makes a cell on this subset pairable row for row against sealed arm A --
and it is why no clip is re-cut, no segment table re-extracted and no revision
re-pinned here.

**The WAVs are re-hashed, not copied on trust.** Every one of the 1,500 files
is read and digested and the result must equal the sealed supplement's own
recorded digest; a single mismatch refuses the whole build. The bytes are
hashed, never decoded.

Usage (WSL2)::

    python scripts/build_e22_dev1500_roster.py            # print only
    python scripts/build_e22_dev1500_roster.py --write
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

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
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

CARRIER = "earnings22-original"
ROSTER_ID = "E22-DEV-ESB-1500-V1"
SPLIT_NAME = "E22-ESB-DEV1500-UTTERANCES"
PER_CALL = 150
SEED = 20260906
ROSTER_SCHEMA = "saea-e22-esb-utterance-roster-receipt-v1"
SUPPLEMENT_SCHEMA = "saea-d1-media-supplement-v1"

#: The sealed dev10 artifacts this draw subsets, with the digests the
#: 2026-09-05 dataset fragment pins. Both are re-hashed on load; a drift is a
#: refusal, never a warning.
SOURCE_ROSTER_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-05-e22-dev-esb-prompt-ab-v1/roster/flight-roster-receipt.json"
)
SOURCE_ROSTER_SHA256 = "20437bcbde1a52b58bb48642d8809836e20073f7963f19b5ff836ead69c945c8"
SOURCE_SUPPLEMENT_RELPATH = "docs/receipts/artifacts/d1-e22-esb-dev10-utterances.json"
SOURCE_SUPPLEMENT_SHA256 = "ad01c4eca82b2739e121886fda5d95172756c9f232e5627b1f3f42274c2946a1"

OUT_ROSTER = REPO / "docs/receipts/rosters/e22-dev-esb-1500-v1.json"
OUT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-dev-esb-1500-v1/roster"
)
OUT_VIEW = OUT_DIR / "flight-roster-receipt.json"
OUT_SUPPLEMENT = REPO / "docs/receipts/artifacts/d1-e22-esb-dev1500-utterances.json"


class BuildError(RuntimeError):
    """An input drifted, a digest disagreed, or a derived field did not
    reproduce -- fail closed."""


def canonical_sha256(document: object) -> str:
    """The convention every Earnings-22 receipt in this repository uses."""

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
            f"{label} identity drift: the fragment pins {expected[:12]}..., "
            f"{path} now hashes to {measured[:12]}..."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def draw(source: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze the 1,500-row roster from the sealed dev10 items."""

    if source.get("schema") != ROSTER_SCHEMA:
        raise BuildError(f"source roster schema is {source.get('schema')!r}")
    candidates = [
        RosterItem(
            sample_id=str(item["sample_id"]),
            stratum=str(item["parent_sample_id"]),
            extra={
                "audio_seconds": float(item["audio_seconds"]),
                "media_relpath": str(item["media_relpath"]),
            },
        )
        for item in source["items"]
    ]
    return freeze_roster(
        carrier_lock_key=CARRIER,
        candidates=candidates,
        per_stratum=PER_CALL,
        seed=SEED,
        split_role="dev",
        roster_id=ROSTER_ID,
        roster_role=EVALUATION_ROSTER_ROLE,
    )


def probe_view(source: Mapping[str, Any], sample_ids: Sequence[str]) -> dict[str, Any]:
    """The sealed dev10 receipt, filtered to the drawn ids.

    Every derived field is recomputed by the source receipt's own conventions
    rather than copied: a receipt whose ``count`` still said 6,038 would
    describe a population no cell is flying.
    """

    keep = set(sample_ids)
    entries = [item for item in source["items"] if str(item["sample_id"]) in keep]
    if len(entries) != len(keep):
        raise BuildError(
            f"the probe view kept {len(entries)} items for {len(keep)} drawn ids"
        )
    ids = [str(item["sample_id"]) for item in entries]
    if ids != sorted(ids):
        raise BuildError("the source roster's items are not in sample-id order")
    calls = sorted({str(item["parent_sample_id"]) for item in entries})
    view: dict[str, Any] = {
        "schema": ROSTER_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "carrier": CARRIER,
        "split_name": SPLIT_NAME,
        "split_role": "dev",
        "split_role_basis": (
            "A 1,500-row SUBSET of this study's own registered earnings22-original dev "
            "subset10, drawn by core.roster.freeze_roster at 150 per source call with "
            f"seed {SEED} (roster receipt {OUT_ROSTER.relative_to(REPO).as_posix()}). "
            "No owner allowance is involved and none is claimed: dev is the split this "
            "study may optimize on, and every id here was already read by the sealed "
            "2026-09-05 arms. No confirmatory call is named, loaded, decoded or scored, "
            "and the six calibration-exposed ESB test calls stay a separate population "
            "with a separate roster, reference layer and derived media root."
        ),
        "version": str(source["version"]),
        "source_segment_table": dict(source["source_segment_table"]),
        "derived_from": {
            "roster_receipt": SOURCE_ROSTER_RELPATH,
            "roster_receipt_sha256": SOURCE_ROSTER_SHA256,
            "rule": (
                f"core.roster.freeze_roster, per_stratum={PER_CALL} by source call, "
                f"seed={SEED}, roster_role=evaluation, no exclusions"
            ),
            "media_root_unchanged": True,
            "media_root_basis": (
                "The drawn items keep the sealed dev-v1 media_relpath and audio_sha256, "
                "so a cell on this subset is paired row for row against the sealed arm A "
                "outputs on identical bytes. Nothing is re-cut."
            ),
        },
        "sample_rate_hz": int(source["sample_rate_hz"]),
        "decoder": str(source["decoder"]),
        "writer": str(source["writer"]),
        "count": len(entries),
        "audio_seconds_total": round(
            sum(float(item["audio_seconds"]) for item in entries), 6
        ),
        "audio_seconds_longest_item": round(
            max(float(item["audio_seconds"]) for item in entries), 6
        ),
        "audio_seconds_shortest_item": round(
            min(float(item["audio_seconds"]) for item in entries), 6
        ),
        "clamped_to_decoded_parent": sorted(
            str(item["sample_id"])
            for item in entries
            if bool(item["end_clamped_to_decoded_parent"])
        ),
        "per_call": {
            call: {
                "utterances": sum(
                    1 for item in entries if str(item["parent_sample_id"]) == call
                ),
                "audio_seconds": round(
                    sum(
                        float(item["audio_seconds"])
                        for item in entries
                        if str(item["parent_sample_id"]) == call
                    ),
                    6,
                ),
            }
            for call in calls
        },
        "ids_sha256": ids_sha256(ids),
        "items": entries,
    }
    view["items_sha256"] = canonical_sha256(entries)
    return view


def supplement(
    source: Mapping[str, Any],
    sample_ids: Sequence[str],
    *,
    view_sha256: str,
    root: Path,
    rehash: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """The D1 media supplement, filtered and (by default) re-hashed off disk.

    The schema is exact-keyed by ``contracts.gate_media_identity``, so the
    re-hash evidence cannot live inside the document; it is returned beside it
    and written into the build receipt instead.
    """

    if source.get("schema") != SUPPLEMENT_SCHEMA:
        raise BuildError(f"source supplement schema is {source.get('schema')!r}")
    keep = set(sample_ids)
    manifest = [entry for entry in source["manifest"] if str(entry["id"]) in keep]
    if len(manifest) != len(keep):
        raise BuildError(
            f"the supplement kept {len(manifest)} entries for {len(keep)} drawn ids"
        )
    checked = 0
    for entry in manifest:
        if not rehash:
            continue
        path = Path(root) / str(entry["media_relpath"])
        measured = sha256_file(path)
        if measured != str(entry["sha256"]):
            raise BuildError(
                f"media identity drift on {entry['id']}: the sealed supplement records "
                f"{str(entry['sha256'])[:12]}..., {path} now hashes to {measured[:12]}..."
            )
        if path.stat().st_size != int(entry["bytes"]):
            raise BuildError(f"media byte-count drift on {entry['id']}")
        checked += 1
    ids = [str(entry["id"]) for entry in manifest]
    document = {
        "schema": SUPPLEMENT_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "carrier_lock_key": CARRIER,
        "parent_d1_sha256": str(source["parent_d1_sha256"]),
        "source_binding_sha256": view_sha256,
        "count": len(manifest),
        "ids_sha256": ids_sha256(ids),
        "manifest": manifest,
        "manifest_sha256": canonical_sha256(manifest),
        "total_bytes": sum(int(entry["bytes"]) for entry in manifest),
    }
    evidence = {
        "files_rehashed": checked,
        "rehash_requested": rehash,
        "all_digests_matched_the_sealed_supplement": bool(rehash) and checked == len(manifest),
        "audio_samples_decoded": 0,
    }
    return document, evidence


def build(*, write: bool, rehash: bool) -> dict[str, Any]:
    attempts = arm_offline_guard()
    root = Path(data_root())
    source_roster = load_pinned(
        SOURCE_ROSTER_RELPATH, SOURCE_ROSTER_SHA256, "dev10 flight roster receipt"
    )
    source_supplement = load_pinned(
        SOURCE_SUPPLEMENT_RELPATH, SOURCE_SUPPLEMENT_SHA256, "dev10 D1 media supplement"
    )

    receipt = draw(source_roster)
    sample_ids = [str(item["sample_id"]) for item in receipt["items"]]
    view = probe_view(source_roster, sample_ids)
    view_bytes = (
        json.dumps(view, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    view_sha256 = hashlib.sha256(view_bytes).hexdigest()
    media, evidence = supplement(
        source_supplement,
        sample_ids,
        view_sha256=view_sha256,
        root=root,
        rehash=rehash,
    )
    media_bytes = (
        json.dumps(media, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")

    build_receipt = {
        "schema": "saea-e22-dev1500-roster-build-receipt-v1",
        "exposure_row": "SAEA-SN-MF-E22-DEV1500-ROSTER-V1",
        "execution_profile": "model-free-check",
        "roster_id": ROSTER_ID,
        "split_name": SPLIT_NAME,
        "split_role": "dev",
        "seed": SEED,
        "per_stratum": PER_CALL,
        "count": len(sample_ids),
        "split_identity_hash": receipt["split_identity_hash"],
        "strata_counts": receipt["strata_counts"],
        "audio_seconds_total": view["audio_seconds_total"],
        "audio_seconds_longest_item": view["audio_seconds_longest_item"],
        "audio_seconds_shortest_item": view["audio_seconds_shortest_item"],
        "clamped_to_decoded_parent": view["clamped_to_decoded_parent"],
        "sources": {
            "roster_receipt": SOURCE_ROSTER_RELPATH,
            "roster_receipt_sha256": SOURCE_ROSTER_SHA256,
            "d1_media_supplement": SOURCE_SUPPLEMENT_RELPATH,
            "d1_media_supplement_sha256": SOURCE_SUPPLEMENT_SHA256,
        },
        "outputs": {
            "roster_receipt": OUT_ROSTER.relative_to(REPO).as_posix(),
            "roster_receipt_sha256": hashlib.sha256(
                canonical_receipt_bytes(receipt)
            ).hexdigest(),
            "probe_view": OUT_VIEW.relative_to(REPO).as_posix(),
            "probe_view_sha256": view_sha256,
            "d1_media_supplement": OUT_SUPPLEMENT.relative_to(REPO).as_posix(),
            "d1_media_supplement_sha256": hashlib.sha256(media_bytes).hexdigest(),
        },
        "media_identity": evidence,
        "contacts": {
            "frozen_core": 0,
            "tokenizer": 0,
            "embedder": 0,
            "retriever": 0,
            "scorer": 0,
            "network": 0,
            "gpu_hours": 0,
            "audio_seconds_decoded": 0,
            "paid_api_spend": 0,
            "outbound_connection_attempts": attempts.count,
            "outbound_connection_targets": list(attempts.targets),
        },
        "opened": {
            "reference_sentences": 0,
            "sealed_outputs": 0,
            "scores": 0,
            "test_split_artifacts": 0,
        },
    }

    if write:
        write_roster(receipt, OUT_ROSTER)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        OUT_VIEW.write_bytes(view_bytes)
        OUT_SUPPLEMENT.write_bytes(media_bytes)
        write_json_artifact(OUT_DIR / "build-receipt.json", build_receipt)
    return build_receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the three receipts")
    parser.add_argument(
        "--no-rehash",
        action="store_true",
        help="skip the per-file SHA-256 pass (for a dry run without the data root)",
    )
    args = parser.parse_args()

    receipt = build(write=args.write, rehash=not args.no_rehash)
    print(
        f"{receipt['roster_id']}: {receipt['count']} rows, "
        f"{receipt['audio_seconds_total']:.3f} s "
        f"({receipt['audio_seconds_total'] / 3600.0:.4f} h), "
        f"identity {receipt['split_identity_hash']}"
    )
    print(f"  strata: {receipt['strata_counts']}")
    print(
        f"  media: {receipt['media_identity']['files_rehashed']} files re-hashed, "
        f"0 samples decoded"
    )
    for name, value in sorted(receipt["outputs"].items()):
        print(f"  {name}: {value}")
    if args.write:
        print("wrote the roster receipt, the probe view and the D1 supplement")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
