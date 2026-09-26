"""Verify TRAIN memory provenance offline; expose compact attestations at runtime.

The root-approved admission pins this attestation independently of memory bytes.
It proves source correspondence, not scientific quality. Runtime validation never
opens reward artifacts, archived answers, traces, score files or references.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from ..core.preparation import (
    PreparationError, hash_stable_file, load_artifact, prepare_artifact,
)
from .experience_memory import ExperienceMemoryCatalog, ExperienceMemoryError, SourceRef, _sha
from .hashing import content_hash

SOURCE_VERIFICATION_SCHEMA = "saea-experience-source-verification-v1"
SOURCE_VERIFICATION_KIND = "experience-memory-sources"
_PROOF_KEYS = frozenset({
    "schema", "status", "manifest_sha256", "construction_roster_sha256",
    "verifier_sha256", "reward_sources", "records",
})
_SOURCE_PIN_KEYS = frozenset({
    "artifact_sha256", "config_sha256", "manifest_sha256",
    "complete_score_receipt_sha256", "construction_roster_sha256",
})
_RECORD_KEYS = frozenset({
    "record_sha256", "source", "primary_link_sha256",
    "supporting_link_sha256s", "contradicting_link_sha256s",
})


class MemorySourceVerificationError(ValueError):
    """A memory record lacks the required authoritative TRAIN correspondence."""


def reward_link_source_ref(link) -> SourceRef:
    """Name a link canonically; this helper alone does not verify its authority."""
    link.validate()
    return reward_link_hash_source_ref(link.link_sha256)


def _sha_value(value, field):
    try:
        return _sha(value, field)
    except ExperienceMemoryError as error:
        raise MemorySourceVerificationError(str(error)) from error


def reward_link_hash_source_ref(link_sha256: str) -> SourceRef:
    """Name a source-verified link hash; naming alone grants no authority."""
    canonical = _sha_value(link_sha256, "reward-link SHA-256")
    return SourceRef("reward-link:" + canonical, canonical, "train")


def _record_row(record, primary):
    references = record.supporting_source_refs + record.contradicting_source_refs
    for ref in references:
        if ref != reward_link_hash_source_ref(ref.sha256):
            raise MemorySourceVerificationError("memory source reference is not canonical")
    return {
        "record_sha256": record.record_sha256,
        "source": record.source.as_json(),
        "primary_link_sha256": _sha_value(primary, "primary reward-link hash"),
        "supporting_link_sha256s": [ref.sha256 for ref in record.supporting_source_refs],
        "contradicting_link_sha256s": [
            ref.sha256 for ref in record.contradicting_source_refs
        ],
    }


def _proof_inputs(proof):
    return {
        key: proof[key] for key in (
            "manifest_sha256", "construction_roster_sha256",
            "verifier_sha256", "reward_sources",
        )
    }


def _validate_proof(catalog, proof):
    if not isinstance(proof, Mapping) or set(proof) != _PROOF_KEYS:
        raise MemorySourceVerificationError("source verification has wrong fields")
    if proof["schema"] != SOURCE_VERIFICATION_SCHEMA or proof["status"] != "source-verified":
        raise MemorySourceVerificationError("source verification schema or status differs")
    if (
        proof["manifest_sha256"] != catalog.manifest_sha256
        or proof["construction_roster_sha256"] != catalog.train_construction_sha256
    ):
        raise MemorySourceVerificationError("source verification memory identity mismatch")
    _sha_value(proof["verifier_sha256"], "verifier source hash")
    sources = proof["reward_sources"]
    if not isinstance(sources, list) or not sources:
        raise MemorySourceVerificationError("source verification requires reward source pins")
    seen = set()
    for pin in sources:
        if not isinstance(pin, Mapping) or set(pin) != _SOURCE_PIN_KEYS:
            raise MemorySourceVerificationError("reward source pin has wrong fields")
        for key, value in pin.items():
            _sha_value(value, key)
        if pin["construction_roster_sha256"] != catalog.train_construction_sha256:
            raise MemorySourceVerificationError("reward source construction identity mismatch")
        identity = (pin["artifact_sha256"], pin["config_sha256"])
        if identity in seen:
            raise MemorySourceVerificationError("duplicate reward source binding")
        seen.add(identity)
    rows = proof["records"]
    if not isinstance(rows, list) or len(rows) != len(catalog.records):
        raise MemorySourceVerificationError("source verification record count mismatch")
    for record, row in zip(catalog.records, rows, strict=True):
        if not isinstance(row, Mapping) or set(row) != _RECORD_KEYS:
            raise MemorySourceVerificationError("source verification record has wrong fields")
        if row != _record_row(record, row["primary_link_sha256"]):
            raise MemorySourceVerificationError("source verification record correspondence mismatch")
    return dict(proof)


def verify_experience_memory_sources(
    catalog: ExperienceMemoryCatalog, reward_source_bindings: Sequence[Mapping],
) -> dict:
    """Rebuild every bound reward source OFFLINE before admitting correspondence."""
    # Import only on this offline path. The answering-runtime reader below does not
    # import or call the reward reader, bundle verifier or scorer.
    from .reward_link_io import read_verified_reward_link_artifact

    catalog.validate()
    if (
        isinstance(reward_source_bindings, (str, bytes))
        or not isinstance(reward_source_bindings, Sequence)
        or not reward_source_bindings
    ):
        raise MemorySourceVerificationError("nonempty reward source bindings are required")
    by_hash, by_source, pins = {}, {}, []
    for binding in reward_source_bindings:
        if not isinstance(binding, Mapping) or set(binding) != {"config", "artifact"}:
            raise MemorySourceVerificationError("reward source binding has wrong fields")
        config, artifact = binding["config"], binding["artifact"]
        if not isinstance(artifact, Mapping) or set(artifact) != {"path", "sha256"}:
            raise MemorySourceVerificationError("reward artifact pin has wrong fields")
        if not isinstance(artifact["path"], str) or not Path(artifact["path"]).is_absolute():
            raise MemorySourceVerificationError("reward artifact path must be absolute")
        expected = _sha_value(artifact["sha256"], "reward artifact hash")
        try:
            _, actual, fingerprint = hash_stable_file(Path(artifact["path"]), "reward artifact")
            if actual != expected:
                raise MemorySourceVerificationError("reward artifact hash mismatch")
            links = read_verified_reward_link_artifact(config, Path(artifact["path"]))
            _, after, after_fingerprint = hash_stable_file(
                Path(artifact["path"]), "reward artifact after verification",
            )
            if after != expected or after_fingerprint != fingerprint:
                raise MemorySourceVerificationError("reward artifact changed during verification")
        except (ValueError, RuntimeError, OSError) as error:
            raise MemorySourceVerificationError(
                f"cannot read authoritative verified reward source: {error}"
            ) from error
        for link in links:
            if link.construction_roster_sha256 != catalog.train_construction_sha256:
                raise MemorySourceVerificationError("reward source construction identity mismatch")
            if (
                link.source.partition_role != "train"
                or link.source.source_sample_id not in catalog.expected_train_sample_ids
            ):
                raise MemorySourceVerificationError("reward source is outside allowed TRAIN membership")
            if link.link_sha256 in by_hash:
                raise MemorySourceVerificationError("duplicate reward link across source bindings")
            if link.source in by_source:
                raise MemorySourceVerificationError("ambiguous primary source across reward bindings")
            by_hash[link.link_sha256] = link
            by_source[link.source] = link.link_sha256
        pins.append({
            "artifact_sha256": expected,
            "config_sha256": content_hash(config),
            "manifest_sha256": config["manifest"]["sha256"],
            "complete_score_receipt_sha256": config["complete_score_receipt"]["sha256"],
            "construction_roster_sha256": config["construction_roster"]["sha256"],
        })
    rows = []
    for record in catalog.records:
        if record.source not in by_source:
            raise MemorySourceVerificationError("memory primary source has no authoritative match")
        row = _record_row(record, by_source[record.source])
        for ref in record.supporting_source_refs + record.contradicting_source_refs:
            if ref.sha256 not in by_hash or ref != reward_link_source_ref(by_hash[ref.sha256]):
                raise MemorySourceVerificationError("memory source reference is outside verified TRAIN links")
        rows.append(row)
    _, verifier_sha, _ = hash_stable_file(Path(__file__), "memory source verifier")
    return _validate_proof(catalog, {
        "schema": SOURCE_VERIFICATION_SCHEMA, "status": "source-verified",
        "manifest_sha256": catalog.manifest_sha256,
        "construction_roster_sha256": catalog.train_construction_sha256,
        "verifier_sha256": verifier_sha, "reward_sources": pins, "records": rows,
    })


def prepare_experience_memory_sources(catalog, reward_source_bindings, output_path):
    """Persist a verified attestation through the existing shared preparation base."""
    # Reverify even when a prepared cache exists; cold and warm offline admission
    # have the same authority. Runtime uses only the frozen compact attestation.
    proof = verify_experience_memory_sources(catalog, reward_source_bindings)
    try:
        return prepare_artifact(
            Path(output_path), kind=SOURCE_VERIFICATION_KIND,
            inputs=_proof_inputs(proof), producer=lambda: proof, contact_class="model-free",
        )
    except PreparationError as error:
        raise MemorySourceVerificationError(str(error)) from error


def load_verified_memory_sources(catalog, path, *, expected_sha256):
    """Check an independently admission-pinned attestation without opening sources."""
    catalog.validate()
    try:
        raw = Path(path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise MemorySourceVerificationError("source verification file hash mismatch")
        wrapper = json.loads(raw)
        if not isinstance(wrapper, Mapping) or wrapper.get("contact_class") != "model-free":
            raise MemorySourceVerificationError("source verification must be model-free")
        proof = _validate_proof(catalog, wrapper.get("output"))
        output = load_artifact(
            Path(path), expected_sha256=expected_sha256, kind=SOURCE_VERIFICATION_KIND,
            inputs=_proof_inputs(proof),
        )
        return _validate_proof(catalog, output)
    except (OSError, UnicodeError, json.JSONDecodeError, PreparationError) as error:
        raise MemorySourceVerificationError(f"cannot load source verification: {error}") from error


def system_group_hash_source_ref(group_sha256: str) -> SourceRef:
    """Reference a verified full-system comparison group, never a legacy reward link."""
    return SourceRef(
        "complete-system-group:" + _sha_value(group_sha256, "system group SHA-256"),
        group_sha256, "train",
    )
