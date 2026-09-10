"""Write-once, independently verified receipts for complete score jobs."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .bundle.artifacts import VerifiedBundle

SCHEMA = "saea-complete-score-receipt-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")


class ScoreReceiptError(RuntimeError):
    """A score result is incomplete or no longer matches its scored source."""


@dataclass(frozen=True)
class SavedScoreReceiptRef:
    """Hash-pinned reference to one delivery cell's saved score receipt."""

    cell_id: str
    path: Path
    sha256: str


@dataclass(frozen=True)
class ScoreSourceSnapshot:
    """Exact source identity captured before a score process starts."""

    manifest: Mapping[str, str]
    outputs: Mapping[str, str]
    identity: Mapping[str, object]
    scorers: tuple[str, ...]
    roster: frozenset[str]


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _hash_file(path: Path, label: str) -> str:
    try:
        return _sha256_bytes(Path(path).read_bytes())
    except OSError as error:
        raise ScoreReceiptError(f"cannot read {label} at {path}: {error}") from error


def _canonical_hash(value: object) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return _sha256_bytes(raw)


def _artifact(path: Path, label: str) -> dict[str, str]:
    path = Path(path).resolve()
    if not path.is_file():
        raise ScoreReceiptError(f"{label} does not exist: {path}")
    return {"path": str(path), "sha256": _hash_file(path, label)}


def _source_identity(bundle: VerifiedBundle) -> dict[str, object]:
    manifest = bundle.manifest
    declaration = manifest.get("declaration")
    cell_id = declaration.get("cell_id") if isinstance(declaration, Mapping) else None
    if cell_id is not None and (not isinstance(cell_id, str) or not cell_id):
        raise ScoreReceiptError("score source has an invalid delivery cell identity")
    parent = manifest.get("parent")
    if parent is not None:
        if (
            not isinstance(parent, Mapping)
            or set(parent) != {"path", "sha256"}
            or not isinstance(parent.get("path"), str)
            or not isinstance(parent.get("sha256"), str)
            or _SHA256.fullmatch(parent["sha256"]) is None
        ):
            raise ScoreReceiptError("score source has an invalid parent identity")
        parent = dict(parent)
    config = manifest.get("config")
    split = manifest.get("split")
    if not isinstance(config, Mapping) or _SHA256.fullmatch(
        str(config.get("config_hash", ""))
    ) is None:
        raise ScoreReceiptError("score source has an invalid config identity")
    if not isinstance(split, Mapping) or _SHA256.fullmatch(
        str(split.get("identity_hash", ""))
    ) is None:
        raise ScoreReceiptError("score source has an invalid split identity")
    roster = sorted(bundle.split_ids)
    if (
        not roster
        or not all(isinstance(sample_id, str) and sample_id for sample_id in roster)
        or split.get("count") != len(roster)
        or set(split.get("ids", ())) != set(roster)
    ):
        raise ScoreReceiptError("score source split does not match its verified roster")
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise ScoreReceiptError("score source has no run identity")
    return {
        "run_id": run_id,
        "cell_id": cell_id,
        "parent": parent,
        "config_hash": config["config_hash"],
        "split_identity_hash": split["identity_hash"],
        "split_count": len(roster),
        "split_ids_sha256": _canonical_hash(roster),
    }


def capture_score_source(bundle: VerifiedBundle) -> ScoreSourceSnapshot:
    """Capture manifest/output bytes and verified scientific identities."""

    if not isinstance(bundle, VerifiedBundle):
        raise ScoreReceiptError("score source must be a VerifiedBundle")
    if bundle.outputs_path is None:
        raise ScoreReceiptError("score source has no outputs artifact")
    scorers = bundle.manifest.get("scorers")
    if (
        not isinstance(scorers, list)
        or not scorers
        or not all(isinstance(name, str) and name for name in scorers)
        or len(set(scorers)) != len(scorers)
    ):
        raise ScoreReceiptError("score source has invalid configured scorers")
    return ScoreSourceSnapshot(
        manifest=_artifact(bundle.manifest_path, "score source manifest"),
        outputs=_artifact(bundle.outputs_path, "score source outputs"),
        identity=_source_identity(bundle),
        scorers=tuple(scorers),
        roster=frozenset(bundle.split_ids),
    )


def _validate_scores(
    payload: object, *, source: ScoreSourceSnapshot, manifest_path: Path
) -> Mapping[str, object]:
    if not isinstance(payload, Mapping) or set(payload) != {
        "manifest", "verified", "scores"
    }:
        raise ScoreReceiptError("score result must contain exact verified score fields")
    if payload.get("verified") is not True:
        raise ScoreReceiptError("score result is not verified")
    named_manifest = payload.get("manifest")
    if (
        not isinstance(named_manifest, str)
        or Path(named_manifest).resolve() != Path(manifest_path).resolve()
    ):
        raise ScoreReceiptError("score result manifest identity mismatch")
    scores = payload.get("scores")
    if not isinstance(scores, Mapping) or set(scores) != set(source.scorers):
        raise ScoreReceiptError("score result does not match configured scorers")
    for name in source.scorers:
        result = scores[name]
        if (
            not isinstance(result, Mapping)
            or not isinstance(result.get("aggregate"), Mapping)
            or not isinstance(result.get("per_sample"), list)
        ):
            raise ScoreReceiptError(
                f"scorer {name!r} lacks aggregate and per_sample results"
            )
        if name == "cost":
            # Match reused_delivery_scores: cost has no sample-roster
            # requirement, but retains the common aggregate/list shape.
            continue
        rows = result["per_sample"]
        if len(rows) != len(source.roster) or not all(
            isinstance(row, Mapping) for row in rows
        ):
            raise ScoreReceiptError(
                f"scorer {name!r} per_sample rows do not cover the complete roster exactly once"
            )
        ids = [row.get("sample_id") for row in rows]
        if set(ids) != source.roster:
            raise ScoreReceiptError(
                f"scorer {name!r} per_sample rows do not cover the complete roster exactly once"
            )
    return payload


