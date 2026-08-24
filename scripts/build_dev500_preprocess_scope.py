"""Audit DEV-500 packet coverage and freeze the preprocessing scope.

DEV-500 confirmatory prep prerequisite #1, second half (preregistration
``docs/readiness/2026-08-24-dev500-confirmatory-preregistration.md``
section 4.1): before the ~400 new devel packets can be materialized, the
exact set that NEEDS materialization must be measured — never assumed —
and frozen as its own committed identity so the CPU-sidecar preprocessing
run contacts EXACTLY the missing recordings and not the 100 DEV-100
members whose packets already live in the resident feature root.

Why a derived probe receipt: ``core.driver.run_experiment`` enumerates a
run's samples from the dataset fragment's ``split_name`` through
``load_verified_probe_split`` and refuses any subset mechanism (by
design — a plan binds a whole frozen identity set). Scoping the sidecar to
the missing recordings therefore requires a committed probe-sample receipt
naming exactly those items. The receipt written here is NOT a new sampling
decision: it is the deterministic set difference DEV-500 minus DEV-100
(two frozen, committed receipts), which the preregistration section 1
already names as the confirmatory statistic's unexposed-400 population,
and this generator verifies it EQUALS the measured missing-from-feature-
root set before writing anything.

Model-free audit (mirrors the DEV-100 preprocess row's audit): for every
DEV-500 item, presence is measured in the six legacy feature caches (by
the llama.cpp featcache FNV-1a key over the original media bytes) and the
three packet roots (by promoted packet directory), and every already-
present packet in the resident root is re-verified to carry this item's
exact ``audio_sha256``.

Outputs:

* ``docs/receipts/probe-samples/DEV-500-NEW400.json`` — the derived
  preprocessing-scope receipt (both hash conventions, parents pinned).
* ``configs/dataset/slurp-speech-native-dev500-new400.json`` — the
  label-free runtime view over exactly those items (schema
  ``saea-speech-native-runtime-view-v1``, null D1 supplement — every item
  is inside the same base-D1 devel closure the DEV-500 view proved).
* An audit JSON on stdout for the exposure-ledger registration.

Run in WSL2 (data root on /mnt/e; feature caches on ext4):

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \
      python scripts/build_dev500_preprocess_scope.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    legacy_audio_feature_cache_key,
    load_speech_feature_packet,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash as slash_hash,
)
from speech_aware_evidence_acquisition.reproduction.sampling import (  # noqa: E402
    split_identity_hash as key_hash,
)

SPLIT_NAME = "DEV-500-NEW400"
CARRIER = "slurp"
PARENT_RECEIPT = REPO_ROOT / "docs" / "receipts" / "probe-samples" / "DEV-500.json"
NESTED_RECEIPT = REPO_ROOT / "docs" / "receipts" / "probe-samples" / "DEV-100.json"
DEV500_VIEW = REPO_ROOT / "configs" / "dataset" / "slurp-speech-native-dev500.json"
RECEIPT_OUT = REPO_ROOT / "docs" / "receipts" / "probe-samples" / f"{SPLIT_NAME}.json"
VIEW_OUT = REPO_ROOT / "configs" / "dataset" / "slurp-speech-native-dev500-new400.json"

FEAT_CACHE_ROOT = Path("/home/chao/feat-cache")
LEGACY_CACHES = (
    "ami-q4km",
    "audio2tool-q4km",
    "q4km",
    "slurp-lco3b",
    "slurp-lco7b",
    "slurp-q4km",
)
PACKET_ROOTS = (
    "slurp-q4km-packets",
    "slurp-q4km-packets-04ccc72a",
    "slurp-q4km-packets-x108-04ccc72a",
)
RESIDENT_PACKET_ROOT = "slurp-q4km-packets-04ccc72a"


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
    view = json.loads(DEV500_VIEW.read_text(encoding="utf-8"))
    unsigned = {k: v for k, v in view.items() if k != "runtime_view_sha256"}
    if view["runtime_view_sha256"] != canonical_sha256(unsigned):
        raise SystemExit("committed DEV-500 runtime view fails its own hash")
    if view["split_name"] != "DEV-500" or view["count"] != 500:
        raise SystemExit("committed DEV-500 runtime view identity mismatch")

    parent = json.loads(PARENT_RECEIPT.read_text(encoding="utf-8"))
    nested = json.loads(NESTED_RECEIPT.read_text(encoding="utf-8"))
    parent_ids = {item["id"] for item in parent["items"]}
    nested_ids = {item["id"] for item in nested["items"]}
    if len(parent_ids) != 500 or len(nested_ids) != 100 or not nested_ids <= parent_ids:
        raise SystemExit("DEV-500/DEV-100 receipt nesting is not the expected 100-in-500")
    expected_difference = parent_ids - nested_ids

    root = data_root()
    audit_counts = {name: 0 for name in (*LEGACY_CACHES, *PACKET_ROOTS)}
    missing_items: list[dict[str, object]] = []
    present_items: list[str] = []
    for item in view["items"]:
        sample_id = item["sample_id"]
        packet_id = item["packet_id"]
        media_path = Path(root) / item["media_relpath"]
        audio_bytes = media_path.read_bytes()
        audio_sha256 = hashlib.sha256(audio_bytes).hexdigest()
        if audio_sha256 != item["audio_sha256"]:
            raise SystemExit(f"media hash drift for {sample_id!r} vs the committed view")
        fnv_key = legacy_audio_feature_cache_key(audio_bytes)
        for cache in LEGACY_CACHES:
            if (FEAT_CACHE_ROOT / cache / f"{fnv_key}_o0.feat").is_file():
                audit_counts[cache] += 1
        in_resident_root = False
        for packet_root in PACKET_ROOTS:
            packet_dir = FEAT_CACHE_ROOT / packet_root / packet_id
            if packet_dir.is_dir():
                audit_counts[packet_root] += 1
                if packet_root == RESIDENT_PACKET_ROOT:
                    packet = load_speech_feature_packet(
                        FEAT_CACHE_ROOT / packet_root, packet_id
                    )
                    if packet.audio_sha256 != audio_sha256:
                        raise SystemExit(
                            f"resident packet {packet_id!r} carries a DIFFERENT "
                            "audio_sha256 than this DEV-500 item"
                        )
                    in_resident_root = True
        if in_resident_root:
            present_items.append(sample_id)
        else:
            missing_items.append(item)

    present_set = set(present_items)
    missing_set = {item["sample_id"] for item in missing_items}
    if present_set != nested_ids or missing_set != expected_difference:
        raise SystemExit(
            "measured feature-root coverage does not equal the DEV-100 nesting: "
            f"present={len(present_set)} (DEV-100 members present: "
            f"{len(present_set & nested_ids)}), missing={len(missing_set)}; "
            "the derived set-difference receipt would misstate the preprocessing "
            "scope, refusing to write it"
        )

    ordered_missing_ids = sorted(missing_set)
    keys = [f"{CARRIER}:{sample_id}" for sample_id in ordered_missing_ids]
    receipt_integrity = key_hash(keys)
    run_identity = slash_hash(tuple(prefixed(CARRIER, tuple(ordered_missing_ids))))
    missing_audio_seconds = round(
        sum(float(item["audio_seconds"]) for item in missing_items), 9
    )

    receipt = {
        "schema": "saea-dev-ladder-derived-v1",
        "probe": "dev-ladder-dev500-preprocess-new400",
        "generated_date": "2026-08-24",
        "generator": "scripts/build_dev500_preprocess_scope.py",
        "authority": (
            "docs/readiness/2026-08-24-dev500-confirmatory-preregistration.md "
            "section 4.1 (prep prerequisite: ~400 new devel packets via the CPU "
            "preprocessing sidecar); owner ladder rulings "
            "docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md section 2.2"
        ),
        "carrier": CARRIER,
        "split": "devel",
        "split_role": "dev",
        "n_items": len(ordered_missing_ids),
        "selection_rule": (
            "DERIVED, not sampled: the deterministic set difference DEV-500 minus "
            "DEV-100 over the two committed probe-sample receipts (DEV-100 is an "
            "exact seeded subset of DEV-500 by construction). This equals the "
            "preregistration section-1 unexposed-400 statistic population, and this "
            "generator verified it equals the measured missing-from-feature-root "
            "set (packet-directory + audio_sha256 audit of "
            "/home/chao/feat-cache/slurp-q4km-packets-04ccc72a) before writing. "
            "No recording choice is made here; every item id was frozen by "
            "scripts/build_dev_ladder.py in the parent receipts."
        ),
        "parents": {
            "dev500_receipt": "docs/receipts/probe-samples/DEV-500.json",
            "dev500_split_identity_hash": parent["split_identity_hash"],
            "dev500_run_identity_hash": parent["run_identity_hash"],
            "dev100_receipt": "docs/receipts/probe-samples/DEV-100.json",
            "dev100_split_identity_hash": nested["split_identity_hash"],
            "dev100_run_identity_hash": nested["run_identity_hash"],
        },
        "exclusions": parent.get("exclusions"),
        "seed": parent["seed"],
        "split_identity_hash": receipt_integrity,
        "split_identity_hash_basis": (
            "sha256 over the LF-joined, sorted, carrier-prefixed item 'key' strings "
            "(reproduction.sampling.split_identity_hash -- the receipt-integrity "
            "convention load_verified_probe_split recomputes fail-closed)"
        ),
        "run_identity_hash": run_identity,
        "run_identity_hash_basis": (
            "sha256 over the LF-joined, sorted carrier-prefixed sample ids "
            "(f'{carrier}/{id}') -- data.splits.split_identity_hash, the value "
            "load_split/ExecutionPlan/protocol_hash carry"
        ),
        "items": [
            {"id": sample_id, "key": f"{CARRIER}:{sample_id}"}
            for sample_id in ordered_missing_ids
        ],
    }
    receipt_file_sha256 = write_json(RECEIPT_OUT, receipt)

    items = sorted(missing_items, key=lambda item: item["sample_id"])
    view_unsigned: dict[str, object] = {
        "schema": "saea-speech-native-runtime-view-v1",
        "study": "speech-aware-evidence-acquisition",
        "status": "MODEL-FREE, LABEL-FREE ENGINEERING INPUT; NOT AN EXPOSURE REGISTRATION",
        "carrier_lock_key": CARRIER,
        "split_name": SPLIT_NAME,
        "split_role": "dev",
        "seed": parent["seed"],
        "split_identity_hash": run_identity,
        "source_binding_sha256": canonical_sha256(receipt),
        "d1_media_supplement": None,
        "d1_media_supplement_sha256": None,
        "d1_manifest_sha256": None,
        "count": len(items),
        "audio_seconds_total": missing_audio_seconds,
        "items": items,
    }
    runtime_view = {**view_unsigned, "runtime_view_sha256": canonical_sha256(view_unsigned)}
    view_file_sha256 = write_json(VIEW_OUT, runtime_view)

    print(
        json.dumps(
            {
                "audit_counts": audit_counts,
                "present_in_resident_root": len(present_items),
                "present_equals_dev100_members": sorted(present_set) == sorted(nested_ids),
                "missing_count": len(items),
                "missing_audio_seconds_total": missing_audio_seconds,
                "receipt": str(RECEIPT_OUT.relative_to(REPO_ROOT)),
                "receipt_file_sha256": receipt_file_sha256,
                "receipt_integrity_hash": receipt_integrity,
                "run_identity_hash": run_identity,
                "runtime_view": str(VIEW_OUT.relative_to(REPO_ROOT)),
                "runtime_view_sha256": runtime_view["runtime_view_sha256"],
                "runtime_view_file_sha256": view_file_sha256,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
