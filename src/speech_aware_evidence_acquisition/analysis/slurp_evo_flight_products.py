"""The model-free flight products of one EVO-S1 fold roster.

Exposure row ``SAEA-SN-MF-SLURP-EVO-FOLD-SUPPLEMENTS-V2``. A frozen roster
receipt is an IDENTITY statement; a fold cannot be flown from it alone. Three
artifacts turn one into a hydratable population, and this module builds all
three from the same single measurement pass, so they cannot disagree:

* the **D1 media supplement** (``saea-d1-media-supplement-v1``, the shape
  ``contracts.gate_media_identity`` reads). The immutable D1 identity artifact
  closes over the SLURP **devel** split only -- 8,690 recordings, zero
  ``slurp:train:`` ids -- so every TRAIN row a flight sends needs an additive
  media receipt or the gate refuses the model touch. This is the TRAIN90
  precedent, the only TRAIN roster this study has ever flown;
* the **speech-native runtime view** (``saea-speech-native-runtime-view-v1``),
  the dataset fragment a composed config names, carrying per item
  ``media_relpath``, ``audio_sha256``, ``audio_seconds``, ``sample_rate_hz``
  and ``packet_id``;
* the **probe-sample view** under ``docs/receipts/probe-samples/``, because
  ``core.driver.run_experiment`` enumerates a run's samples through
  ``reproduction.probe_split.load_verified_probe_split`` and a dataset
  fragment's ``split_name`` must resolve to a committed receipt there.

Contact surface, stated once: each flac is re-hashed byte for byte and only
its container HEADER is read for duration and sample rate. No sentence text,
transcript, scenario, action, intent, entity, gold, score or future turn is
opened -- the SLURP loader is consulted for ``media_relpath`` and nothing
else. No model, network, tokenizer, scorer or GPU contact.

Two identity conventions meet here and are kept distinct on purpose. The
roster receipt's ``split_identity_hash`` is the SLASH-prefixed run identity
(``data.splits.split_identity_hash`` over ``slurp/<sample_id>``) that an
``ExecutionPlan`` and ``core.bundle.verify_bundle`` carry, and the runtime
view republishes exactly that value. The probe-sample receipt's own
``split_identity_hash`` is the COLON-keyed receipt-integrity value
``load_verified_probe_split`` recomputes fail-closed; it is a different
serialization of the same frozen id set, and either one pins the other.

**Packets are not built here.** Promoting a fold's featcache packets runs a
llama.cpp sidecar with the decoder and the mmproj loaded and issues one
one-token contact per row (``SAEA-SN-DEV1000-PREPROCESS``,
``bounded-discovery-probe``). That is a model contact and belongs to the
flight agent; :func:`packet_coverage` measures, model-free, exactly how many
of a fold's rows already have one, so the flight agent's scope is proven
rather than assumed.
"""

from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..e0.d1_identity import _confined_media_path, _probe_speech_media

STUDY = "speech-aware-evidence-acquisition"
CARRIER = "slurp"
D1_SUPPLEMENT_SCHEMA = "saea-d1-media-supplement-v1"
RUNTIME_VIEW_SCHEMA = "saea-speech-native-runtime-view-v1"
VIEW_STATUS = "MODEL-FREE, LABEL-FREE ENGINEERING INPUT; NOT AN EXPOSURE REGISTRATION"

#: Owner rule (2026-09-03 pipeline directive): CPU preprocessing runs at 20
#: workers idle and AT MOST 8 while a GPU campaign flies. This module can run
#: beside a flight, so 8 is its ceiling, not its optimum.
MAX_WORKERS = 8

#: The feature caches and packet roots a SLURP row can already live in. Read
#: only to COUNT coverage; nothing here is written.
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


class FlightProductError(ValueError):
    """A fold cannot be turned into flight products -- fail closed."""