def _expected_document(
    *, job_id: str, result_path: Path, source: ScoreSourceSnapshot,
    verified_bundle: VerifiedBundle,
) -> dict[str, object]:
    if not isinstance(job_id, str) or not job_id:
        raise ScoreReceiptError("score receipt job_id must be non-empty")
    after = capture_score_source(verified_bundle)
    if after != source:
        if after.manifest != source.manifest:
            raise ScoreReceiptError("score source manifest hash mismatch after scoring")
        if after.outputs != source.outputs:
            raise ScoreReceiptError("score source outputs hash mismatch after scoring")
        raise ScoreReceiptError("score source identity changed after scoring")
    result_path = Path(result_path).resolve()
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ScoreReceiptError(f"cannot read complete score result: {error}") from error
    _validate_scores(payload, source=source, manifest_path=verified_bundle.manifest_path)
    return {
        "schema": SCHEMA,
        "status": "complete",
        "job_id": job_id,
        "operation": "score",
        "include_per_sample": True,
        "manifest": dict(source.manifest),
        "outputs": dict(source.outputs),
        "identity": dict(source.identity),
        "scorers": list(source.scorers),
        "score_result": _artifact(result_path, "score result"),
    }


def write_complete_score_receipt(
    path: Path, *, job_id: str, result_path: Path,
    source: ScoreSourceSnapshot, verified_bundle: VerifiedBundle,
) -> SavedScoreReceiptRef:
    """Write a complete receipt once, after rechecking source and score rows."""

    path = Path(path).resolve()
    result_path = Path(result_path).resolve()
    if result_path.parent != path.parent:
        raise ScoreReceiptError("score result and receipt must share an output directory")
    document = _expected_document(
        job_id=job_id, result_path=result_path, source=source,
        verified_bundle=verified_bundle,
    )
    raw = (
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    try:
        with path.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as error:
        raise ScoreReceiptError(f"cannot publish complete score receipt {path}: {error}") from error
    cell_id = source.identity.get("cell_id")
    return SavedScoreReceiptRef(
        cell_id=cell_id if isinstance(cell_id, str) else job_id,
        path=path,
        sha256=_sha256_bytes(raw),
    )


def load_complete_score_receipt(
    reference: SavedScoreReceiptRef,
) -> Mapping[str, object]:
    """Load and hash-check the exact receipt without touching its score source."""

    if (
        not isinstance(reference, SavedScoreReceiptRef)
        or not isinstance(reference.cell_id, str)
        or not reference.cell_id
        or not isinstance(reference.sha256, str)
        or _SHA256.fullmatch(reference.sha256) is None
    ):
        raise ScoreReceiptError("saved score receipt reference is invalid")
    path = Path(reference.path).resolve()
    try:
        raw = path.read_bytes()
        document = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ScoreReceiptError(f"cannot read saved score receipt {path}: {error}") from error
    if _sha256_bytes(raw) != reference.sha256:
        raise ScoreReceiptError("saved score receipt hash mismatch")
    expected_keys = {
        "schema", "status", "job_id", "operation", "include_per_sample",
        "manifest", "outputs", "identity", "scorers", "score_result",
    }
    if not isinstance(document, Mapping) or set(document) != expected_keys:
        raise ScoreReceiptError("saved score receipt has missing or unknown fields")
    if (
        document.get("schema") != SCHEMA
        or document.get("status") != "complete"
        or document.get("operation") != "score"
        or document.get("include_per_sample") is not True
    ):
        raise ScoreReceiptError("saved score receipt is not a complete score operation")
    return document


def verify_complete_score_receipt(
    reference: SavedScoreReceiptRef, bundle: VerifiedBundle,
) -> Mapping[str, object]:
    """Verify saved bytes and full score coverage without invoking a scorer or gate."""

    document = load_complete_score_receipt(reference)
    path = Path(reference.path).resolve()
    current = capture_score_source(bundle)
    if document["manifest"] != current.manifest:
        raise ScoreReceiptError("saved score receipt manifest hash mismatch")
    if document["outputs"] != current.outputs:
        raise ScoreReceiptError("saved score receipt outputs hash mismatch")
    if document["identity"] != current.identity or document["scorers"] != list(current.scorers):
        raise ScoreReceiptError("saved score receipt source identity mismatch")
    expected_cell = current.identity.get("cell_id")
    if reference.cell_id != (expected_cell if isinstance(expected_cell, str) else document["job_id"]):
        raise ScoreReceiptError("saved score receipt cell identity mismatch")
    result_meta = document["score_result"]
    if (
        not isinstance(result_meta, Mapping)
        or set(result_meta) != {"path", "sha256"}
        or Path(str(result_meta.get("path"))).resolve().parent != path.parent
    ):
        raise ScoreReceiptError("saved score receipt result path is invalid")
    result_path = Path(result_meta["path"]).resolve()
    if _hash_file(result_path, "score result") != result_meta.get("sha256"):
        raise ScoreReceiptError("score result hash mismatch")
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ScoreReceiptError(f"cannot parse score result: {error}") from error
    _validate_scores(payload, source=current, manifest_path=bundle.manifest_path)
    return document


__all__ = [
    "SCHEMA",
    "SavedScoreReceiptRef",
    "ScoreReceiptError",
    "ScoreSourceSnapshot",
    "capture_score_source",
    "load_complete_score_receipt",
    "verify_complete_score_receipt",
    "write_complete_score_receipt",
]
