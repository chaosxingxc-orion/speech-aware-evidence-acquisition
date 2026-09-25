"""``VerifiedBundle`` and the shared artifact-hash-recompute helpers used by
:func:`speech_aware_evidence_acquisition.core.bundle.verify.verify_bundle`.

Split out of the former monolithic ``core/bundle.py`` (R0 repair refactor
stage 1, pure move, no behaviour change).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from . import BundleError
from ..session.receipt import archived_session_receipt_path


@dataclass(frozen=True)
class VerifiedBundle:
    """The result of a bundle that passed every I7 cross-check. Only this
    type -- never a bare manifest path or dict -- is accepted by
    ``core.scorers.score_bundle``: scoring is structurally impossible without
    first surviving :func:`verify_bundle`."""

    manifest_path: Path
    manifest: Mapping[str, object]
    outputs_path: Path | None
    outputs_rows: tuple[Mapping[str, object], ...]
    trace_records: Mapping[str, Mapping[str, object]]
    split_ids: frozenset
    attempt_state: str


def _read_bytes(path: Path, label: str) -> bytes:
    try:
        return Path(path).read_bytes()
    except OSError as error:
        raise BundleError(f"cannot read {label} at {path}: {error}") from error


def _verify_artifact(meta: object, label: str, *, confine_to: Path | None = None) -> bytes | None:
    """Recompute an artifact's hash from bytes on disk.

    ``confine_to`` (Minor hardening, round-2 external-threat-model review):
    when given, ``meta["path"]`` must resolve strictly inside it -- WITHOUT
    this, a manifest's artifact ``path`` values were absolute and completely
    unconfined at verify time; only ``manifest_path``'s OWN directory was
    ever checked against anything (``_refuse_if_inside_repo``, an EXCLUSION
    from the study repo, not a positive confinement of referenced artifacts).
    A manifest could therefore bind another run's outputs.jsonl -- or any
    other file on the filesystem -- as if it were this run's own, as long as
    the manifest also carried that file's correct hash. Passed by
    :func:`verify_bundle` for ``outputs``/``raw_trace``/``trace_manifest``/
    ``scores`` -- every artifact this module's own ``build_manifest``/
    ``finalize_bundle`` ALWAYS place directly in the manifest's own run
    directory -- but deliberately NOT for ``session_receipt``, whose path is
    supplied by the caller from outside this module (``--session-receipt``)
    and may legitimately name a session file SHARED across many runs/run
    directories (one resident server can serve many attempts), never
    something this module itself writes into a specific run_dir.
    """

    if meta is None:
        return None
    if not isinstance(meta, Mapping) or not isinstance(meta.get("path"), str) or not isinstance(
        meta.get("sha256"), str
    ):
        raise BundleError(f"manifest {label} entry must be a {{path, sha256}} object")
    artifact_path = Path(meta["path"])
    if confine_to is not None:
        try:
            resolved = artifact_path.resolve()
        except OSError as error:
            raise BundleError(f"cannot resolve {label} path {artifact_path}: {error}") from error
        if not resolved.is_relative_to(confine_to):
            raise BundleError(
                f"manifest {label} path {artifact_path} does not resolve under this "
                f"bundle's own run directory {confine_to}; an artifact belonging to a "
                "different run -- or an arbitrary filesystem location -- can never be "
                "bound into this manifest"
            )
        artifact_path = resolved
    try:
        raw = _read_bytes(artifact_path, label)
    except BundleError:
        if label != "session receipt" or confine_to is not None:
            raise
        raw = None
    actual = hashlib.sha256(raw).hexdigest() if raw is not None else None
    if actual == meta["sha256"]:
        return raw
    if label == "session receipt" and confine_to is None:
        # Resident session paths can be replaced at restart. Only this artifact
        # may resolve its original manifest hash from the defined sibling archive.
        try:
            archive = archived_session_receipt_path(artifact_path, meta["sha256"])
        except ValueError as error:
            raise BundleError(f"invalid archived session receipt hash: {error}") from error
        archived = _read_bytes(archive, "archived session receipt")
        if hashlib.sha256(archived).hexdigest() != meta["sha256"]:
            raise BundleError(f"archived session receipt hash mismatch at {archive}")
        return archived
    raise BundleError(
        f"{label} hash mismatch: manifest records {meta['sha256'][:12]}..., actual "
        f"on-disk bytes hash to {actual[:12]}... ({meta['path']})"
    )