def canonical_sha256(document: object) -> str:
    """SHA-256 over the canonical JSON serialization used by every receipt."""

    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def measure_media(
    roster: Mapping[str, object],
    *,
    relpath_by_id: Mapping[str, str],
    data_root: Path,
    workers: int = MAX_WORKERS,
    probe: Callable[[Path], tuple[int, str, float, int]] = _probe_speech_media,
) -> list[dict[str, object]]:
    """Re-measure every roster recording into a D1-shaped manifest.

    The roster's own ``audio_seconds`` is cross-checked against the header
    this pass reads, so a receipt that drifted from the corpus refuses before
    anything is written.
    """

    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= MAX_WORKERS:
        raise FlightProductError(f"workers must be an integer in [1, {MAX_WORKERS}]")
    items = sorted(
        (dict(item) for item in roster["items"]),  # type: ignore[union-attr]
        key=lambda item: str(item["sample_id"]),
    )
    confined: list[tuple[dict[str, object], str, Path]] = []
    for item in items:
        sample_id = str(item["sample_id"])
        if not sample_id.startswith("slurp:train:"):
            raise FlightProductError(f"{sample_id!r} is not a SLURP train identity")
        relpath = relpath_by_id.get(sample_id)
        if relpath is None:
            raise FlightProductError(f"{sample_id!r} is absent from the train loader")
        confined.append(
            (item, *_confined_media_path(data_root, relpath, context=f"fold row {sample_id!r}"))
        )
    with ThreadPoolExecutor(max_workers=min(workers, len(confined))) as pool:
        measured = tuple(pool.map(probe, (entry[2] for entry in confined)))

    manifest: list[dict[str, object]] = []
    for (item, media_relpath, _path), facts in zip(confined, measured, strict=True):
        media_bytes, media_sha256, header_seconds, sample_rate_hz = facts
        claimed = item.get("audio_seconds")
        if abs(float(claimed) - header_seconds) > 1e-6:  # type: ignore[arg-type]
            raise FlightProductError(
                f"audio duration drift for {item['sample_id']!r}: roster {claimed!r}, "
                f"header {header_seconds!r}"
            )
        manifest.append(
            {
                "id": str(item["sample_id"]),
                "media_relpath": media_relpath,
                "bytes": media_bytes,
                "sha256": media_sha256,
                "audio_seconds": round(float(header_seconds), 9),
                "sample_rate_hz": sample_rate_hz,
                "roles": ["query"],
            }
        )
    return manifest


def build_d1_supplement(
    manifest: Sequence[Mapping[str, object]],
    *,
    parent_d1: Mapping[str, object],
    parent_d1_sha256: str,
    source_binding_sha256: str,
) -> dict[str, object]:
    """The additive media receipt for one fold, in the gate's exact shape.

    ``contracts.gate_media_identity`` refuses a supplement entry that
    duplicates a base D1 sample, so an overlap is a hard refusal here rather
    than a skip: the immutable artifact records ZERO ``slurp:train:`` ids, and
    an overlap would mean the base artifact -- not this fold -- had changed.
    """

    media = parent_d1["carriers"][CARRIER]["layers"]["media"]["manifest"]  # type: ignore[index]
    base_ids = {str(entry["id"]) for entry in media}
    collisions = sorted(base_ids & {str(entry["id"]) for entry in manifest})
    if collisions:
        raise FlightProductError(
            f"{len(collisions)} fold rows are already in the immutable D1 artifact "
            f"(first: {collisions[0]!r}); the gate refuses a duplicated supplement entry"
        )
    entries = [dict(entry) for entry in manifest]
    ordered_ids = sorted(str(entry["id"]) for entry in entries)
    if len(ordered_ids) != len(set(ordered_ids)):
        raise FlightProductError("fold manifest contains a duplicate sample id")
    return {
        "schema": D1_SUPPLEMENT_SCHEMA,
        "study": STUDY,
        "carrier_lock_key": CARRIER,
        "parent_d1_sha256": parent_d1_sha256,
        "source_binding_sha256": source_binding_sha256,
        "count": len(entries),
        "ids_sha256": hashlib.sha256("\n".join(ordered_ids).encode("utf-8")).hexdigest(),
        "manifest": entries,
        "manifest_sha256": canonical_sha256(entries),
        "total_bytes": sum(int(entry["bytes"]) for entry in entries),
    }


