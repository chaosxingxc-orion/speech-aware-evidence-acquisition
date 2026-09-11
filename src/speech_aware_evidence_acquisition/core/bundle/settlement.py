"""Settle a generation attempt from complete saved raw or derivative scores."""

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
from .delivery_replay import canonical, delivery_declarations, sha256
from .verify import verify_bundle

SCHEMA = "saea-phase-delivery-settlement-v1"
DELIVERY_SCHEMA = "saea-delivery-settlement-v1"
SCORED_SCHEMA = "saea-scored-attempt-settlement-v1"


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


def _recorded_legacy_delivery_declarations(
    parent: VerifiedBundle, repo_root: Path, *, require_deliveries: bool = True,
) -> tuple[Mapping, ...]:
    """Recover markerless OBS declarations from the parent's committed source.

    Keep this settlement-only reader outside the replay source files: existing
    immutable derivatives bind those files byte for byte.
    """
    from ..config import _reject_duplicate_keys, fragment_path
    from .git_commit import _git

    fragments = parent.manifest.get("config", {}).get("fragments")
    if not isinstance(fragments, Mapping) or "experiment" not in fragments:
        raise BundleError("markerless delivery requires recorded experiment fragments")
    commit = parent.manifest.get("study_commit")
    if not isinstance(commit, str) or len(commit) != 40 or any(
        c not in "0123456789abcdef" for c in commit
    ):
        raise BundleError("markerless delivery requires a valid recorded study commit")
    path = fragment_path(repo_root, "experiment", fragments["experiment"])
    relative = path.relative_to(repo_root).as_posix()
    code, _, _ = _git(repo_root, "cat-file", "-e", commit + "^{commit}")
    if code:
        raise BundleError("markerless delivery recorded study commit is unavailable")
    code, raw, _ = _git(repo_root, "show", f"{commit}:{relative}")
    if code:
        raise BundleError("markerless delivery recorded experiment is unavailable")
    try:
        values = json.loads(raw, object_pairs_hook=_reject_duplicate_keys(path))
    except (ValueError, TypeError) as error:
        raise BundleError(f"invalid recorded delivery experiment: {error}") from error
    if not isinstance(values, Mapping) or not isinstance(values.get("cells"), list):
        raise BundleError("markerless delivery requires recorded parent cells")
    selected = []
    for declaration in delivery_declarations(values):
        cells = [
            cell for cell in values["cells"]
            if isinstance(cell, Mapping)
            and cell.get("cell_id") == declaration["parent_cell_id"]
        ]
        if len(cells) != 1:
            raise BundleError("delivery requires one unambiguous recorded parent cell")
        cell = cells[0]
        if any(
            cell.get(f"{kind}_fragment") != fragments.get(kind)
            for kind in ("model", "dataset", "baseline")
        ):
            continue
        if cell.get("run_id") not in (None, parent.manifest["run_id"]):
            continue
        if cell.get("attempt_id") not in (
            None, parent.manifest["attempt"]["attempt_id"]
        ):
            continue
        if "source_selector" in declaration:
            raise BundleError("phase delivery settlement requires its original manifest marker")
        selected.append(declaration)
    if not selected and require_deliveries:
        raise BundleError("no legacy deliveries match the recorded parent identity")
    return tuple(selected)


def _required_declarations(
    parent: VerifiedBundle, repo_root: Path,
) -> tuple[Mapping, ...]:
    if "required_phase_deliveries" not in parent.manifest:
        return _recorded_legacy_delivery_declarations(parent, repo_root)
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
    deliveries = (
        [document.get("score")] if document.get("schema") == SCORED_SCHEMA
        else document.get("deliveries")
    )
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


def _expected_scored_parent(
    parent: VerifiedBundle, *, repo_root: Path,
    score_receipts: Sequence[SavedScoreReceiptRef],
) -> dict[str, object]:
    if "required_phase_deliveries" in parent.manifest:
        raise BundleError("raw score cannot replace required phase deliveries")
    if _recorded_legacy_delivery_declarations(
        parent, repo_root, require_deliveries=False,
    ):
        raise BundleError("raw score cannot replace recorded delivery derivatives")
    if len(score_receipts) != 1:
        raise BundleError("raw settlement requires exactly one complete score receipt")
    reference = score_receipts[0]
    score = verify_complete_score_receipt(reference, parent)
    attempt = parent.manifest["attempt"]
    cost = parent.manifest.get("cost")
    if not isinstance(cost, Mapping):
        raise BundleError("raw scored parent lacks generation cost")
    return {
        "schema": SCORED_SCHEMA,
        "status": "complete",
        "parent": {
            "run_id": parent.manifest["run_id"],
            "attempt_id": attempt["attempt_id"],
            "manifest": _meta(parent.manifest_path),
            "cost": dict(cost),
            "cost_attribution": "parent generation is charged once",
        },
        "score": {
            "cell_id": reference.cell_id,
            "score_receipt": _meta(reference.path),
            "score_result": dict(score["score_result"]),
        },
    }


