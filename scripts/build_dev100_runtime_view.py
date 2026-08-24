"""Build the DEV-100 label-free runtime view from its probe-sample receipt.

Why a separate generator (and not ``e0.d1_identity.build_speech_native_
runtime_view``): the existing speech-native builders derive their item list
from the frozen SLURP **train** binding and hard-refuse any sample id whose
``split`` component is not ``train`` (``_build_speech_native_runtime_view``)
or whose id does not start with ``slurp:train:``
(``build_d1_media_supplement``). The DEV ladder is a different governance
object -- its identity comes from the committed probe-sample receipt
``docs/receipts/probe-samples/DEV-100.json`` (owner ruling
``2026-08-23-knowledge-plane-baseline-rulings.md`` section 2.2), not from a
binding -- so this module reproduces the SAME two output schemas over that
receipt instead of widening the train-only builders.

What is (and is not) read here
------------------------------
Only ``media_relpath`` is consumed from the SLURP devel loader; scenario,
action, intent, entity, and transcript fields are never copied into either
output. Both artifacts are therefore label-free engineering inputs and carry
no exposure. The canonical recording per utterance is NOT re-chosen here:
the DEV-100 receipt already froze exactly one recording per selected
utterance via ``random.Random(f"{seed}:{scenario}:{utterance_id}")`` over the
utterance's id-sorted recordings (``scripts/build_dev_ladder.py``), and this
generator consumes those exact sample ids verbatim.

Identity discipline (the E108 lesson)
-------------------------------------
The 2026-08-22 EVIDENCE-E108 preprocessing plan was refused because the
dataset fragment's embedded ``split_identity_hash`` was NOT the identity the
authoritative split loader returns -- so the plan's protocol hash was built
over the wrong value. The DEV-100 receipt carries BOTH conventions and names
them explicitly:

* ``split_identity_hash`` -- SHA-256 over the sorted, LF-joined, COLON-keyed
  item strings (``f"{carrier}:{id}"``); the receipt-integrity value
  ``load_verified_probe_split`` recomputes fail-closed.
* ``run_identity_hash`` -- SHA-256 over the sorted, LF-joined, SLASH-prefixed
  ids (``f"{carrier}/{id}"``); this is what
  ``reproduction.probe_split.VerifiedSplit.identity_hash`` and therefore
  ``core.driver.run.load_split`` return, and what every ``ExecutionPlan``
  and ``protocol_hash`` must carry.

This runtime view embeds the SECOND value in its ``split_identity_hash``
field, so the fragment and the plan agree by construction. The generator
verifies both conventions against the receipt and refuses on disagreement;
the receipt-integrity value is recorded in the flight-readiness receipt.

``source_binding_sha256`` has no speech-native binding to point at for a
DEV-ladder view, so it carries the canonical-JSON SHA-256 of the DEV-100
probe-sample receipt document -- the artifact that actually binds this
view's identity. The field name is fixed by the frozen
``saea-speech-native-runtime-view-v1`` key set (exact-keys check), so the
substitution is recorded here and in the flight-readiness receipt rather
than in an extra key.

No D1 media supplement (measured, not assumed)
----------------------------------------------
A supplement is an ADDITIVE successor for a carrier slice OUTSIDE the
immutable E0 D1 closure, and ``contracts.gate_media_identity`` refuses any
supplement entry that duplicates a base D1 sample. The first DEV-100
preprocessing attempt was refused by exactly that check, with zero model
contacts: base D1's ``slurp`` media layer already records all 8,690 devel
recordings, so all 100 DEV-100 items are inside the closure and there is
nothing to supplement. This generator therefore verifies that coverage and
writes ``d1_media_supplement`` / ``d1_media_supplement_sha256`` /
``d1_manifest_sha256`` as null -- the gate reads DEV-100 media identity
straight from D1 and re-hashes every file at model-touch time exactly as it
would through a supplement. It refuses if any item is NOT covered, rather
than silently emitting a supplement the gate would reject.

Run in WSL2 (data root on /mnt/e):

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \
      python scripts/build_dev100_runtime_view.py
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

SPLIT_NAME = "DEV-100"
SPLIT_ROLE = "dev"
CARRIER = "slurp"
RECEIPT_PATH = REPO_ROOT / "docs" / "receipts" / "probe-samples" / f"{SPLIT_NAME}.json"
PARENT_D1_PATH = REPO_ROOT / "docs" / "receipts" / "artifacts" / "d1-identity.json"
RUNTIME_VIEW_PATH = REPO_ROOT / "configs" / "dataset" / "slurp-speech-native-dev100.json"
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
        raise SystemExit("DEV-100 receipt run identity disagrees with the split loader")
    if verified.split_role != SPLIT_ROLE:
        raise SystemExit("DEV-100 verified split role is not 'dev'")
    if receipt["split_role"] != SPLIT_ROLE or receipt["carrier"] != CARRIER:
        raise SystemExit("DEV-100 receipt is not the dev-role SLURP split")
    sample_ids = [item["id"] for item in receipt["items"]]
    if len(set(sample_ids)) != len(sample_ids) or len(sample_ids) != receipt["n_items"]:
        raise SystemExit("DEV-100 receipt item ids are malformed")
    if any(not sample_id.startswith("slurp:devel:") for sample_id in sample_ids):
        raise SystemExit("DEV-100 must carry only SLURP devel sample ids")

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    # media_relpath only -- no scenario/action/entity/transcript field is copied.
    relpath_by_id = {
        record.sample_id: record.media_relpath
        for record in load_slurp_split(lock, root, "devel")
    }
    missing = [sample_id for sample_id in sample_ids if sample_id not in relpath_by_id]
    if missing:
        raise SystemExit(f"DEV-100 samples absent from the devel loader: {missing[:5]}")

    ordered = sorted(sample_ids)
    confined = [
        (
            sample_id,
            *_confined_media_path(
                root,
                relpath_by_id[sample_id],
                context=f"DEV-100 sample {sample_id!r}",
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
                f"DEV-100 sample {entry['id']!r} is OUTSIDE the D1 closure; this "
                "generator only emits supplement-free views"
            )
        if base["sha256"] != entry["sha256"] or base["bytes"] != entry["bytes"]:
            raise SystemExit(
                f"DEV-100 sample {entry['id']!r} media bytes drifted from D1's record"
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
        # null: DEV-100's media is already inside the immutable D1 closure
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

    print(
        json.dumps(
            {
                "split_identity_hash_load_split": runtime_view["split_identity_hash"],
                "split_identity_hash_receipt_integrity": receipt["split_identity_hash"],
                "runtime_view_sha256": runtime_view["runtime_view_sha256"],
                "runtime_view_file_sha256": runtime_view_file_sha256,
                "d1_media_supplement": runtime_view["d1_media_supplement"],
                "d1_covered_items": len(manifest),
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