def build_runtime_view(
    roster: Mapping[str, object],
    manifest: Sequence[Mapping[str, object]],
    *,
    supplement: Mapping[str, object],
    supplement_relpath: str,
    supplement_artifact_sha256: str,
    source_binding_sha256: str,
) -> dict[str, object]:
    """The label-free dataset fragment a composed config names."""

    if supplement.get("source_binding_sha256") != source_binding_sha256:
        raise FlightProductError("the supplement does not bind this roster receipt")
    items = [
        {
            "sample_id": str(entry["id"]),
            "media_relpath": entry["media_relpath"],
            "audio_sha256": entry["sha256"],
            "audio_seconds": entry["audio_seconds"],
            "sample_rate_hz": entry["sample_rate_hz"],
            "packet_id": str(entry["id"]).replace(":", "/"),
        }
        for entry in manifest
    ]
    unsigned: dict[str, object] = {
        "schema": RUNTIME_VIEW_SCHEMA,
        "study": STUDY,
        "status": VIEW_STATUS,
        "carrier_lock_key": CARRIER,
        "split_name": str(roster["roster_id"]),
        "split_role": str(roster["split_role"]),
        "seed": roster["seed"],
        "split_identity_hash": str(roster["split_identity_hash"]),
        "source_binding_sha256": source_binding_sha256,
        "d1_media_supplement": supplement_relpath,
        "d1_media_supplement_sha256": supplement_artifact_sha256,
        "d1_manifest_sha256": supplement["manifest_sha256"],
        "count": len(items),
        "audio_seconds_total": round(
            sum(float(item["audio_seconds"]) for item in items), 9
        ),
        "items": items,
    }
    return {**unsigned, "runtime_view_sha256": canonical_sha256(unsigned)}


def build_fold_products(
    roster: Mapping[str, object],
    *,
    slug: str,
    version: str,
    relpath_by_id: Mapping[str, str],
    data_root: Path,
    parent_d1: Mapping[str, object],
    parent_d1_sha256: str,
    feature_cache_root: Path,
    workers: int = MAX_WORKERS,
    writer: Callable[[str, object], str],
) -> dict[str, object]:
    """Build and hand out one fold's three artifacts, then report the facts.

    ``writer(relpath, document) -> file sha256`` is injected so this module
    never decides where an artifact lands (and a dry run can hash without
    touching the tree). The supplement is written FIRST because the runtime
    view has to carry its artifact hash.
    """

    binding_sha256 = canonical_sha256(roster)
    started = time.monotonic()
    manifest = measure_media(
        roster, relpath_by_id=relpath_by_id, data_root=data_root, workers=workers
    )
    elapsed = time.monotonic() - started
    supplement = build_d1_supplement(
        manifest,
        parent_d1=parent_d1,
        parent_d1_sha256=parent_d1_sha256,
        source_binding_sha256=binding_sha256,
    )
    supplement_relpath = f"docs/receipts/artifacts/d1-slurp-evo-{slug}-{version.lower()}.json"
    supplement_sha256 = writer(supplement_relpath, supplement)
    view = build_runtime_view(
        roster,
        manifest,
        supplement=supplement,
        supplement_relpath=supplement_relpath.removeprefix("docs/"),
        supplement_artifact_sha256=supplement_sha256,
        source_binding_sha256=binding_sha256,
    )
    probe = probe_receipt(view)
    view_relpath = f"configs/dataset/slurp-speech-native-evo-{slug}-{len(manifest)}.json"
    probe_relpath = f"docs/receipts/probe-samples/{view['split_name']}.json"
    return {
        "roster_id": roster["roster_id"],
        "roster_canonical_sha256": binding_sha256,
        "count": len(manifest),
        "audio_seconds_total": view["audio_seconds_total"],
        "channel_mix": channel_mix(roster),
        "split_identity_hash_run": view["split_identity_hash"],
        "split_identity_hash_receipt": probe["split_identity_hash"],
        "d1_media_supplement": supplement_relpath,
        "d1_media_supplement_sha256": supplement_sha256,
        "d1_manifest_sha256": supplement["manifest_sha256"],
        "d1_ids_sha256": supplement["ids_sha256"],
        "d1_total_bytes": supplement["total_bytes"],
        "dataset_fragment": view_relpath,
        "dataset_fragment_file_sha256": writer(view_relpath, view),
        "runtime_view_sha256": view["runtime_view_sha256"],
        "probe_sample_view": probe_relpath,
        "probe_sample_view_file_sha256": writer(probe_relpath, probe),
        "measure_wall_seconds": round(elapsed, 3),
        "measure_rows_per_second": round(len(manifest) / elapsed, 3) if elapsed else None,
        "measure_workers": workers,
        "packet_coverage": packet_coverage(
            manifest, feature_cache_root=feature_cache_root
        ),
    }


