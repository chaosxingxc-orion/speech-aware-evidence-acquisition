#!/usr/bin/env python3
"""Build the additive D1 media receipt for a SLURP roster that sits outside D1.

The immutable D1 identity artifact (``docs/receipts/artifacts/d1-identity.json``)
closes over the SLURP **devel** split only -- 8,690 recordings, zero
``slurp:train:`` ids -- so ``contracts.gate_media_identity.verify_media_identity``
refuses the model touch on every TRAIN row of a roster drawn from the
construction pool. The registered packet-promotion preflight for
``SLURP-STAGE3-CONSTRUCTION-R01`` died of exactly that, on its first roster row.

An additive supplement (schema ``saea-d1-media-supplement-v1``, the shape the
gate reads) closes the hole without touching the immutable artifact. This
builder is the SLURP sibling of
``scripts/build_a2t_tier1_official_population_d1_supplement.py`` and produces a
document byte-compatible with the two EVO fold supplements that
``analysis.slurp_evo_flight_products.build_d1_supplement`` wrote; it is
roster-parameterised (``--roster-receipt`` / ``--runtime-view`` / ``--output``)
so the next SLURP construction roster reuses it rather than adding a near
duplicate. The defaults name R01 because that is the roster it was written for.

Two source documents are read and cross-checked against each other, so a
supplement can never be built over a pair that has drifted apart:

* the **roster receipt** (``saea-roster-receipt-v1``) -- the identity
  statement. Its canonical SHA-256 becomes the supplement's
  ``source_binding_sha256``, which is also the value the runtime view already
  republishes as its own ``source_binding_sha256``; and
* the **runtime view** (``saea-speech-native-runtime-view-v1``) -- the
  label-free dataset fragment, which is where each row's ``media_relpath``
  lives. It is verified through its own ``runtime_view_sha256`` before a single
  media byte is read, and its id set must equal the roster's.

Base-closure ids are SKIPPED, not refused. The gate refuses a supplement entry
that duplicates a base D1 sample, so any roster id the immutable artifact
already records is verified byte-for-byte against the parent record instead and
named in the printed summary. R01 is all-TRAIN and base D1 records no TRAIN id,
so the expected skip count is zero -- but a roster that overlapped would be a
fact to report, not a crash.

Contact surface, stated once: each media file is re-hashed byte for byte and
only its container HEADER is read for duration and sample rate (never decoded).
No sentence, transcript, scenario, action, intent, entity, gold, score or future
turn is opened; the SLURP annotation loader is never consulted. Zero model,
network, tokenizer, scorer and GPU contacts. Only ids, counts and hashes are
printed.

With ``--write --pin-runtime-view`` the runtime view's ``d1_media_supplement``,
``d1_media_supplement_sha256`` and ``d1_manifest_sha256`` are filled in and its
``runtime_view_sha256`` is recomputed. The loader
(``data.slurp.load_speech_native_runtime_view``) requires an EXACT key set and
an all-or-nothing supplement triple, so the three fields and the signature move
together or not at all -- which is why this is code rather than a hand edit.
Pinning changes the composed config hash; re-pinning the readiness packages that
carry that hash is a separate, deliberate step and is never done here.

Run in WSL2 (the governed SLURP release lives under ``$SPEECHRL_DATA_DIR``)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/build_slurp_stage3_construction_r01_d1_supplement.py \\
      --write --pin-runtime-view
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.e0.d1_identity import (  # noqa: E402
    _confined_media_path,
    _probe_speech_media,
)

STUDY = "speech-aware-evidence-acquisition"
CARRIER = "slurp"
D1_SUPPLEMENT_SCHEMA = "saea-d1-media-supplement-v1"
ROSTER_SCHEMA = "saea-roster-receipt-v1"
RUNTIME_VIEW_SCHEMA = "saea-speech-native-runtime-view-v1"

DEFAULT_ROSTER = REPO_ROOT / "docs/receipts/rosters/slurp-stage3-construction-r01.json"
DEFAULT_RUNTIME_VIEW = (
    REPO_ROOT / "configs/dataset/slurp-speech-native-stage3-construction-r01.json"
)
DEFAULT_PARENT_D1 = REPO_ROOT / "docs/receipts/artifacts/d1-identity.json"
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs/receipts/artifacts/d1-slurp-stage3-construction-r01.json"
)
DEFAULT_SAMPLE_ID_PREFIX = "slurp:train:"

#: Owner rule (2026-09-03 pipeline directive): CPU preprocessing runs at 20
#: workers idle and AT MOST 8 while a GPU campaign flies. This builder can run
#: beside a flight, so 8 is its ceiling.
MAX_WORKERS = 8


class SupplementError(ValueError):
    """A supplement cannot be built from these inputs -- fail closed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(document: object) -> str:
    """SHA-256 over the canonical JSON serialization every receipt here uses."""

    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, document: object) -> str:
    """Write one receipt in the repository's committed JSON form, atomically."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
    temporary.replace(path)
    return sha256_file(path)


def _load_object(path: Path, label: str) -> Mapping[str, Any]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SupplementError(f"cannot read {label}: {error}") from error
    if not isinstance(document, Mapping):
        raise SupplementError(f"{label} must be a JSON object")
    return document


def _roster_sample_ids(roster: Mapping[str, Any]) -> list[str]:
    if roster.get("schema") != ROSTER_SCHEMA:
        raise SupplementError(f"roster receipt schema must be {ROSTER_SCHEMA!r}")
    if roster.get("carrier_lock_key") != CARRIER:
        raise SupplementError(f"roster receipt carrier must be {CARRIER!r}")
    # A tripwire, and a narrow one: it refuses the literal split_role value
    # "test", which no roster this repository has ever frozen uses. It is NOT
    # the guard that keeps a held-out split safe, and it never was -- a D1
    # media supplement carries media identity only (relpath, bytes, SHA-256,
    # header duration, sample rate) and no annotation of any kind, so building
    # one can never make a gold field reachable.
    #
    # SLURP-TEST-FULL-13078-V1 (owner decisions 99 of 2026-09-22 and 107 of
    # 2026-09-23) is supplemented here deliberately, with
    # --sample-id-prefix slurp:test:, because the immutable D1 artifact closes
    # over the SLURP devel split only and every test row therefore sits outside
    # it. Its roster declares split_role "final-report", and the guard that
    # actually governs it is contracts.plan.require_owner_split_allowance,
    # which refuses every final-report ExecutionPlan until the committed
    # owner-allowance receipt says "authorised".
    if roster.get("split_role") == "test":
        raise SupplementError("a test-split roster is never supplemented here")
    items = roster.get("items")
    if not isinstance(items, list) or not items:
        raise SupplementError("roster receipt carries no items")
    ids: list[str] = []
    for item in items:
        if not isinstance(item, Mapping):
            raise SupplementError("roster receipt item must be an object")
        sample_id = item.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise SupplementError("roster receipt sample ids are malformed")
        ids.append(sample_id)
    if len(set(ids)) != len(ids):
        raise SupplementError("roster receipt repeats a sample id")
    return ids


def _runtime_view_items(
    view: Mapping[str, Any], *, sample_id_prefix: str
) -> list[dict[str, Any]]:
    """The view's rows, after the view has proved its own signature."""

    if view.get("schema") != RUNTIME_VIEW_SCHEMA:
        raise SupplementError(f"runtime view schema must be {RUNTIME_VIEW_SCHEMA!r}")
    if view.get("study") != STUDY or view.get("carrier_lock_key") != CARRIER:
        raise SupplementError("runtime view study or carrier identity mismatch")
    signature = view.get("runtime_view_sha256")
    unsigned = {key: value for key, value in view.items() if key != "runtime_view_sha256"}
    if signature != canonical_sha256(unsigned):
        raise SupplementError("runtime view runtime_view_sha256 mismatch")
    items = view.get("items")
    if not isinstance(items, list) or not items or view.get("count") != len(items):
        raise SupplementError("runtime view count disagrees with its own items")
    item_keys = {
        "sample_id",
        "media_relpath",
        "audio_sha256",
        "audio_seconds",
        "sample_rate_hz",
        "packet_id",
    }
    rows: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, Mapping) or set(item) != item_keys:
            raise SupplementError(
                "runtime view items must be label-free and carry exact keys "
                f"{sorted(item_keys)}"
            )
        sample_id = item["sample_id"]
        if not isinstance(sample_id, str) or not sample_id.startswith(sample_id_prefix):
            raise SupplementError(
                f"runtime view sample ids must start with {sample_id_prefix!r}"
            )
        if item["packet_id"] != sample_id.replace(":", "/"):
            raise SupplementError(f"runtime view packet id disagrees for {sample_id!r}")
        rows.append(dict(item))
    return sorted(rows, key=lambda row: str(row["sample_id"]))


