"""Build the DEV-500 label-free runtime view from its probe-sample receipt.

Sibling of ``scripts/build_dev100_runtime_view.py`` (DEV-500 confirmatory
prep prerequisite #1, ``docs/readiness/2026-08-24-dev500-confirmatory-
preregistration.md`` section 4). The DEV ladder's identity comes from the
committed probe-sample receipt ``docs/receipts/probe-samples/DEV-500.json``
(owner ruling ``2026-08-23-knowledge-plane-baseline-rulings.md`` section
2.2), not from a train binding, so the train-only ``e0.d1_identity``
builders stay untouched and this generator reproduces the SAME output
schema over that receipt.

Canonical-recording rule — IDENTICAL to the DEV-100 fragment's, by
construction: the recording per utterance is NOT chosen here at all. The
DEV-500 receipt already froze exactly one recording per selected utterance
via ``random.Random(f"{seed}:{scenario}:{utterance_id}")`` over the
utterance's id-sorted recordings (``scripts/build_dev_ladder.py``,
recorded verbatim in the receipt's own ``selection_rule``), and this
generator consumes those exact sample ids verbatim — the same consume-
verbatim discipline the committed DEV-100 view used. The 100 DEV-100
members are an exact seeded subset of DEV-500 (receipt ``nesting`` block),
so their ``sample_id``/``packet_id`` values here are byte-identical to the
DEV-100 view's and their already-promoted packet identities carry over
unchanged.

What is (and is not) read: only ``media_relpath`` is consumed from the
SLURP devel loader; scenario, action, intent, entity, and transcript
fields are never copied into the output. The view is a label-free
engineering input and carries no exposure.

Identity discipline (the E108 lesson, carried verbatim from the DEV-100
generator): the receipt carries BOTH hash conventions —

* ``split_identity_hash`` — colon-keyed receipt-integrity value
  ``load_verified_probe_split`` recomputes fail-closed;
* ``run_identity_hash`` — slash-prefixed run identity ``load_split`` /
  ``ExecutionPlan`` / ``protocol_hash`` use.

This runtime view embeds the SECOND value in its ``split_identity_hash``
field so the fragment and any later plan agree by construction; the
generator verifies both conventions and refuses on disagreement.

``source_binding_sha256`` carries the canonical-JSON SHA-256 of the
DEV-500 probe-sample receipt document (no speech-native binding exists for
a DEV-ladder view; same substitution as DEV-100, recorded here).

No D1 media supplement (measured, not assumed): base D1's slurp media
layer records all 8,690 devel recordings, so every DEV-500 item must fall
inside that closure with byte-identical media. The generator PROVES that
item by item (id, size, SHA-256 against ``d1-identity.json``) and writes
the supplement triple as null, refusing outright on any uncovered or
drifted item — never emitting a supplement the gate would reject.

Run in WSL2 (data root on /mnt/e):

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \
      python scripts/build_dev500_runtime_view.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402
from speech_aware_evidence_acquisition.e0.d1_identity import (  # noqa: E402
    _confined_media_path,
    _probe_speech_media,
)
from speech_aware_evidence_acquisition.reproduction.probe_split import (  # noqa: E402
    load_verified_probe_split,
)

SPLIT_NAME = "DEV-500"
SPLIT_ROLE = "dev"
CARRIER = "slurp"
RECEIPT_PATH = REPO_ROOT / "docs" / "receipts" / "probe-samples" / f"{SPLIT_NAME}.json"
NESTED_RECEIPT_PATH = REPO_ROOT / "docs" / "receipts" / "probe-samples" / "DEV-100.json"
PARENT_D1_PATH = REPO_ROOT / "docs" / "receipts" / "artifacts" / "d1-identity.json"
RUNTIME_VIEW_PATH = REPO_ROOT / "configs" / "dataset" / "slurp-speech-native-dev500.json"
WORKERS = 8  # standing rule: <= 8 CPU workers while a GPU campaign may fly


def canonical_sha256(document: object) -> str:
    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, document: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    verified = load_verified_probe_split(REPO_ROOT, SPLIT_NAME)
    # load_verified_probe_split already recomputed the receipt-integrity
    # (colon-keyed) hash fail-closed; what it RETURNS is the slash-prefixed
    # run identity every ExecutionPlan carries. Both must match the receipt.
    if verified.identity_hash != receipt["run_identity_hash"]:
        raise SystemExit("DEV-500 receipt run identity disagrees with the split loader")
    if verified.split_role != SPLIT_ROLE:
        raise SystemExit("DEV-500 verified split role is not 'dev'")
    if receipt["split_role"] != SPLIT_ROLE or receipt["carrier"] != CARRIER:
        raise SystemExit("DEV-500 receipt is not the dev-role SLURP split")
    sample_ids = [item["id"] for item in receipt["items"]]
    if len(set(sample_ids)) != len(sample_ids) or len(sample_ids) != receipt["n_items"]:
        raise SystemExit("DEV-500 receipt item ids are malformed")
    if any(not sample_id.startswith("slurp:devel:") for sample_id in sample_ids):
        raise SystemExit("DEV-500 must carry only SLURP devel sample ids")

    # The receipt's own nesting claim, verified rather than trusted: the
    # committed DEV-100 receipt's items must be an EXACT subset, so the 100
    # already-materialized packet identities are guaranteed to be members of
    # this view with unchanged ids.
    nested = json.loads(NESTED_RECEIPT_PATH.read_text(encoding="utf-8"))
    nested_ids = {item["id"] for item in nested["items"]}
    if not nested_ids.issubset(set(sample_ids)) or len(nested_ids) != 100:
        raise SystemExit("DEV-100 is not an exact 100-item subset of DEV-500")
    nesting = receipt.get("nesting")
    if (
        not isinstance(nesting, dict)
        or nesting.get("is_exact_subset_of_parent") is not True
    ):
        raise SystemExit("DEV-500 receipt nesting block is malformed")

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    # media_relpath only -- no scenario/action/entity/transcript field is copied.
    relpath_by_id = {
        record.sample_id: record.media_relpath
        for record in load_slurp_split(lock, root, "devel")
    }
    missing = [sample_id for sample_id in sample_ids if sample_id not in relpath_by_id]
    if missing:
        raise SystemExit(f"DEV-500 samples absent from the devel loader: {missing[:5]}")

    ordered = sorted(sample_ids)
    confined = [
        (
            sample_id,
            *_confined_media_path(
                root,
                relpath_by_id[sample_id],
                context=f"DEV-500 sample {sample_id!r}",
            ),
        )
        for sample_id in ordered
    ]
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=min(WORKERS, len(confined))) as pool:
        measured = tuple(pool.map(_probe_speech_media, (entry[2] for entry in confined)))

    manifest: list[dict[str, object]] = []
    for (sample_id, media_relpath, _path), facts in zip(confined, measured, strict=True):
        media_bytes, media_sha256, audio_seconds, sample_rate_hz = facts
        manifest.append(
            {
                "id": sample_id,
                "media_relpath": media_relpath,
                "bytes": media_bytes,
                "sha256": media_sha256,
                "audio_seconds": round(float(audio_seconds), 9),
                "sample_rate_hz": sample_rate_hz,
            }
        )

    # Prove the "no supplement needed" claim against the immutable D1
    # artifact rather than asserting it: every item must already be recorded
    # there, with the SAME bytes this generator just re-measured.
    d1 = json.loads(PARENT_D1_PATH.read_text(encoding="utf-8"))
    d1_media = {
        entry["id"]: entry
        for entry in d1["carriers"][CARRIER]["layers"]["media"]["manifest"]
    }
    for entry in manifest:
        base = d1_media.get(entry["id"])
        if base is None:
            raise SystemExit(
                f"DEV-500 sample {entry['id']!r} is OUTSIDE the D1 closure; this "
                "generator only emits supplement-free views"
            )
        if base["sha256"] != entry["sha256"] or base["bytes"] != entry["bytes"]:
            raise SystemExit(
                f"DEV-500 sample {entry['id']!r} media bytes drifted from D1's record"
            )

    items = [
        {
            "sample_id": entry["id"],
            "media_relpath": entry["media_relpath"],
            "audio_sha256": entry["sha256"],
            "audio_seconds": entry["audio_seconds"],
            "sample_rate_hz": entry["sample_rate_hz"],
            "packet_id": entry["id"].replace(":", "/"),
        }
        for entry in manifest
    ]
    unsigned: dict[str, object] = {
        "schema": "saea-speech-native-runtime-view-v1",
        "study": "speech-aware-evidence-acquisition",
        "status": "MODEL-FREE, LABEL-FREE ENGINEERING INPUT; NOT AN EXPOSURE REGISTRATION",
        "carrier_lock_key": CARRIER,
        "split_name": SPLIT_NAME,
        "split_role": SPLIT_ROLE,
        "seed": receipt["seed"],
        # the load_split / ExecutionPlan convention, not the receipt-integrity one
        "split_identity_hash": verified.identity_hash,
        "source_binding_sha256": canonical_sha256(receipt),
        # null: DEV-500's media is already inside the immutable D1 closure
        # (verified above), so there is nothing to supplement.
        "d1_media_supplement": None,
        "d1_media_supplement_sha256": None,
        "d1_manifest_sha256": None,
        "count": len(items),
        "audio_seconds_total": round(
            sum(float(item["audio_seconds"]) for item in items), 9
        ),
        "items": items,
    }
    runtime_view = {**unsigned, "runtime_view_sha256": canonical_sha256(unsigned)}
    runtime_view_file_sha256 = write_json(RUNTIME_VIEW_PATH, runtime_view)

    dev100_view = json.loads(
        (REPO_ROOT / "configs" / "dataset" / "slurp-speech-native-dev100.json").read_text(
            encoding="utf-8"
        )
    )
    dev100_items_here = {
        item["sample_id"]: item for item in items if item["sample_id"] in nested_ids
    }
    for item in dev100_view["items"]:
        if dev100_items_here.get(item["sample_id"]) != item:
            raise SystemExit(
                f"DEV-100 member {item['sample_id']!r} does not carry byte-identical "
                "item facts in the DEV-500 view; packet identity would not carry over"
            )

    print(
        json.dumps(
            {
                "split_identity_hash_load_split": runtime_view["split_identity_hash"],
                "split_identity_hash_receipt_integrity": receipt["split_identity_hash"],
                "runtime_view_sha256": runtime_view["runtime_view_sha256"],
                "runtime_view_file_sha256": runtime_view_file_sha256,
                "d1_media_supplement": runtime_view["d1_media_supplement"],
                "d1_covered_items": len(manifest),
                "dev100_members_byte_identical": len(dev100_view["items"]),
                "count": runtime_view["count"],
                "audio_seconds_total": runtime_view["audio_seconds_total"],
                "total_bytes": sum(int(entry["bytes"]) for entry in manifest),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