def _expected(
    parent: VerifiedBundle,
    *,
    repo_root: Path,
    score_receipts: Sequence[SavedScoreReceiptRef],
    scored_parent: bool = False,
) -> dict[str, object]:
    if (
        parent.manifest.get("schema") != RUN_MANIFEST_SCHEMA
        or parent.manifest.get("status") != STATUS_COMPLETED
    ):
        raise BundleError("phase delivery settlement requires an ordinary completed parent")
    if scored_parent:
        return _expected_scored_parent(
            parent, repo_root=repo_root, score_receipts=score_receipts,
        )
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
    is_phase = "required_phase_deliveries" in parent.manifest
    declaration_key = "required_phase_deliveries" if is_phase else "required_deliveries"
    return {
        "schema": SCHEMA if is_phase else DELIVERY_SCHEMA,
        "status": "complete",
        "parent": {
            "run_id": parent.manifest["run_id"],
            "attempt_id": attempt["attempt_id"],
            "manifest": parent_meta,
            "cost": dict(parent_cost),
            "cost_attribution": "parent generation is charged once",
        },
        declaration_key: [dict(item) for item in declarations],
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


def _verify_settlement(
    settlement_path: Path, *, repo_root: Path, scored_parent: bool = False,
) -> Mapping[str, object]:
    """Recompute every dependency of a saved settlement without scoring."""

    path = Path(settlement_path).resolve()
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BundleError(f"cannot read phase delivery settlement: {error}") from error
    schemas = {SCORED_SCHEMA} if scored_parent else {SCHEMA, DELIVERY_SCHEMA}
    if not isinstance(document, Mapping) or document.get("schema") not in schemas:
        raise BundleError("delivery settlement has an unknown schema")
    declaration_key = (
        "required_phase_deliveries" if document["schema"] == SCHEMA
        else "required_deliveries"
    )
    expected_keys = (
        {"schema", "status", "parent", "score"} if scored_parent
        else {"schema", "status", "parent", declaration_key, "deliveries"}
    )
    if set(document) != expected_keys:
        raise BundleError("delivery settlement has missing or unknown fields")
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
            scored_parent=scored_parent,
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
            "kind": document["schema"],
        }
        if attempt_document.get("finalization") != binding:
            raise BundleError("finalized attempt does not bind this settlement receipt")
    elif state != STATE_OPENED:
        raise BundleError("saved settlement belongs to a non-open terminal attempt")
    return document


def _settle_attempt(
    parent_manifest: Path,
    *,
    repo_root: Path,
    score_receipts: Sequence[SavedScoreReceiptRef],
    settlement_path: Path,
    scored_parent: bool = False,
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
            parent, repo_root=repo_root, score_receipts=tuple(score_receipts),
            scored_parent=scored_parent,
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
    _verify_settlement(
        settlement_path, repo_root=repo_root, scored_parent=scored_parent,
    )
    try:
        handle.finalize_with_receipt(
            str(settlement_path), receipt_sha256, document["schema"]
        )
    except AttemptError as error:
        raise BundleError(f"phase delivery settlement cannot finalize attempt: {error}") from error
    return PhaseDeliverySettlementResult(
        receipt_path=settlement_path,
        receipt_sha256=receipt_sha256,
        attempt_state="FINALIZED",
        reused=reused,
    )


def verify_phase_delivery_settlement(
    settlement_path: Path, *, repo_root: Path,
) -> Mapping[str, object]:
    """Verify all recorded derivative evidence without invoking a scorer."""
    return _verify_settlement(settlement_path, repo_root=repo_root)


def settle_phase_delivery_attempt(
    parent_manifest: Path, *, repo_root: Path,
    score_receipts: Sequence[SavedScoreReceiptRef], settlement_path: Path,
) -> PhaseDeliverySettlementResult:
    """Finalize only after all declared derivatives have complete saved scores."""
    return _settle_attempt(
        parent_manifest, repo_root=repo_root, score_receipts=score_receipts,
        settlement_path=settlement_path,
    )


def verify_scored_attempt_settlement(
    settlement_path: Path, *, repo_root: Path,
) -> Mapping[str, object]:
    """Verify a raw parent's saved score and finalization without rescoring."""
    return _verify_settlement(
        settlement_path, repo_root=repo_root, scored_parent=True,
    )


def settle_scored_attempt(
    parent_manifest: Path, *, repo_root: Path,
    score_receipt: SavedScoreReceiptRef, settlement_path: Path,
) -> PhaseDeliverySettlementResult:
    """Finalize a completed raw parent from its first complete saved score.

    Refuse parents with recorded delivery obligations. Keep the raw manifest,
    outputs, trace and saved scores immutable; reuse the common atomic
    publication and exact-retry finalization path.
    """
    return _settle_attempt(
        parent_manifest, repo_root=repo_root, score_receipts=(score_receipt,),
        settlement_path=settlement_path, scored_parent=True,
    )


def settle_delivery_attempt(
    parent_manifest: Path, *, repo_root: Path,
    score_receipts: Sequence[SavedScoreReceiptRef], settlement_path: Path,
) -> PhaseDeliverySettlementResult:
    """Settle every recorded derivative and charge the generation parent once."""
    return settle_phase_delivery_attempt(
        parent_manifest, repo_root=repo_root, score_receipts=score_receipts,
        settlement_path=settlement_path,
    )


def verify_delivery_settlement(
    settlement_path: Path, *, repo_root: Path,
) -> Mapping[str, object]:
    """Verify either a legacy OBS or phase-pair delivery settlement."""
    return verify_phase_delivery_settlement(settlement_path, repo_root=repo_root)


__all__ = [
    "PhaseDeliverySettlementResult",
    "SCHEMA",
    "DELIVERY_SCHEMA",
    "settle_delivery_attempt",
    "verify_delivery_settlement",
    "settle_phase_delivery_attempt",
    "verify_phase_delivery_settlement",
]