def _parent_media_records(parent: Mapping[str, Any]) -> dict[str, tuple[object, object]]:
    """``{sample_id: (bytes, sha256)}`` from the immutable artifact's SLURP media
    layer -- the same manifest ``contracts.gate_media_identity`` reads."""

    carriers = parent.get("carriers")
    carrier = carriers.get(CARRIER) if isinstance(carriers, Mapping) else None
    layers = carrier.get("layers") if isinstance(carrier, Mapping) else None
    media = layers.get("media") if isinstance(layers, Mapping) else None
    manifest = media.get("manifest") if isinstance(media, Mapping) else None
    if not isinstance(manifest, list):
        raise SupplementError(f"parent D1 lacks the {CARRIER!r} media manifest")
    records: dict[str, tuple[object, object]] = {}
    for entry in manifest:
        if not isinstance(entry, Mapping):
            raise SupplementError("parent D1 media manifest entry is not an object")
        sample_id = entry.get("id")
        if not isinstance(sample_id, str) or not sample_id or sample_id in records:
            raise SupplementError("parent D1 media ids are malformed or duplicated")
        records[sample_id] = (entry.get("bytes"), entry.get("sha256"))
    return records


def _agrees(claimed: object, measured: float) -> bool:
    return (
        not isinstance(claimed, bool)
        and isinstance(claimed, (int, float))
        and math.isfinite(float(claimed))
        and abs(float(claimed) - measured) <= 1e-6
    )


