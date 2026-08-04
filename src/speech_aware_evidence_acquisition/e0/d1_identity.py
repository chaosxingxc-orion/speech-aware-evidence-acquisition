"""E0 D1: cross-layer sample/segment identity closure for the three core carriers.

Hard invariants (generation fails closed if any is violated):

- Earnings21: media, file metadata, NLP references, WER tags and normalizations all
  name exactly the same 44 samples (counts cross-checked against the umbrella lock's
  own verification block).
- Earnings22: media, metadata rows, NLP references and force-aligned references all
  name exactly the same 125 samples; the upstream ten-call subset is a subset.
- ConEC (Earnings21 side): contexts, corrected NLP references, timestamps and WER
  tags all name exactly the Earnings21 identity set — every core call has context.

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
    conec_layers,
    earnings21_layers,
    earnings22_layers,
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


def build_d1(lock_path: Path, data_root: Path) -> dict[str, object]:
    lock = load_lock(lock_path)

    e21 = earnings21_layers(asset_dir(lock, "earnings21-original", data_root))
    e22 = earnings22_layers(asset_dir(lock, "earnings22-original", data_root))
    conec = conec_layers(asset_dir(lock, "conec", data_root))

    e21_identity: Layer = e21["media"]
    for layer in e21.values():
        require_equal(e21_identity, layer)

    e22_identity: Layer = e22["media"]
    for name in ("file_metadata", "nlp_references", "force_aligned_nlp_references"):
        require_equal(e22_identity, e22[name])
    require_subset(e22["subset10_media"], e22_identity)

    for layer in conec.values():
        require_equal(e21_identity, layer)

    e21_entry = lock_entry(lock, "earnings21-original")
    e22_entry = lock_entry(lock, "earnings22-original")
    conec_entry = lock_entry(lock, "conec")
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
        },
        "invariants": [
            "earnings21: media == file_metadata == nlp_references == wer_tags == normalizations",
            "earnings22: media == file_metadata == nlp_references == force_aligned_nlp_references",
            "earnings22: subset10_media is a subset of media",
            "conec(e21): contexts == nlp_references == timestamps == wer_tags == earnings21 media",
            "layer counts agree with the umbrella lock verification block",
        ],
        "redistribution_note": (
            "Carrier bytes stay under SPEECHRL_DATA_DIR and are never committed; this "
            "receipt holds only IDs, counts and SHA-256 digests."
        ),
        "core_carrier_lock_keys": list(CORE_CARRIER_LOCK_KEYS),
    }