def probe_receipt(runtime_view: Mapping[str, object]) -> dict[str, object]:
    """Bind one runtime view into the probe-split format the driver reads.

    Written here rather than through
    ``e0.d1_identity.build_speech_native_probe_receipt`` for one reason: that
    helper's ``design`` sentence states the identity was "derived from the
    frozen speech-native train binding", which is true of TRAIN90 and false
    here. The shape, the two hash conventions and the ``slurp:<sample_id>``
    key convention are identical.
    """

    unsigned = {
        key: value for key, value in runtime_view.items() if key != "runtime_view_sha256"
    }
    if runtime_view.get("runtime_view_sha256") != canonical_sha256(unsigned):
        raise FlightProductError("runtime view SHA-256 mismatch")
    split_name = str(runtime_view["split_name"])
    keys = [f"{CARRIER}:{item['sample_id']}" for item in runtime_view["items"]]  # type: ignore[union-attr]
    if len(set(keys)) != len(keys):
        raise FlightProductError("runtime view has duplicate sample ids")
    return {
        "carrier": CARRIER,
        "design": (
            f"Exact label-free {split_name} identity derived from the frozen "
            "EVO-S1 fold roster receipt; construction-role Stage-2 discovery rows."
        ),
        "items": [
            {"id": str(item["sample_id"]), "key": key}
            for item, key in zip(runtime_view["items"], keys, strict=True)  # type: ignore[arg-type]
        ],
        "probe": "speech-native-runtime-view",
        "seed": runtime_view.get("seed"),
        "source_runtime_view_sha256": runtime_view.get("runtime_view_sha256"),
        "source_split_identity_hash": runtime_view.get("split_identity_hash"),
        "split_identity_hash": hashlib.sha256(
            "\n".join(sorted(keys)).encode("utf-8")
        ).hexdigest(),
        "split_role": str(runtime_view["split_role"]),
    }


def channel_mix(roster: Mapping[str, object]) -> dict[str, object]:
    """Headset / far-field counts and share, recomputed from the receipt."""

    items = list(roster["items"])  # type: ignore[arg-type]
    headset = sum(1 for item in items if item.get("headset"))
    return {
        "recordings": len(items),
        "headset_recordings": headset,
        "far_field_recordings": len(items) - headset,
        "headset_share": round(headset / len(items), 6) if items else 0.0,
    }


def packet_coverage(
    manifest: Sequence[Mapping[str, object]], *, feature_cache_root: Path
) -> dict[str, object]:
    """Model-free audit: how many of a fold's rows already have a packet.

    Presence in each packet root is the promoted packet DIRECTORY for that
    row's ``packet_id``; presence in a legacy cache is that root merely
    existing on disk with the row's cache key. Nothing is written and no
    feature is computed -- building a missing packet needs a model contact and
    is the flight agent's row.
    """

    root = Path(feature_cache_root)
    packet_ids = [str(entry["id"]).replace(":", "/") for entry in manifest]
    present: dict[str, int] = {}
    for name in PACKET_ROOTS:
        base = root / name
        present[name] = sum(1 for pid in packet_ids if (base / pid).is_dir())
    return {
        "feature_cache_root": str(root),
        "rows": len(packet_ids),
        "packets_present_by_root": present,
        "resident_packet_root": RESIDENT_PACKET_ROOT,
        "rows_needing_a_packet": len(packet_ids) - present.get(RESIDENT_PACKET_ROOT, 0),
        "legacy_caches_on_disk": [
            name for name in LEGACY_CACHES if (root / name).is_dir()
        ],
    }


__all__ = [
    "CARRIER",
    "D1_SUPPLEMENT_SCHEMA",
    "LEGACY_CACHES",
    "MAX_WORKERS",
    "PACKET_ROOTS",
    "RESIDENT_PACKET_ROOT",
    "RUNTIME_VIEW_SCHEMA",
    "FlightProductError",
    "build_d1_supplement",
    "build_fold_products",
    "build_runtime_view",
    "canonical_sha256",
    "channel_mix",
    "measure_media",
    "packet_coverage",
    "probe_receipt",
]