def build_supplement(
    *,
    roster_path: Path,
    runtime_view_path: Path,
    data_root: Path,
    parent_d1_path: Path,
    sample_id_prefix: str = DEFAULT_SAMPLE_ID_PREFIX,
    workers: int = MAX_WORKERS,
    probe: Callable[[Path], tuple[int, str, float, int]] = _probe_speech_media,
) -> tuple[dict[str, object], list[str]]:
    """``(supplement, skipped_ids)`` -- the additive media receipt for every
    roster row the immutable D1 artifact does NOT already record.

    Deterministic: rows are measured in sorted id order, durations are rounded
    to nine decimals, and every hash is taken over the canonical serialization,
    so two runs over unchanged bytes produce byte-identical output.
    """

    if (
        isinstance(workers, bool)
        or not isinstance(workers, int)
        or not 1 <= workers <= MAX_WORKERS
    ):
        raise SupplementError(f"workers must be an integer in [1, {MAX_WORKERS}]")
    roster = _load_object(roster_path, "roster receipt")
    roster_ids = _roster_sample_ids(roster)
    roster_seconds = {
        str(item["sample_id"]): item.get("audio_seconds")
        for item in roster["items"]
    }
    view = _load_object(runtime_view_path, "runtime view")
    rows = _runtime_view_items(view, sample_id_prefix=sample_id_prefix)
    source_binding_sha256 = canonical_sha256(roster)
    if view.get("source_binding_sha256") != source_binding_sha256:
        raise SupplementError(
            "the runtime view does not bind this roster receipt "
            "(source_binding_sha256 disagree)"
        )
    if {str(row["sample_id"]) for row in rows} != set(roster_ids):
        raise SupplementError("roster receipt and runtime view name different samples")

    root = Path(data_root)
    confined: list[tuple[dict[str, Any], str, Path]] = []
    for row in rows:
        sample_id = str(row["sample_id"])
        relpath, resolved = _confined_media_path(
            root, row["media_relpath"], context=f"roster row {sample_id!r}"
        )
        confined.append((row, relpath, resolved))
    with ThreadPoolExecutor(
        max_workers=min(workers, len(confined)),
        thread_name_prefix="saea-d1-supplement",
    ) as pool:
        measured = tuple(pool.map(probe, (entry[2] for entry in confined)))

    base_records = _parent_media_records(_load_object(parent_d1_path, "parent D1"))
    manifest: list[dict[str, object]] = []
    skipped: list[str] = []
    for (row, relpath, _path), facts in zip(confined, measured, strict=True):
        sample_id = str(row["sample_id"])
        media_bytes, media_sha256, header_seconds, sample_rate_hz = facts
        if media_sha256 != row["audio_sha256"]:
            raise SupplementError(f"media hash drift for {sample_id!r}")
        if not _agrees(row["audio_seconds"], header_seconds):
            raise SupplementError(f"audio duration drift for {sample_id!r}")
        if not _agrees(roster_seconds.get(sample_id), header_seconds):
            raise SupplementError(f"roster audio duration drift for {sample_id!r}")
        if row["sample_rate_hz"] != int(sample_rate_hz):
            raise SupplementError(f"sample rate drift for {sample_id!r}")
        base = base_records.get(sample_id)
        if base is not None:
            # Already inside the immutable D1 identity artifact. The gate
            # refuses a supplement entry that duplicates a base D1 sample, so
            # this id is verified against the parent record -- the only two
            # per-media facts that artifact carries -- and then skipped.
            base_bytes, base_sha256 = base
            if base_sha256 != media_sha256 or base_bytes != int(media_bytes):
                raise SupplementError(
                    f"{sample_id!r} is in parent D1 with a different media identity; "
                    "refusing to supplement over an identity disagreement"
                )
            skipped.append(sample_id)
            continue
        manifest.append(
            {
                "id": sample_id,
                "media_relpath": relpath,
                "bytes": int(media_bytes),
                "sha256": media_sha256,
                "audio_seconds": round(float(header_seconds), 9),
                "sample_rate_hz": int(sample_rate_hz),
                "roles": ["query"],
            }
        )

    if not manifest:
        raise SupplementError(
            "every roster row is already inside the immutable D1 closure; "
            "no supplement is needed or legal"
        )
    ordered_ids = sorted(str(entry["id"]) for entry in manifest)
    supplement: dict[str, object] = {
        "schema": D1_SUPPLEMENT_SCHEMA,
        "study": STUDY,
        "carrier_lock_key": CARRIER,
        "parent_d1_sha256": sha256_file(parent_d1_path),
        "source_binding_sha256": source_binding_sha256,
        "count": len(manifest),
        "ids_sha256": hashlib.sha256("\n".join(ordered_ids).encode("utf-8")).hexdigest(),
        "manifest": manifest,
        "manifest_sha256": canonical_sha256(manifest),
        "total_bytes": sum(int(entry["bytes"]) for entry in manifest),
    }
    return supplement, skipped


