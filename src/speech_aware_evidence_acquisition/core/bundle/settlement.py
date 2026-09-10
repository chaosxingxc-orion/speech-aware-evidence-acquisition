"""Settle one raw phase attempt from verified, already-scored derivatives."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..attempts import (
    AttemptError, AttemptHandle, STATE_FINALIZED, STATE_OPENED,
)
from ..scoring_receipt import (
    SavedScoreReceiptRef,
    ScoreReceiptError,
    load_complete_score_receipt,
    verify_complete_score_receipt,
)
from . import RUN_MANIFEST_SCHEMA, STATUS_COMPLETED, BundleError
from .artifacts import VerifiedBundle
from .delivery import (
    DELIVERY_MANIFEST_SCHEMA,
    recorded_phase_delivery_declarations,
)
from .delivery_replay import canonical, sha256
from .verify import verify_bundle

SCHEMA = "saea-phase-delivery-settlement-v1"


@dataclass(frozen=True)
class PhaseDeliverySettlementResult:
    receipt_path: Path
    receipt_sha256: str
    attempt_state: str
    reused: bool


def _meta(path: Path) -> dict[str, str]:
    path = Path(path).resolve()
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise BundleError(f"cannot read settlement input {path}: {error}") from error
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}


def _data_root(parent: VerifiedBundle) -> Path:
    attempt = parent.manifest.get("attempt")
    if not isinstance(attempt, Mapping) or not isinstance(
        attempt.get("state_path"), str
    ):
        raise BundleError("phase delivery parent lacks an attempt state path")
    state_path = Path(attempt["state_path"]).resolve()
    try:
        if state_path.parent.parent.name != "attempts":
            raise BundleError("phase delivery attempt is outside the data attempts tree")
        data_root = state_path.parent.parent.parent
        expected = (
            data_root / "attempts" / str(attempt.get("run_id"))
            / f"{attempt.get('attempt_id')}.json"
        ).resolve()
        if state_path != expected:
            raise BundleError("phase delivery attempt path differs from its run identity")
        return data_root
    except IndexError as error:
        raise BundleError("phase delivery attempt path is malformed") from error


def _required_declarations(
    parent: VerifiedBundle, repo_root: Path,
) -> tuple[Mapping, ...]:
    marker = parent.manifest.get("required_phase_deliveries")
    if not isinstance(marker, list) or not marker or not all(
        isinstance(item, Mapping) for item in marker
    ):
        raise BundleError("phase delivery settlement requires full declared delivery marker")
    recorded = recorded_phase_delivery_declarations(parent, repo_root)
    if canonical(marker) != canonical(recorded):
        raise BundleError(
            "phase delivery marker differs from the exact recorded experiment declarations"
        )
    return tuple(recorded)


def _receipt_refs_from_document(document: Mapping) -> tuple[SavedScoreReceiptRef, ...]:
    deliveries = document.get("deliveries")
    if not isinstance(deliveries, list):
        raise BundleError("phase delivery settlement lacks deliveries")
    refs = []
    for delivery in deliveries:
        if not isinstance(delivery, Mapping):
            raise BundleError("phase delivery settlement entry must be a mapping")
        receipt = delivery.get("score_receipt")
        if (
            not isinstance(receipt, Mapping)
            or set(receipt) != {"path", "sha256"}
        ):
            raise BundleError("phase delivery settlement lacks a score receipt binding")
        refs.append(SavedScoreReceiptRef(
            cell_id=delivery.get("cell_id"),
            path=Path(receipt.get("path", "")),
            sha256=receipt.get("sha256"),
        ))
    return tuple(refs)


def _expected(
    parent: VerifiedBundle,
    *,
    repo_root: Path,
    score_receipts: Sequence[SavedScoreReceiptRef],
) -> dict[str, object]:
    if (
        parent.manifest.get("schema") != RUN_MANIFEST_SCHEMA
        or parent.manifest.get("status") != STATUS_COMPLETED
    ):
        raise BundleError("phase delivery settlement requires an ordinary completed parent")
    declarations = _required_declarations(parent, repo_root)
    expected_by_cell = {item["cell_id"]: item for item in declarations}
    if len(expected_by_cell) != len(declarations):
        raise BundleError("phase delivery declarations repeat a cell identity")
    refs_by_cell: dict[str, SavedScoreReceiptRef] = {}
    seen_paths: set[Path] = set()
    for reference in score_receipts:
        if not isinstance(reference, SavedScoreReceiptRef):
            raise BundleError("phase delivery score evidence must be a saved receipt reference")
        if reference.cell_id in refs_by_cell:
            raise BundleError("phase delivery score evidence repeats a cell identity")
        path = Path(reference.path).resolve()
        if path in seen_paths:
            raise BundleError("phase delivery score evidence repeats a receipt path")
        refs_by_cell[reference.cell_id] = reference
        seen_paths.add(path)
    if set(refs_by_cell) != set(expected_by_cell):
        raise BundleError(
            "phase delivery score evidence does not exactly cover required cells"
        )

    parent_meta = _meta(parent.manifest_path)
    deliveries = []
    for declaration in declarations:
        cell_id = declaration["cell_id"]
        reference = refs_by_cell[cell_id]
        score_document = load_complete_score_receipt(reference)
        manifest_meta = score_document.get("manifest")
        if not isinstance(manifest_meta, Mapping) or not isinstance(
            manifest_meta.get("path"), str
        ):
            raise BundleError("complete score receipt lacks derivative manifest identity")
        derivative = verify_bundle(Path(manifest_meta["path"]))
        if derivative.manifest.get("schema") != DELIVERY_MANIFEST_SCHEMA:
            raise BundleError("phase delivery score receipt names a non-derivative bundle")
        if derivative.manifest.get("parent") != parent_meta:
            raise BundleError("phase delivery derivative belongs to a foreign parent")
        if canonical(derivative.manifest.get("declaration")) != canonical(declaration):
            raise BundleError("phase delivery derivative declaration differs from required cell")
        verified_score = verify_complete_score_receipt(reference, derivative)
        identity = verified_score["identity"]
        if not isinstance(identity, Mapping) or identity.get("cell_id") != cell_id:
            raise BundleError("complete score receipt cell identity mismatch")
        cost = derivative.manifest.get("cost")
        if (
            not isinstance(cost, Mapping)
            or cost.get("calls_used") != 0
            or cost.get("additional_model_contacts") != 0
        ):
            raise BundleError("phase delivery derivative must add zero model contacts")
        deliveries.append({
            "cell_id": cell_id,
            "declaration": dict(declaration),
            "declaration_sha256": sha256(canonical(declaration)),
            "derivative_manifest": _meta(derivative.manifest_path),
            "derived_outputs": _meta(derivative.outputs_path),
            "score_receipt": _meta(reference.path),
            "score_result": dict(verified_score["score_result"]),
            "cost": dict(cost),
        })

    attempt = parent.manifest["attempt"]
    parent_cost = parent.manifest.get("cost")
    if not isinstance(parent_cost, Mapping):
        raise BundleError("phase delivery parent lacks generation cost")
    return {
        "schema": SCHEMA,
        "status": "complete",
        "parent": {
            "run_id": parent.manifest["run_id"],
            "attempt_id": attempt["attempt_id"],
            "manifest": parent_meta,
            "cost": dict(parent_cost),
            "cost_attribution": "parent generation is charged once",
        },
        "required_phase_deliveries": [dict(item) for item in declarations],
        "deliveries": deliveries,
    }


def _publish_once(path: Path, raw: bytes) -> bool:
    lock_path = path.with_name(path.name + ".producer.lock")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise BundleError("phase delivery settlement publisher is busy") from error
        if path.exists():
            if path.read_bytes() != raw:
                raise BundleError("existing phase delivery settlement differs")
            return True
        file_descriptor, temporary = tempfile.mkstemp(
            prefix=".phase-settlement-", dir=path.parent
        )
        try:
            with os.fdopen(file_descriptor, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                if path.read_bytes() != raw:
                    raise BundleError("concurrent phase delivery settlement differs") from None
                return True
        finally:
            os.unlink(temporary)
        return False
    except OSError as error:
        raise BundleError(f"cannot publish phase delivery settlement: {error}") from error
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def verify_phase_delivery_settlement(
    settlement_path: Path, *, repo_root: Path,
) -> Mapping[str, object]:
    """Recompute every dependency of a saved settlement without scoring."""

    path = Path(settlement_path).resolve()
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BundleError(f"cannot read phase delivery settlement: {error}") from error
    if not isinstance(document, Mapping) or set(document) != {
        "schema", "status", "parent", "required_phase_deliveries", "deliveries"
    }:
        raise BundleError("phase delivery settlement has missing or unknown fields")
    parent_meta = document.get("parent")
    manifest_meta = parent_meta.get("manifest") if isinstance(parent_meta, Mapping) else None
    if not isinstance(manifest_meta, Mapping) or not isinstance(
        manifest_meta.get("path"), str
    ):
        raise BundleError("phase delivery settlement lacks parent manifest identity")
    parent = verify_bundle(Path(manifest_meta["path"]))
    try:
        expected = _expected(
            parent,
            repo_root=Path(repo_root),
            score_receipts=_receipt_refs_from_document(document),
        )
    except ScoreReceiptError as error:
        raise BundleError(f"phase delivery score receipt refused: {error}") from error
    if dict(document) != expected:
        raise BundleError("phase delivery settlement differs from deterministic verification")
    attempt = parent.manifest["attempt"]
    handle = AttemptHandle(
        path=Path(attempt["state_path"]),
        run_id=attempt["run_id"],
        attempt_id=attempt["attempt_id"],
    )
    try:
        state = handle.state()
    except AttemptError as error:
        raise BundleError(f"cannot verify settlement attempt state: {error}") from error
    if state == STATE_FINALIZED:
        try:
            attempt_document = json.loads(handle.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise BundleError(f"cannot verify finalization binding: {error}") from error
        binding = {
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "kind": SCHEMA,
        }
        if attempt_document.get("finalization") != binding:
            raise BundleError("finalized attempt does not bind this settlement receipt")
    elif state != STATE_OPENED:
        raise BundleError("saved settlement belongs to a non-open terminal attempt")
    return document


def settle_phase_delivery_attempt(
    parent_manifest: Path,
    *,
    repo_root: Path,
    score_receipts: Sequence[SavedScoreReceiptRef],
    settlement_path: Path,
) -> PhaseDeliverySettlementResult:
    """Publish complete derivative evidence, then finalize the raw attempt."""

    parent = verify_bundle(Path(parent_manifest))
    repo_root = Path(repo_root).resolve()
    settlement_path = Path(settlement_path).resolve()
    data_root = _data_root(parent)
    if not settlement_path.is_relative_to(data_root):
        raise BundleError("phase delivery settlement must remain inside the data root")
    if settlement_path == repo_root or settlement_path.is_relative_to(repo_root):
        raise BundleError("phase delivery settlement must remain outside the repository")
    settlement_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        document = _expected(
            parent, repo_root=repo_root, score_receipts=tuple(score_receipts)
        )
    except ScoreReceiptError as error:
        raise BundleError(f"phase delivery score receipt refused: {error}") from error
    raw = canonical(document) + b"\n"
    receipt_sha256 = hashlib.sha256(raw).hexdigest()
    attempt = parent.manifest["attempt"]
    handle = AttemptHandle(
        path=Path(attempt["state_path"]),
        run_id=attempt["run_id"],
        attempt_id=attempt["attempt_id"],
    )
    try:
        state = handle.state()
    except AttemptError as error:
        raise BundleError(f"cannot read phase delivery attempt state: {error}") from error
    if state not in {STATE_OPENED, STATE_FINALIZED}:
        raise BundleError(
            f"phase delivery attempt is {state!r}, not OPENED or an exact FINALIZED retry"
        )
    if state == STATE_FINALIZED and not settlement_path.is_file():
        raise BundleError("finalized phase delivery attempt lacks its settlement receipt")
    reused = _publish_once(settlement_path, raw)

    # Re-read every source after publication. A crash here leaves an exact
    # retryable receipt and the attempt OPENED.
    verify_phase_delivery_settlement(settlement_path, repo_root=repo_root)
    try:
        handle.finalize_with_receipt(
            str(settlement_path), receipt_sha256, SCHEMA
        )
    except AttemptError as error:
        raise BundleError(f"phase delivery settlement cannot finalize attempt: {error}") from error
    return PhaseDeliverySettlementResult(
        receipt_path=settlement_path,
        receipt_sha256=receipt_sha256,
        attempt_state="FINALIZED",
        reused=reused,
    )


__all__ = [
    "PhaseDeliverySettlementResult",
    "SCHEMA",
    "settle_phase_delivery_attempt",
    "verify_phase_delivery_settlement",
]
