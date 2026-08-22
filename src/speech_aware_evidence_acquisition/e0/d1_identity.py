"""E0 D1: cross-layer sample/segment identity closure for this study's carriers.

Hard invariants for the three CORE carriers (generation fails closed if any is
violated):

- Earnings21: media, file metadata, NLP references, WER tags and normalizations all
  name exactly the same 44 samples (counts cross-checked against the umbrella lock's
  own verification block).
- Earnings22: media, metadata rows, NLP references and force-aligned references all
  name exactly the same 125 samples; the upstream ten-call subset is a subset.
- ConEC (Earnings21 side): contexts, corrected NLP references, timestamps and WER
  tags all name exactly the Earnings21 identity set — every core call has context.

Two bounded-discovery-probe carriers (SLURP, Audio2Tool -- 2026-08-15 owner
amendment) are ALSO closed here, with a deliberately narrower single-layer MEDIA
identity only (``data.identity.slurp_layers``/``audio2tool_layers`` own docstrings
have the full scope account) -- this is what lets
``contracts.gate_media_identity.verify_media_identity`` accept those two carrier
lock keys instead of refusing with "D1 identity artifact has no per-sample media
identity for carrier ...". Closure is unconditional (same fail-closed discipline
as the three core carriers): a caller lacking SLURP/Audio2Tool data or lock
entries gets D1 generation refused outright, never a silently narrower artifact.

The artifact embeds per-file byte/SHA-256 manifests for every layer (segment-grade
binding) plus license/redistribution facts read live from the umbrella lock. It
contains IDs, counts and digests only — no transcript, annotation or context text.
"""

from __future__ import annotations

import hashlib
import json
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Mapping

from ..data.identity import (
    IdentityError,
    Layer,
    layer_report,
    relations_report,
    require_equal,
    require_subset,
    audio2tool_layers,
    conec_layers,
    earnings21_layers,
    earnings22_layers,
    slurp_layers,
)
from ..data.lock import CORE_CARRIER_LOCK_KEYS, asset_dir, load_lock, lock_entry
from .artifacts import sha256_file, today


def _canonical_sha256(document: object) -> str:
    raw = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _confined_media_path(data_root: Path, relpath: object, *, context: str) -> tuple[str, Path]:
    if not isinstance(relpath, str) or not relpath or "\\" in relpath:
        raise IdentityError(f"{context} media_relpath must be a non-empty POSIX relative path")
    relative = Path(relpath)
    if relative.is_absolute() or any(part in ("", ".", "..") for part in relative.parts):
        raise IdentityError(f"{context} media_relpath is absolute or contains traversal")
    root = Path(data_root).resolve(strict=True)
    try:
        resolved = (root / relative).resolve(strict=True)
    except OSError as error:
        raise IdentityError(f"{context} media is unavailable: {error}") from error
    if not resolved.is_file() or not resolved.is_relative_to(root):
        raise IdentityError(f"{context} media path escapes the governed data root")
    return relpath, resolved


def _probe_speech_media(path: Path) -> tuple[int, str, float, int]:
    """Measure bytes/hash and header-only duration/rate for one speech file."""

    import soundfile  # deferred: keep the package import light

    digest = hashlib.sha256()
    size = 0
    try:
        with Path(path).open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
        info = soundfile.info(str(path))
    except Exception as error:
        raise IdentityError(f"cannot measure bounded speech media {path}: {error}") from error
    if size <= 0 or info.samplerate <= 0 or info.frames <= 0:
        raise IdentityError(f"bounded speech media {path} has invalid byte/header facts")
    return size, digest.hexdigest(), float(info.frames / info.samplerate), int(info.samplerate)