def pin_runtime_view(
    view: Mapping[str, Any],
    *,
    supplement: Mapping[str, Any],
    supplement_relpath: str,
    supplement_artifact_sha256: str,
) -> dict[str, Any]:
    """The runtime view with its D1 supplement triple filled in and its
    ``runtime_view_sha256`` recomputed.

    ``data.slurp.load_speech_native_runtime_view`` requires an EXACT key set and
    an all-or-nothing supplement triple, so no key is added or removed here and
    all three move together. ``supplement_relpath`` is the path RELATIVE TO
    ``<repo>/docs``, which is what ``contracts.gate.FrozenCoreGate.for_study_repo``
    resolves the configured value under.
    """

    if supplement.get("schema") != D1_SUPPLEMENT_SCHEMA:
        raise SupplementError("only a saea-d1-media-supplement-v1 document may be pinned")
    if supplement.get("source_binding_sha256") != view.get("source_binding_sha256"):
        raise SupplementError("the supplement does not bind this runtime view's roster")
    if supplement_relpath.startswith("docs/") or supplement_relpath.startswith("/"):
        raise SupplementError(
            "d1_media_supplement is resolved under <repo>/docs and must not repeat it"
        )
    unsigned = {key: value for key, value in view.items() if key != "runtime_view_sha256"}
    unsigned["d1_media_supplement"] = supplement_relpath
    unsigned["d1_media_supplement_sha256"] = supplement_artifact_sha256
    unsigned["d1_manifest_sha256"] = supplement["manifest_sha256"]
    return {**unsigned, "runtime_view_sha256": canonical_sha256(unsigned)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roster-receipt", type=Path, default=DEFAULT_ROSTER)
    parser.add_argument("--runtime-view", type=Path, default=DEFAULT_RUNTIME_VIEW)
    parser.add_argument("--parent-d1", type=Path, default=DEFAULT_PARENT_D1)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--sample-id-prefix", default=DEFAULT_SAMPLE_ID_PREFIX)
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--write", action="store_true")
    parser.add_argument(
        "--pin-runtime-view",
        action="store_true",
        help=(
            "also fill the runtime view's D1 supplement triple and recompute its "
            "runtime_view_sha256 (requires --write); this changes the composed "
            "config hash, and re-pinning readiness packages is a separate step"
        ),
    )
    args = parser.parse_args(argv)
    if args.pin_runtime_view and not args.write:
        raise SystemExit("--pin-runtime-view requires --write")

    root = args.data_root
    if root is None:
        value = os.environ.get("SPEECHRL_DATA_DIR")
        if not value:
            raise SystemExit("--data-root or SPEECHRL_DATA_DIR is required")
        root = Path(value)

    supplement, skipped = build_supplement(
        roster_path=args.roster_receipt,
        runtime_view_path=args.runtime_view,
        data_root=root,
        parent_d1_path=args.parent_d1,
        sample_id_prefix=args.sample_id_prefix,
        workers=args.workers,
    )
    payload = json.dumps(supplement, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if args.write:
        output_sha256 = write_json(Path(args.output), supplement)

    runtime_view_sha256 = None
    if args.pin_runtime_view:
        relpath = Path(args.output).resolve().relative_to(REPO_ROOT / "docs").as_posix()
        view = _load_object(args.runtime_view, "runtime view")
        pinned = pin_runtime_view(
            view,
            supplement=supplement,
            supplement_relpath=relpath,
            supplement_artifact_sha256=output_sha256,
        )
        write_json(Path(args.runtime_view), pinned)
        runtime_view_sha256 = pinned["runtime_view_sha256"]

    print(
        json.dumps(
            {
                "count": supplement["count"],
                "ids_sha256": supplement["ids_sha256"],
                "manifest_sha256": supplement["manifest_sha256"],
                "output": str(args.output),
                "output_sha256": output_sha256,
                "parent_d1_sha256": supplement["parent_d1_sha256"],
                "pinned_runtime_view": (
                    str(args.runtime_view) if args.pin_runtime_view else None
                ),
                "pinned_runtime_view_sha256": runtime_view_sha256,
                "roster_rows": supplement["count"] + len(skipped),
                "skipped_already_in_parent_d1": skipped,
                "skipped_already_in_parent_d1_count": len(skipped),
                "source_binding_sha256": supplement["source_binding_sha256"],
                "total_bytes": supplement["total_bytes"],
                "written": args.write,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
