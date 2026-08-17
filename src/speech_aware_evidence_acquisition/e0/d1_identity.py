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

from pathlib import Path
from typing import Mapping

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