def _load_verified_speech_native_binding(
    binding_path: Path,
) -> tuple[Mapping[str, object], str]:
    try:
        binding = json.loads(Path(binding_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise IdentityError(f"cannot read speech-native binding {binding_path}: {error}") from error
    if not isinstance(binding, Mapping):
        raise IdentityError("speech-native binding must be a JSON object")
    claimed = binding.get("binding_sha256")
    unsigned = {key: value for key, value in binding.items() if key != "binding_sha256"}
    if not isinstance(claimed, str) or claimed != _canonical_sha256(unsigned):
        raise IdentityError("speech-native binding SHA-256 mismatch")
    return binding, claimed


def build_d1_media_supplement(
    *,
    binding_path: Path,
    data_root: Path,
    parent_d1_path: Path,
    workers: int = 16,
    expected_query_count: int = 72,
    expected_audio_key_count: int = 18,
    media_probe: Callable[[Path], tuple[int, str, float, int]] = _probe_speech_media,
) -> dict[str, object]:
    """Build the bounded SLURP-train media successor for speech-native work.

    The immutable E0 D1 artifact remains untouched. This supplement closes
    exactly the query samples and audio-key sources named by the existing
    speech-native binding, carries no sentence, label, or transcript text,
    and is independently digest-pinned by the composed run config. Independent
    media files are measured concurrently while output order stays canonical.
    """

    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 64:
        raise IdentityError("D1 media supplement workers must be an integer in [1, 64]")
    for name, value in (
        ("expected_query_count", expected_query_count),
        ("expected_audio_key_count", expected_audio_key_count),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise IdentityError(f"{name} must be a positive integer")
    binding, claimed_binding_sha256 = _load_verified_speech_native_binding(binding_path)

    selected: dict[str, dict[str, object]] = {}

    def add(sample_id: object, media_relpath: object, role: str) -> None:
        if not isinstance(sample_id, str) or not sample_id.startswith("slurp:train:"):
            raise IdentityError(f"D1 supplement {role} sample is not SLURP train: {sample_id!r}")
        if not isinstance(media_relpath, str) or not media_relpath.startswith(
            "datasets/slurp/slurp_real/"
        ):
            raise IdentityError(
                f"D1 supplement {sample_id!r} is not bound to real SLURP speech"
            )
        entry = selected.setdefault(
            sample_id, {"media_relpath": media_relpath, "roles": []}
        )
        if entry["media_relpath"] != media_relpath:
            raise IdentityError(f"D1 supplement sample {sample_id!r} has conflicting media paths")
        roles = entry["roles"]
        if not isinstance(roles, list):  # defensive: locally constructed above
            raise IdentityError("D1 supplement roles are malformed")
        if role not in roles:
            roles.append(role)

    splits = binding.get("splits")
    if not isinstance(splits, Mapping):
        raise IdentityError("speech-native binding lacks scientific splits")
    query_ids: set[str] = set()
    for split_name in sorted(splits):
        split = splits.get(split_name)
        items = split.get("items") if isinstance(split, Mapping) else None
        if not isinstance(items, list):
            raise IdentityError(f"speech-native binding split {split_name!r} lacks items")
        for item in items:
            if not isinstance(item, Mapping):
                raise IdentityError(f"speech-native binding split {split_name!r} item is malformed")
            sample_id = item.get("sample_id")
            if sample_id in query_ids:
                raise IdentityError(f"duplicate speech-native query sample {sample_id!r}")
            if isinstance(sample_id, str):
                query_ids.add(sample_id)
            add(sample_id, item.get("media_relpath"), "query")
    if len(query_ids) != expected_query_count:
        raise IdentityError(
            f"speech-native binding selects {len(query_ids)} queries, expected "
            f"{expected_query_count}"
        )

    key_material = binding.get("key_material")
    if not isinstance(key_material, list):
        raise IdentityError("speech-native binding lacks key_material")
    audio_key_ids: set[str] = set()
    for key in key_material:
        if not isinstance(key, Mapping):
            raise IdentityError("speech-native key material entry is malformed")
        sample_id = key.get("audio_key_source_sample_id")
        sources = key.get("sources")
        if not isinstance(sources, list):
            raise IdentityError("speech-native key material sources are malformed")
        matching = [source for source in sources if isinstance(source, Mapping) and source.get("sample_id") == sample_id]
        if len(matching) != 1:
            raise IdentityError(
                f"audio key sample {sample_id!r} must resolve to exactly one key source"
            )
        if sample_id in audio_key_ids:
            raise IdentityError(f"duplicate speech-native audio key sample {sample_id!r}")
        if isinstance(sample_id, str):
            audio_key_ids.add(sample_id)
        add(sample_id, matching[0].get("media_relpath"), "audio_key")
    if len(audio_key_ids) != expected_audio_key_count:
        raise IdentityError(
            f"speech-native binding selects {len(audio_key_ids)} audio keys, expected "
            f"{expected_audio_key_count}"
        )

    ordered = sorted(selected.items())
    confined = [
        (
            sample_id,
            *_confined_media_path(
                Path(data_root),
                entry["media_relpath"],
                context=f"D1 supplement sample {sample_id!r}",
            ),
            entry["roles"],
        )
        for sample_id, entry in ordered
    ]

    worker_count = min(workers, len(confined))
    if worker_count == 1:
        measured = tuple(media_probe(entry[2]) for entry in confined)
    else:
        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="saea-d1-speech-media",
        ) as pool:
            measured = tuple(pool.map(media_probe, (entry[2] for entry in confined)))

    manifest: list[dict[str, object]] = []
    for (sample_id, media_relpath, _path, roles), facts in zip(
        confined, measured, strict=True
    ):
        media_bytes, media_sha256, audio_seconds, sample_rate_hz = facts
        if (
            isinstance(media_bytes, bool)
            or not isinstance(media_bytes, int)
            or media_bytes <= 0
            or not isinstance(media_sha256, str)
            or len(media_sha256) != 64
            or isinstance(audio_seconds, bool)
            or not isinstance(audio_seconds, (int, float))
            or not math.isfinite(audio_seconds)
            or audio_seconds <= 0
            or isinstance(sample_rate_hz, bool)
            or not isinstance(sample_rate_hz, int)
            or sample_rate_hz <= 0
        ):
            raise IdentityError(f"invalid measured media facts for {sample_id!r}")
        manifest.append(
            {
                "id": sample_id,
                "media_relpath": media_relpath,
                "bytes": media_bytes,
                "sha256": media_sha256,
                "audio_seconds": round(float(audio_seconds), 9),
                "sample_rate_hz": sample_rate_hz,
                "roles": sorted(roles, key=("query", "audio_key").index),
            }
        )
    ids = [entry["id"] for entry in manifest]
    return {
        "schema": "saea-d1-media-supplement-v1",
        "study": "speech-aware-evidence-acquisition",
        "carrier_lock_key": "slurp",
        "parent_d1_sha256": sha256_file(parent_d1_path),
        "source_binding_sha256": claimed_binding_sha256,
        "count": len(manifest),
        "ids_sha256": hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest(),
        "manifest": manifest,
        "manifest_sha256": _canonical_sha256(manifest),
        "total_bytes": sum(int(entry["bytes"]) for entry in manifest),
    }


_SPEECH_NATIVE_RUNTIME_COUNTS: Mapping[str, int] = {
    "ENG-GATE8": 8,
    "OPT-A36": 36,
    "OPT-B18": 18,
    "GATE18": 18,
    "KEY18": 18,
    "TRAIN90": 90,
    "DISCOVERY-X108": 108,
}


def _speech_native_runtime_selection(
    binding: Mapping[str, object], selection_name: str
) -> tuple[list[Mapping[str, object]], int, str]:
    if selection_name == "ENG-GATE8":
        source = binding.get("engineering_gate")
    elif selection_name in ("KEY18", "TRAIN90"):
        seed = binding.get("seed")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise IdentityError("speech-native binding seed is malformed")
        selected: list[Mapping[str, object]] = []
        if selection_name == "TRAIN90":
            splits = binding.get("splits")
            if not isinstance(splits, Mapping):
                raise IdentityError("speech-native binding lacks scientific splits")
            for split_name in ("OPT-A36", "OPT-B18", "GATE18"):
                split = splits.get(split_name)
                split_items = split.get("items") if isinstance(split, Mapping) else None
                if not isinstance(split_items, list) or not all(
                    isinstance(item, Mapping) for item in split_items
                ):
                    raise IdentityError(
                        f"speech-native binding split {split_name!r} lacks items"
                    )
                selected.extend(split_items)
        key_material = binding.get("key_material")
        if not isinstance(key_material, list):
            raise IdentityError("speech-native binding lacks key_material")
        for key in key_material:
            if not isinstance(key, Mapping):
                raise IdentityError("speech-native key material entry is malformed")
            sample_id = key.get("audio_key_source_sample_id")
            sources = key.get("sources")
            if not isinstance(sources, list):
                raise IdentityError("speech-native key material sources are malformed")
            matches = [
                item
                for item in sources
                if isinstance(item, Mapping) and item.get("sample_id") == sample_id
            ]
            if len(matches) != 1:
                raise IdentityError(
                    f"audio key sample {sample_id!r} must resolve to exactly one source"
                )
            selected.append(matches[0])
        sample_ids = [item.get("sample_id") for item in selected]
        if not all(isinstance(sample_id, str) for sample_id in sample_ids):
            raise IdentityError(f"speech-native selection {selection_name!r} has malformed ids")
        if len(set(sample_ids)) != len(sample_ids):
            raise IdentityError(f"speech-native selection {selection_name!r} has duplicate ids")
        identity = {
            "schema": "saea-speech-native-split-v1",
            "name": selection_name,
            "seed": seed,
            "sample_ids": sample_ids,
        }
        return selected, seed, _canonical_sha256(identity)
    else:
        splits = binding.get("splits")
        source = splits.get(selection_name) if isinstance(splits, Mapping) else None

    if not isinstance(source, Mapping):
        raise IdentityError(f"speech-native binding lacks selection {selection_name!r}")
    items = source.get("items")
    sample_ids = source.get("sample_ids")
    seed = source.get("seed")
    if (
        not isinstance(items, list)
        or not all(isinstance(item, Mapping) for item in items)
        or not isinstance(sample_ids, list)
        or isinstance(seed, bool)
        or not isinstance(seed, int)
    ):
        raise IdentityError(f"speech-native selection {selection_name!r} is malformed")
    actual_ids = [item.get("sample_id") for item in items]
    if actual_ids != sample_ids or not all(isinstance(sample_id, str) for sample_id in sample_ids):
        raise IdentityError(
            f"speech-native selection {selection_name!r} item order disagrees with sample_ids"
        )
    identity = {
        "schema": "saea-speech-native-split-v1",
        "name": selection_name,
        "seed": seed,
        "sample_ids": sample_ids,
    }
    split_identity_hash = _canonical_sha256(identity)
    if source.get("split_identity_hash") != split_identity_hash:
        raise IdentityError(
            f"speech-native selection {selection_name!r} identity hash mismatch"
        )
    return items, seed, split_identity_hash


def _build_speech_native_runtime_view(
    *,
    binding_path: Path,
    supplement: Mapping[str, object],
    supplement_artifact_sha256: str,
    selection_name: str,
    expected_count: int,
    schema: str,
    supplement_relpath: str = "receipts/artifacts/d1-speech-native-train90.json",
) -> dict[str, object]:
    """Derive one label-free runtime view from the frozen train binding."""

    binding, binding_sha256 = _load_verified_speech_native_binding(binding_path)
    if (
        not isinstance(supplement_artifact_sha256, str)
        or len(supplement_artifact_sha256) != 64
        or any(ch not in "0123456789abcdef" for ch in supplement_artifact_sha256)
    ):
        raise IdentityError("D1 supplement artifact SHA-256 must be lowercase 64-hex")
    if not isinstance(supplement_relpath, str) or not supplement_relpath:
        raise IdentityError("D1 supplement relative path must be non-empty")
    if supplement.get("source_binding_sha256") != binding_sha256:
        raise IdentityError("D1 supplement does not bind the selected speech-native binding")
    manifest = supplement.get("manifest")
    if not isinstance(manifest, list):
        raise IdentityError("D1 supplement manifest is missing")
    by_id = {
        entry.get("id"): entry
        for entry in manifest
        if isinstance(entry, Mapping) and isinstance(entry.get("id"), str)
    }
    if len(by_id) != len(manifest):
        raise IdentityError("D1 supplement manifest ids are malformed or duplicated")
    if isinstance(expected_count, bool) or not isinstance(expected_count, int) or expected_count <= 0:
        raise IdentityError("speech-native runtime view expected_count must be positive")
    source_items, seed, split_identity_hash = _speech_native_runtime_selection(
        binding, selection_name
    )
    if len(source_items) != expected_count:
        raise IdentityError(
            f"speech-native selection {selection_name!r} carries {len(source_items)} items, "
            f"expected {expected_count}"
        )
    items: list[dict[str, object]] = []
    for item in source_items:
        sample_id = item.get("sample_id")
        media_relpath = item.get("media_relpath")
        measured = by_id.get(sample_id)
        if not isinstance(sample_id, str) or not isinstance(measured, Mapping):
            raise IdentityError(
                f"speech-native selection {selection_name!r} sample {sample_id!r} "
                "lacks D1 supplement facts"
            )
        if not isinstance(media_relpath, str) or measured.get("media_relpath") != media_relpath:
            raise IdentityError(
                f"speech-native selection {selection_name!r} sample {sample_id!r} "
                "media path drift"
            )
        parts = sample_id.split(":")
        if len(parts) != 4 or parts[0:2] != ["slurp", "train"]:
            raise IdentityError(f"speech-native sample id is malformed: {sample_id!r}")
        items.append(
            {
                "sample_id": sample_id,
                "media_relpath": media_relpath,
                "audio_sha256": measured["sha256"],
                "audio_seconds": measured["audio_seconds"],
                "sample_rate_hz": measured["sample_rate_hz"],
                "packet_id": "/".join(parts),
            }
        )
    unsigned: dict[str, object] = {
        "schema": schema,
        "study": "speech-aware-evidence-acquisition",
        "status": "MODEL-FREE, LABEL-FREE ENGINEERING INPUT; NOT AN EXPOSURE REGISTRATION",
        "carrier_lock_key": "slurp",
        "split_name": selection_name,
        "split_role": "discovery",
        "seed": seed,
        "split_identity_hash": split_identity_hash,
        "source_binding_sha256": binding_sha256,
        "d1_media_supplement": supplement_relpath,
        "d1_media_supplement_sha256": supplement_artifact_sha256,
        "d1_manifest_sha256": supplement.get("manifest_sha256"),
        "count": len(items),
        "audio_seconds_total": round(
            sum(float(item["audio_seconds"]) for item in items), 9
        ),
        "items": items,
    }
    return {**unsigned, "runtime_view_sha256": _canonical_sha256(unsigned)}


def build_speech_native_runtime_view(
    *,
    binding_path: Path,
    supplement: Mapping[str, object],
    supplement_artifact_sha256: str,
    selection_name: str,
    expected_count: int | None = None,
    supplement_relpath: str = "receipts/artifacts/d1-speech-native-train90.json",
) -> dict[str, object]:
    """Build a label-free runtime view for a scientific or preprocessing slice."""

    count = _SPEECH_NATIVE_RUNTIME_COUNTS.get(selection_name) if expected_count is None else expected_count
    if count is None:
        raise IdentityError(f"unknown speech-native runtime selection {selection_name!r}")
    return _build_speech_native_runtime_view(
        binding_path=binding_path,
        supplement=supplement,
        supplement_artifact_sha256=supplement_artifact_sha256,
        selection_name=selection_name,
        expected_count=count,
        schema="saea-speech-native-runtime-view-v1",
        supplement_relpath=supplement_relpath,
    )


def build_speech_native_engineering_gate_view(
    *,
    binding_path: Path,
    supplement: Mapping[str, object],
    supplement_artifact_sha256: str,
    supplement_relpath: str = "receipts/artifacts/d1-speech-native-train90.json",
) -> dict[str, object]:
    """Backward-compatible ENG-GATE8 view for historical configs and receipts."""

    binding, _binding_sha256 = _load_verified_speech_native_binding(binding_path)
    engineering = binding.get("engineering_gate")
    engineering_items = engineering.get("items") if isinstance(engineering, Mapping) else None
    if not isinstance(engineering_items, list) or not engineering_items:
        raise IdentityError("speech-native binding lacks ENG-GATE8 items")
    return _build_speech_native_runtime_view(
        binding_path=binding_path,
        supplement=supplement,
        supplement_artifact_sha256=supplement_artifact_sha256,
        selection_name="ENG-GATE8",
        expected_count=len(engineering_items),
        schema="saea-speech-native-engineering-gate-view-v1",
        supplement_relpath=supplement_relpath,
    )


def build_speech_native_probe_receipt(
    runtime_view: Mapping[str, object],
) -> dict[str, object]:
    """Bind one label-free runtime view into the existing probe-split format."""

    unsigned = {
        key: value for key, value in runtime_view.items() if key != "runtime_view_sha256"
    }
    runtime_view_sha256 = runtime_view.get("runtime_view_sha256")
    if runtime_view_sha256 != _canonical_sha256(unsigned):
        raise IdentityError("speech-native runtime view SHA-256 mismatch")
    split_name = runtime_view.get("split_name")
    items = runtime_view.get("items")
    if (
        not isinstance(split_name, str)
        or not split_name
        or any(
            character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
            for character in split_name
        )
        or not isinstance(items, list)
        or not items
    ):
        raise IdentityError("speech-native runtime view cannot form a probe receipt")
    receipt_items: list[dict[str, str]] = []
    keys: list[str] = []
    for item in items:
        sample_id = item.get("sample_id") if isinstance(item, Mapping) else None
        if not isinstance(sample_id, str):
            raise IdentityError("speech-native runtime view has a malformed sample id")
        key = f"slurp:{sample_id}"
        receipt_items.append({"id": sample_id, "key": key})
        keys.append(key)
    if len(set(keys)) != len(keys):
        raise IdentityError("speech-native runtime view has duplicate sample ids")
    return {
        "carrier": "slurp",
        "design": (
            f"Exact label-free {split_name} identity derived from the frozen "
            "speech-native train binding; Stage-2 bounded discovery only."
        ),
        "items": receipt_items,
        "probe": "speech-native-runtime-view",
        "seed": runtime_view.get("seed"),
        "source_runtime_view_sha256": runtime_view_sha256,
        "source_split_identity_hash": runtime_view.get("split_identity_hash"),
        "split_identity_hash": hashlib.sha256(
            "\n".join(sorted(keys)).encode("utf-8")
        ).hexdigest(),
        "split_role": "discovery",
    }


def _verification_int(entry: Mapping[str, object], field: str) -> int | None:
    verification = entry.get("verification")
    if isinstance(verification, Mapping):
        value = verification.get(field)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _require_lock_count(entry: Mapping[str, object], field: str, actual: int, label: str) -> None:
    expected = _verification_int(entry, field)
    if expected is not None and expected != actual:
        raise IdentityError(
            f"{label}: layer count {actual} disagrees with the umbrella lock's "
            f"verification.{field}={expected}"
        )


def _license_facts(entry: Mapping[str, object]) -> dict[str, object]:
    facts: dict[str, object] = {}
    for field in ("license", "lifecycle", "profiles", "claim_limit"):
        if field in entry:
            facts[field] = entry[field]
    return facts


def build_d1(lock_path: Path, data_root: Path, *, repo_root: Path | None = None) -> dict[str, object]:
    """``repo_root`` is threaded to :func:`speech_aware_evidence_acquisition.
    data.identity.audio2tool_layers` (default: this study checkout, where the
    committed frozen probe-sample receipt lives) -- a synthetic test world
    passes its own receipt tree here; production callers never pass it."""

    lock = load_lock(lock_path)

    e21 = earnings21_layers(asset_dir(lock, "earnings21-original", data_root))
    e22 = earnings22_layers(asset_dir(lock, "earnings22-original", data_root))
    conec = conec_layers(asset_dir(lock, "conec", data_root))
    slurp = slurp_layers(lock, data_root)
    audio2tool = audio2tool_layers(lock, data_root, repo_root=repo_root)

    e21_identity: Layer = e21["media"]
    for layer in e21.values():
        require_equal(e21_identity, layer)

    e22_identity: Layer = e22["media"]
    for name in ("file_metadata", "nlp_references", "force_aligned_nlp_references"):
        require_equal(e22_identity, e22[name])
    require_subset(e22["subset10_media"], e22_identity)
    if len(e22["subset10_media"].ids) != 10:
        raise IdentityError(
            "earnings22 subset10 must resolve exactly 10 calls, got "
            f"{len(e22['subset10_media'].ids)} (dangling symlinks are not layer files)"
        )

    for layer in conec.values():
        require_equal(e21_identity, layer)

    e21_entry = lock_entry(lock, "earnings21-original")
    e22_entry = lock_entry(lock, "earnings22-original")
    conec_entry = lock_entry(lock, "conec")
    slurp_entry = lock_entry(lock, "slurp")
    audio2tool_entry = lock_entry(lock, "audio2tool")
    _require_lock_count(e21_entry, "main_audio_files", len(e21["media"].ids), "earnings21")
    _require_lock_count(e21_entry, "metadata_rows", len(e21["file_metadata"].ids), "earnings21")
    _require_lock_count(e22_entry, "main_audio_files", len(e22["media"].ids), "earnings22")
    _require_lock_count(e22_entry, "metadata_rows", len(e22["file_metadata"].ids), "earnings22")

    return {
        "artifact_kind": "saea-e0-d1-identity-v1",
        "generated": today(),
        "identity_authority": {
            "lock_relpath_from_study_root": "../../docs/datasets.lock.json",
            "lock_sha256_at_generation": sha256_file(lock_path),
            "note": (
                "The umbrella lock is the only live identity source; this receipt "
                "records observations, it does not fork identity."
            ),
        },
        "carriers": {
            "earnings21-original": {
                "canonical_identity": "media",
                "sample_count": len(e21_identity.ids),
                "identity_ids_sha256": e21_identity.ids_sha256(),
                "layers": layer_report(e21),
                "cross_layer_relations": relations_report(
                    [(e21["media"], e21[name]) for name in e21 if name != "media"]
                ),
                "license_facts": _license_facts(e21_entry),
            },
            "earnings22-original": {
                "canonical_identity": "media",
                "sample_count": len(e22_identity.ids),
                "identity_ids_sha256": e22_identity.ids_sha256(),
                "layers": layer_report(e22),
                "cross_layer_relations": relations_report(
                    [(e22["media"], e22[name]) for name in e22 if name != "media"]
                ),
                "license_facts": _license_facts(e22_entry),
            },
            "conec": {
                "canonical_identity": "earnings21-original media",
                "sample_count": len(e21_identity.ids),
                "layers": layer_report(conec),
                "cross_layer_relations": relations_report(
                    [(e21_identity, layer) for layer in conec.values()]
                ),
                "license_facts": _license_facts(conec_entry),
                "earnings22_side_note": (
                    "ConEC's Earnings22 side (contexts/pdfs and transcripts) has no "
                    "per-sample identity contract yet; it is frozen at R0 when first "
                    "consumed by a registered experiment."
                ),
            },
            "slurp": {
                "canonical_identity": "media",
                "sample_count": len(slurp["media"].ids),
                "identity_ids_sha256": slurp["media"].ids_sha256(),
                "layers": layer_report(slurp),
                "cross_layer_relations": [],
                "license_facts": _license_facts(slurp_entry),
                "scope_note": (
                    "Bounded discovery-probe carrier (2026-08-15 owner amendment): "
                    "MEDIA identity only, covering the devel split in full (every "
                    "governed recording). test is HELD OUT and train/train_synthetic "
                    "are roster-construction-only (data.slurp split discipline); "
                    "neither is addressable by a flight today, so D1 does not close "
                    "over them. SLURP's own governed-metadata reconciliation receipt "
                    "(datasets/slurp/annotation-receipt.json) already verified every "
                    "recordings[] reference against the flac tree; this layer adds "
                    "the fresh on-disk byte re-hash that receipt does not carry."
                ),
            },
            "audio2tool": {
                "canonical_identity": "media",
                "sample_count": len(audio2tool["media"].ids),
                "identity_ids_sha256": audio2tool["media"].ids_sha256(),
                "layers": layer_report(audio2tool),
                "cross_layer_relations": [],
                "license_facts": _license_facts(audio2tool_entry),
                "scope_note": (
                    "Bounded discovery-probe carrier (2026-08-15 owner amendment): "
                    "MEDIA identity only, covering exactly the frozen 400-item "
                    "discovery-split probe-sample receipt "
                    "(docs/receipts/probe-samples/r1-audio2tool-sample.json, "
                    "split_role=discovery) -- the sample universe IS that receipt "
                    "(data.audio2tool module docstring); no other Audio2Tool sample "
                    "is addressable by any run."
                ),
            },
        },
        "invariants": [
            "earnings21: media == file_metadata == nlp_references == wer_tags == normalizations",
            "earnings22: media == file_metadata == nlp_references == force_aligned_nlp_references",
            "earnings22: subset10_media is a subset of media",
            "conec(e21): contexts == nlp_references == timestamps == wer_tags == earnings21 media",
            "layer counts agree with the umbrella lock verification block",
            "slurp: media layer covers every devel-split recording, freshly re-hashed on disk "
            "(bounded discovery-probe carrier; single-layer media identity only)",
            "audio2tool: media layer covers exactly the frozen 400-item discovery-split "
            "probe-sample receipt, freshly re-hashed on disk (bounded discovery-probe carrier; "
            "single-layer media identity only)",
        ],
        "redistribution_note": (
            "Carrier bytes stay under SPEECHRL_DATA_DIR and are never committed; this "
            "receipt holds only IDs, counts and SHA-256 digests."
        ),
        "core_carrier_lock_keys": list(CORE_CARRIER_LOCK_KEYS),
    }
