"""Draw and freeze the Audio2Tool stage-G1 evaluation subset, and audit its
speech-feature packet coverage.

Stage G1 of the Audio2Tool generality campaign
(``docs/readiness/2026-08-25-a2t-generality-campaign-plan.md`` section 3.6,
amended by sections 7 and 8) flies on a tier-stratified subset of the
carrier's frozen EXPOSED 400-item discovery split
(``docs/receipts/probe-samples/r1-audio2tool-sample.json``). Per plan section
3.3 the exposed tier's numbers are SECONDARY readings and never the campaign
claim; G1's purpose is mechanics and first signal.

Two model-free deliverables, both produced by this generator:

* ``docs/receipts/a2t/A2T-G1-104.json`` -- the frozen subset receipt (both
  hash conventions, parent receipt pinned, per-item media identity and packet
  id). It is deliberately NOT written under ``docs/receipts/probe-samples/``:
  ``data.audio2tool.audio2tool_receipts`` globs that directory and any file
  placed there would silently EXPAND the carrier's frozen loadable universe
  (the G0 report's own rule, section 2).
* A packet-coverage AUDIT on stdout: for every drawn item, presence in the
  legacy llama.cpp feature caches (by the featcache FNV-1a key over the
  ORIGINAL media bytes) and in the A2T packet root, so the preprocessing
  scope is MEASURED before any sidecar is registered, never assumed.

The draw: 13 items per tier over the 8 tiers = 104, seed 20260807 (the
carrier's own frozen seed). Tiers are processed in ascending tier name and
each tier's candidates are sorted by ``sample_id`` before sampling, so the
draw is deterministic and pool-order independent. 13 per tier is chosen so
every tier carries an EQUAL count -- there is no remainder rule to defend and
no tier can be over- or under-represented by an allocation choice.

Run in WSL2 (data root on /mnt/e; feature caches on ext4)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \
      python scripts/build_a2t_g1_subset.py
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    legacy_audio_feature_cache_key,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash as slash_hash,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (  # noqa: E402
    Audio2ToolAdapter,
)
from speech_aware_evidence_acquisition.reproduction.sampling import (  # noqa: E402
    split_identity_hash as key_hash,
)

SPLIT_NAME = "A2T-G1-104"
PER_TIER = 13
SEED = 20260807
PARENT_RECEIPT = (
    REPO_ROOT / "docs" / "receipts" / "probe-samples" / "r1-audio2tool-sample.json"
)
PARENT_SPLIT_IDENTITY = (
    "e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c"
)
RECEIPT_OUT = REPO_ROOT / "docs" / "receipts" / "a2t" / (SPLIT_NAME + ".json")

FEAT_CACHE_ROOT = Path("/home/chao/feat-cache")
LEGACY_CACHES = (
    "audio2tool-q4km",
    "q4km",
    "ami-q4km",
    "slurp-q4km",
    "slurp-lco3b",
    "slurp-lco7b",
)
PACKET_ROOT = FEAT_CACHE_ROOT / "a2t-q4km-packets-04ccc72a"


def write_json(path: Path, document: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    lock = load_lock(umbrella_lock_path())
    root = data_root()

    parent = json.loads(PARENT_RECEIPT.read_text(encoding="utf-8"))
    if parent["carrier"] != AUDIO2TOOL_LOCK_KEY or parent["split_role"] != "discovery":
        raise SystemExit("parent receipt identity drifted")
    if parent["split_identity_hash"] != PARENT_SPLIT_IDENTITY:
        raise SystemExit("parent receipt split identity drifted")
    parent_keys = [str(item["key"]) for item in parent["items"]]
    if key_hash(parent_keys) != PARENT_SPLIT_IDENTITY:
        raise SystemExit("parent receipt fails its own key-convention identity hash")
    # ID-FORMAT NOTE (the A4 lesson, applied): receipt items carry a ``key`` of
    # the form ``audio2tool:tier:NNNNNN`` while the adapter's ``sample_id`` is
    # ``tier:NNNNNN``. Every set comparison below normalizes to ``sample_id``
    # first; comparing on ``key`` yields a SILENTLY EMPTY intersection.
    parent_sample_ids = {
        "%s:%06d" % (item["tier"], int(item["id"])) for item in parent["items"]
    }
    if len(parent_sample_ids) != 400:
        raise SystemExit(
            "parent receipt normalizes to %d ids" % len(parent_sample_ids)
        )

    adapter = Audio2ToolAdapter(lock, root, repo_root=REPO_ROOT)
    samples = list(adapter.load_split("discovery"))
    loaded_ids = {sample.sample_id for sample in samples}
    if loaded_ids != parent_sample_ids:
        raise SystemExit(
            "the loader's discovery split does not equal the parent receipt's "
            "normalized ids (%d vs %d)" % (len(loaded_ids), len(parent_sample_ids))
        )
    by_id = {sample.sample_id: sample for sample in samples}

    tiers = sorted({sample_id.split(":", 1)[0] for sample_id in loaded_ids})
    if len(tiers) != 8:
        raise SystemExit("expected 8 tiers, got %r" % (tiers,))

    rng = random.Random(SEED)
    drawn: list[str] = []
    for tier in tiers:
        candidates = sorted(
            sid for sid in loaded_ids if sid.split(":", 1)[0] == tier
        )
        if len(candidates) != 50:
            raise SystemExit(
                "tier %s carries %d exposed items" % (tier, len(candidates))
            )
        drawn.extend(rng.sample(candidates, PER_TIER))
    drawn = sorted(drawn)
    if len(drawn) != PER_TIER * len(tiers) or len(set(drawn)) != len(drawn):
        raise SystemExit("the draw is not a %d-item set" % (PER_TIER * len(tiers)))
    strata = Counter(sid.split(":", 1)[0] for sid in drawn)
    if set(strata.values()) != {PER_TIER}:
        raise SystemExit("tier balance broken: %r" % (dict(strata),))
    if not set(drawn) <= parent_sample_ids:
        raise SystemExit("the draw escapes the frozen exposed 400")

    items = []
    audio_total = 0.0
    for sample_id in drawn:
        sample = by_id[sample_id]
        tier, raw_id = sample_id.split(":", 1)
        media_path = root / sample.media_relpath
        audio_bytes = media_path.read_bytes()
        items.append(
            {
                "sample_id": sample_id,
                "key": "%s:%s" % (AUDIO2TOOL_LOCK_KEY, sample_id),
                "tier": tier,
                "id": int(raw_id),
                "media_relpath": sample.media_relpath,
                "audio_sha256": sample.audio_ref.sha256,
                "audio_seconds": float(sample.audio_seconds),
                "packet_id": sample_id.replace(":", "/"),
                "legacy_cache_key": legacy_audio_feature_cache_key(audio_bytes),
            }
        )
        audio_total += float(sample.audio_seconds)

    receipt = {
        "schema": "saea-a2t-subset-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "carrier": AUDIO2TOOL_LOCK_KEY,
        "split_name": SPLIT_NAME,
        "split_role": "discovery",
        "exposure": (
            "EXPOSED. Every item is a member of the frozen 400-item discovery "
            "split already read by the A0 baseline, P-EMB-2 and the S2/S2b/S2c "
            "probes. Campaign plan section 3.3: this tier's numbers are "
            "SECONDARY readings and are never the campaign claim."
        ),
        "purpose": (
            "Audio2Tool generality campaign stage G1 -- mechanics and first "
            "signal under the section 8.1 derived serving geometry."
        ),
        "parent_receipt": "docs/receipts/probe-samples/r1-audio2tool-sample.json",
        "parent_split_identity_hash": PARENT_SPLIT_IDENTITY,
        "seed": SEED,
        "design": (
            "%d items per tier over 8 tiers = %d; tiers processed in ascending "
            "tier name, each tier's candidates sorted by sample_id before "
            "sampling, so the draw is deterministic and pool-order independent. "
            "Equal per-tier counts, so there is no remainder allocation rule."
        )
        % (PER_TIER, PER_TIER * len(tiers)),
        "count": len(items),
        "audio_seconds_total": round(audio_total, 6),
        "strata_counts": dict(sorted(strata.items())),
        "split_identity_hash": key_hash([item["key"] for item in items]),
        "run_identity_hash": slash_hash(
            prefixed(AUDIO2TOOL_LOCK_KEY, [item["sample_id"] for item in items])
        ),
        "id_field_convention": (
            "sample_id (tier:NNNNNN) is what the loader and every flight uses; "
            "key (audio2tool:tier:NNNNNN) is the split_identity_hash basis only; "
            "run_identity_hash is the load-split convention over "
            "audio2tool/tier:NNNNNN. Set comparisons against a flown population "
            "MUST use sample_id."
        ),
        "items": items,
    }
    receipt_sha = write_json(RECEIPT_OUT, receipt)

    # ---- packet-coverage audit (model-free; measured, never assumed) ------
    cache_hits: dict[str, list[str]] = {}
    packet_present: list[str] = []
    for item in items:
        key = item["legacy_cache_key"]
        found = []
        for cache in LEGACY_CACHES:
            if (FEAT_CACHE_ROOT / cache / (key + "_o0.feat")).exists():
                found.append(cache)
        cache_hits[item["sample_id"]] = found
        if (PACKET_ROOT / item["packet_id"] / "packet.json").exists():
            packet_present.append(item["sample_id"])

    warm = sorted(sid for sid, found in cache_hits.items() if found)
    cold = sorted(sid for sid, found in cache_hits.items() if not found)
    cold_set = set(cold)
    audit = {
        "receipt": str(RECEIPT_OUT.relative_to(REPO_ROOT)).replace("\\", "/"),
        "receipt_sha256": receipt_sha,
        "split_name": SPLIT_NAME,
        "count": len(items),
        "audio_seconds_total": round(audio_total, 6),
        "split_identity_hash": receipt["split_identity_hash"],
        "run_identity_hash": receipt["run_identity_hash"],
        "strata_counts": receipt["strata_counts"],
        "legacy_cache_roots_probed": list(LEGACY_CACHES),
        "legacy_cache_warm": len(warm),
        "legacy_cache_cold": len(cold),
        "legacy_cache_cold_ids": cold,
        "legacy_cache_by_root": dict(
            sorted(
                Counter(
                    name for found in cache_hits.values() for name in found
                ).items()
            )
        ),
        "packet_root": str(PACKET_ROOT),
        "packets_already_present": len(packet_present),
        "packets_missing": len(items) - len(packet_present),
        "cold_audio_seconds": round(
            sum(
                item["audio_seconds"]
                for item in items
                if item["sample_id"] in cold_set
            ),
            6,
        ),
    }
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
