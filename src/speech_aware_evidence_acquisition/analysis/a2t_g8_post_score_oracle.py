"""Post-seal, model-free construction of the G8 branch-oracle bundle.

This module is deliberately downstream of the four already-sealed branch
manifests and their four official detailed-score payloads.  It neither reads
the carrier nor invokes a model or scorer.  Gold-derived values may appear
only in the post-score selection inputs; the emitted output rows reuse sealed
response bytes and bind their origin through TOOL trace records.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Mapping, Sequence

from ..core.base import RunResult
from ..core.bundle import STATUS_COMPLETED, build_manifest
from ..core.tracing import TraceSink


BRANCH_ORDER = (
    "STOP_M0",
    "EXHAUSTIVE_G7",
    "SUPPORT_ONLY_RESOLVE",
    "DECOMPOSED_SELECT_BIND_RESOLVE",
)
OFFICIAL_SCORER = "a2t-toolcall"
ORACLE_TOOL_ID = "saea-a2t-g8-post-score-branch-oracle-v1"


class G8OracleError(RuntimeError):
    """A post-score oracle input or output boundary is not auditable."""


@dataclass(frozen=True)
class OracleSelection:
    """One selected sealed response and its score-derived branch provenance."""

    sample_id: str
    branch: str
    text: str
    exact_match: float
    slot_f1: float
    tool_accuracy: float
    source_manifest: Path
    source_manifest_sha256: str
    source_outputs: Path
    source_outputs_sha256: str
    score_payload_sha256: str


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except OSError as error:
        raise G8OracleError(f"cannot read sealed artifact {path}: {error}") from error


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def _positive_count(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise G8OracleError(f"{label} must be a positive integer")
    return value


def _exact_sample_ids(
    sample_ids: Sequence[str], *, expected_sample_count: int = 16
) -> tuple[str, ...]:
    expected = _positive_count(expected_sample_count, "expected_sample_count")
    values = tuple(sample_ids)
    if (
        len(values) != expected
        or len(set(values)) != expected
        or any(not isinstance(item, str) or not item for item in values)
    ):
        raise G8OracleError(
            f"G8 oracle requires exactly {expected} unique non-empty sample identities"
        )
    return values


def _exact_branches(
    value: Mapping[str, object], label: str, branch_order: Sequence[str]
) -> None:
    if (
        len(branch_order) != 4
        or len(set(branch_order)) != 4
        or any(not isinstance(branch, str) or not branch for branch in branch_order)
    ):
        raise G8OracleError(
            "oracle branch order must contain four unique non-empty names"
        )
    if set(value) != set(branch_order):
        raise G8OracleError(
            f"{label} must name exactly the four frozen oracle branches"
        )


def _path(value: object, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise G8OracleError(f"{label} must be a non-empty path string")
    path = Path(value).resolve()
    if not path.is_file():
        raise G8OracleError(f"{label} does not exist: {path}")
    return path


def _sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise G8OracleError(f"{label} must be a lowercase SHA-256")
    return value


def _metric(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise G8OracleError(f"{label} must be a finite numeric score")
    result = float(value)
    if not 0.0 <= result <= 1.0:
        raise G8OracleError(f"{label} must be within [0, 1]")
    return result


def _score_rows(
    *,
    branch: str,
    payload: Mapping[str, object],
    manifest: Path,
    sample_ids: tuple[str, ...],
) -> Mapping[str, Mapping[str, float]]:
    if payload.get("verified") is not True:
        raise G8OracleError(f"{branch} score payload is not verified")
    payload_manifest = _path(
        payload.get("manifest"), f"{branch} score payload manifest"
    )
    if payload_manifest != manifest:
        raise G8OracleError(
            f"{branch} score payload manifest identity does not match sealed branch"
        )
    scores = payload.get("scores")
    if not isinstance(scores, Mapping) or set(scores) != {OFFICIAL_SCORER}:
        raise G8OracleError(
            f"{branch} score payload must contain only {OFFICIAL_SCORER}"
        )
    official = scores.get(OFFICIAL_SCORER)
    if not isinstance(official, Mapping):
        raise G8OracleError(f"{branch} {OFFICIAL_SCORER} score is malformed")
    aggregate = official.get("aggregate")
    details = official.get("per_sample")
    if not isinstance(aggregate, Mapping) or aggregate.get("samples") != len(
        sample_ids
    ):
        raise G8OracleError(
            f"{branch} {OFFICIAL_SCORER} aggregate does not cover the expected sample set"
        )
    if not isinstance(details, list):
        raise G8OracleError(f"{branch} {OFFICIAL_SCORER} lacks per_sample detail")

    rows: dict[str, Mapping[str, float]] = {}
    for detail in details:
        if not isinstance(detail, Mapping):
            raise G8OracleError(f"{branch} per_sample row is malformed")
        sample_id = detail.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id or sample_id in rows:
            raise G8OracleError(
                f"{branch} per_sample rows have duplicate or invalid sample identities"
            )
        rows[sample_id] = {
            "exact_match": _metric(
                detail.get("exact_match"), f"{branch}/{sample_id} exact_match"
            ),
            "slot_f1": _metric(detail.get("slot_f1"), f"{branch}/{sample_id} slot_f1"),
            "tool_accuracy": _metric(
                detail.get("tool_accuracy"), f"{branch}/{sample_id} tool_accuracy"
            ),
        }
    if set(rows) != set(sample_ids):
        raise G8OracleError(
            f"{branch} per_sample sample identities do not match the expected sample set"
        )
    return rows


def validate_branch_score_payloads(
    *,
    score_payloads: Mapping[str, Mapping[str, object]],
    sealed_branches: Mapping[str, Mapping[str, object]],
    sample_ids: Sequence[str],
    expected_sample_count: int = 16,
    branch_order: Sequence[str] = BRANCH_ORDER,
) -> Mapping[str, Mapping[str, Mapping[str, float]]]:
    """Validate the four one-pass official score payloads before any selection."""

    ids = _exact_sample_ids(sample_ids, expected_sample_count=expected_sample_count)
    order = tuple(branch_order)
    _exact_branches(score_payloads, "score payloads", order)
    _exact_branches(sealed_branches, "sealed branches", order)
    validated: dict[str, Mapping[str, Mapping[str, float]]] = {}
    for branch in order:
        seal = sealed_branches[branch]
        if not isinstance(seal, Mapping):
            raise G8OracleError(f"{branch} sealed branch descriptor is malformed")
        manifest = _path(seal.get("manifest"), f"{branch} sealed manifest")
        payload = score_payloads[branch]
        if not isinstance(payload, Mapping):
            raise G8OracleError(f"{branch} score payload is malformed")
        validated[branch] = _score_rows(
            branch=branch, payload=payload, manifest=manifest, sample_ids=ids
        )
    return validated


def _read_sealed_rows(
    path: Path, branch: str, sample_ids: tuple[str, ...]
) -> Mapping[str, Mapping[str, object]]:
    try:
        lines = path.read_text(encoding="utf-8").split("\n")
    except (OSError, UnicodeError) as error:
        raise G8OracleError(f"cannot read {branch} sealed outputs: {error}") from error
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        raise G8OracleError(f"{branch} sealed outputs are empty")
    rows: dict[str, Mapping[str, object]] = {}
    for number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise G8OracleError(
                f"{branch} sealed outputs line {number} is malformed"
            ) from error
        if not isinstance(row, Mapping):
            raise G8OracleError(
                f"{branch} sealed outputs line {number} is not an object"
            )
        sample_id = row.get("sample_id")
        text = row.get("text")
        response_hash = row.get("response_text_sha256")
        if (
            not isinstance(sample_id, str)
            or sample_id in rows
            or not isinstance(text, str)
        ):
            raise G8OracleError(
                f"{branch} sealed output identities or text are malformed"
            )
        if response_hash != _sha256_bytes(text.encode("utf-8")):
            raise G8OracleError(f"{branch} sealed output response text hash drift")
        rows[sample_id] = dict(row)
    if set(rows) != set(sample_ids):
        raise G8OracleError(
            f"{branch} sealed output sample identities do not match the expected sample set"
        )
    return rows


def validate_sealed_branch_outputs(
    *,
    sealed_branches: Mapping[str, Mapping[str, object]],
    sample_ids: Sequence[str],
    expected_sample_count: int = 16,
    branch_order: Sequence[str] = BRANCH_ORDER,
) -> Mapping[str, Mapping[str, Mapping[str, object]]]:
    """Rehash and identity-check all four sealed branch output artifacts."""

    ids = _exact_sample_ids(sample_ids, expected_sample_count=expected_sample_count)
    order = tuple(branch_order)
    _exact_branches(sealed_branches, "sealed branches", order)
    validated: dict[str, Mapping[str, Mapping[str, object]]] = {}
    for branch in order:
        seal = sealed_branches[branch]
        if not isinstance(seal, Mapping):
            raise G8OracleError(f"{branch} sealed branch descriptor is malformed")
        manifest = _path(seal.get("manifest"), f"{branch} sealed manifest")
        declared_manifest_hash = _sha256(
            seal.get("manifest_sha256"), f"{branch} manifest_sha256"
        )
        if _sha256_file(manifest) != declared_manifest_hash:
            raise G8OracleError(f"{branch} manifest hash drift")
        outputs = _path(seal.get("outputs"), f"{branch} sealed outputs")
        declared_outputs_hash = _sha256(
            seal.get("outputs_sha256"), f"{branch} outputs_sha256"
        )
        if _sha256_file(outputs) != declared_outputs_hash:
            raise G8OracleError(f"{branch} output hash drift")
        validated[branch] = _read_sealed_rows(outputs, branch, ids)
    return validated


def select_oracle_rows(
    *,
    score_payloads: Mapping[str, Mapping[str, object]],
    sealed_branches: Mapping[str, Mapping[str, object]],
    sample_ids: Sequence[str],
    expected_sample_count: int = 16,
    branch_order: Sequence[str] = BRANCH_ORDER,
) -> tuple[tuple[OracleSelection, ...], Mapping[str, object]]:
    """Choose one existing sealed output per row using the frozen comparator."""

    ids = _exact_sample_ids(sample_ids, expected_sample_count=expected_sample_count)
    order = tuple(branch_order)
    scores = validate_branch_score_payloads(
        score_payloads=score_payloads,
        sealed_branches=sealed_branches,
        sample_ids=ids,
        expected_sample_count=expected_sample_count,
        branch_order=order,
    )
    outputs = validate_sealed_branch_outputs(
        sealed_branches=sealed_branches,
        sample_ids=ids,
        expected_sample_count=expected_sample_count,
        branch_order=order,
    )
    selections: list[OracleSelection] = []
    counts = {branch: 0 for branch in order}
    exact_count = 0
    for sample_id in ids:
        branch = max(
            order,
            key=lambda candidate: (
                scores[candidate][sample_id]["exact_match"],
                scores[candidate][sample_id]["slot_f1"],
                scores[candidate][sample_id]["tool_accuracy"],
                -order.index(candidate),
            ),
        )
        metric = scores[branch][sample_id]
        seal = sealed_branches[branch]
        source_manifest = _path(seal.get("manifest"), f"{branch} sealed manifest")
        source_outputs = _path(seal.get("outputs"), f"{branch} sealed outputs")
        selection = OracleSelection(
            sample_id=sample_id,
            branch=branch,
            text=str(outputs[branch][sample_id]["text"]),
            exact_match=metric["exact_match"],
            slot_f1=metric["slot_f1"],
            tool_accuracy=metric["tool_accuracy"],
            source_manifest=source_manifest,
            source_manifest_sha256=_sha256(
                seal.get("manifest_sha256"), f"{branch} manifest_sha256"
            ),
            source_outputs=source_outputs,
            source_outputs_sha256=_sha256(
                seal.get("outputs_sha256"), f"{branch} outputs_sha256"
            ),
            score_payload_sha256=_sha256_bytes(
                _canonical_payload_bytes(score_payloads[branch])
            ),
        )
        selections.append(selection)
        counts[branch] += 1
        exact_count += int(selection.exact_match == 1.0)
    return tuple(selections), {
        "samples": len(ids),
        "oracle_exact_count": exact_count,
        "selected_by_branch": counts,
        "selection_rule": "exact_match > slot_f1 > tool_accuracy > frozen_branch_order",
        "new_model_contacts": 0,
    }


def _canonical_payload_bytes(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _oracle_rows(
    selections: Sequence[OracleSelection],
    sink: TraceSink,
    *,
    carrier_lock_key: str,
    arm: str,
) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for index, selection in enumerate(
        sorted(selections, key=lambda item: item.sample_id), start=1
    ):
        request_id = f"g8-oracle-composite-{index:04d}"
        source = {
            "branch": selection.branch,
            "selection_metrics": {
                "exact_match": selection.exact_match,
                "slot_f1": selection.slot_f1,
                "tool_accuracy": selection.tool_accuracy,
            },
            "source_score_payload_sha256": selection.score_payload_sha256,
            "source_manifest_path": str(selection.source_manifest),
            "source_manifest_sha256": selection.source_manifest_sha256,
            "source_artifact_path": str(selection.source_outputs),
            "source_artifact_sha256": selection.source_outputs_sha256,
        }
        request = {
            "tool_id": ORACLE_TOOL_ID,
            "sample_id": selection.sample_id,
            "source": source,
        }
        request_sha256 = _sha256_bytes(_canonical_payload_bytes(request))
        response_text_sha256 = _sha256_bytes(selection.text.encode("utf-8"))
        response = {
            "tool_id": ORACLE_TOOL_ID,
            "sample_id": selection.sample_id,
            "source": source,
            "text_sha256": response_text_sha256,
        }
        response_sha256 = _sha256_bytes(_canonical_payload_bytes(response))
        sink.emit(
            "TOOL",
            f"{request_id}/request",
            {**request, "payload_sha256": request_sha256},
        )
        sink.emit(
            "TOOL",
            f"{request_id}/response",
            {
                **response,
                "text": selection.text,
                "response_sha256": response_sha256,
                "response_text_sha256": response_text_sha256,
            },
        )
        rows.append(
            {
                "request_id": request_id,
                "sample_id": selection.sample_id,
                "carrier_lock_key": carrier_lock_key,
                "arm": arm,
                "text": selection.text,
                "admitted": True,
                "request_sha256": request_sha256,
                "response_sha256": response_sha256,
                "response_text_sha256": response_text_sha256,
                "composite_source": source,
            }
        )
    return tuple(rows)


def build_oracle_artifacts(
    *,
    score_payloads: Mapping[str, Mapping[str, object]],
    sealed_branches: Mapping[str, Mapping[str, object]],
    sample_ids: Sequence[str],
    expected_sample_count: int = 16,
    parent_physical_contacts_once: int = 544,
    run_dir: Path,
    parent_composed: object,
    parent_plan: object,
    parent_verified_split: object,
    data_root: Path,
    session_receipt_path: Path,
    branch_order: Sequence[str] = BRANCH_ORDER,
) -> Mapping[str, object]:
    """Materialize a sealed oracle bundle for one later unchanged scorer call.

    The caller supplies the parent G8 config, plan, split, and session receipt;
    no new runtime state is created.  The returned manifest has exactly the
    official scorer configured but this function never invokes it.
    """

    parent_contacts = _positive_count(
        parent_physical_contacts_once, "parent_physical_contacts_once"
    )
    selections, summary = select_oracle_rows(
        score_payloads=score_payloads,
        sealed_branches=sealed_branches,
        sample_ids=sample_ids,
        expected_sample_count=expected_sample_count,
        branch_order=branch_order,
    )
    run_dir = Path(run_dir)
    if run_dir.exists() and any(run_dir.iterdir()):
        raise G8OracleError(f"oracle output directory is not empty: {run_dir}")
    run_id = getattr(parent_plan, "run_id", None)
    if not isinstance(run_id, str) or not run_id:
        raise G8OracleError("parent G8 plan lacks a run_id")
    values = getattr(parent_composed, "values", {})
    if values is None:
        values = {}
    if not isinstance(values, Mapping):
        raise G8OracleError("parent G8 composed configuration lacks values")
    carrier_lock_key = values.get("carrier_lock_key", "audio2tool")
    arm = values.get("arm", "speech-feature-query")
    if (
        not isinstance(carrier_lock_key, str)
        or not carrier_lock_key
        or not isinstance(arm, str)
        or not arm
    ):
        raise G8OracleError(
            "parent G8 composed configuration has an invalid carrier or arm"
        )

    run_dir.mkdir(parents=True, exist_ok=True)
    sink = TraceSink(run_dir, run_id)
    try:
        rows = _oracle_rows(
            selections, sink, carrier_lock_key=carrier_lock_key, arm=arm
        )
        trace_hash = sink.close()
    except Exception:
        # The trace remains a forensic artifact if a later artifact write fails;
        # it is never overwritten on a retry.
        sink.close()
        raise
    outputs = run_dir / f"{run_id}.oracle.outputs.jsonl"
    _write_jsonl(outputs, rows)
    cost = {
        "calls_used": 0,
        "new_model_contacts": 0,
        "logical_action_contacts": 0,
        "logical_costs_are_nonadditive": True,
        "parent_physical_contacts_once": parent_contacts,
        "parent_cost_is_inherited": True,
    }
    manifest = build_manifest(
        repo_root=Path(__file__).resolve().parents[3],
        data_root=Path(data_root),
        composed=parent_composed,
        plan=parent_plan,
        verified_split=parent_verified_split,
        session_receipt_path=Path(session_receipt_path),
        run_dir=run_dir,
        status=STATUS_COMPLETED,
        result=RunResult(
            run_id=run_id,
            arm=arm,
            outputs_path=outputs,
            trace_manifest_hash=trace_hash,
            cost=cost,
        ),
    )
    try:
        manifest_document = json.loads(Path(manifest).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise G8OracleError(
            f"cannot bind oracle manifest {manifest}: {error}"
        ) from error
    manifest_document["scorers"] = [OFFICIAL_SCORER]
    manifest_document["post_score_oracle"] = {
        "model_contacts": 0,
        "source_branch_order": list(branch_order),
        "source_manifests": {
            branch: str(
                _path(
                    sealed_branches[branch].get("manifest"), f"{branch} sealed manifest"
                )
            )
            for branch in branch_order
        },
        "selection_summary": summary,
        "scoring_invocations_authorized": 1,
    }
    _write_json(Path(manifest), manifest_document)
    return {
        "outputs": str(outputs),
        "outputs_sha256": _sha256_file(outputs),
        "trace_manifest": str(run_dir / f"{run_id}.trace-manifest.json"),
        "trace_manifest_sha256": trace_hash,
        "manifest": str(manifest),
        "new_model_contacts": 0,
        "scoring_invocations": 1,
        "selection_summary": summary,
    }


__all__ = [
    "BRANCH_ORDER",
    "G8OracleError",
    "OFFICIAL_SCORER",
    "ORACLE_TOOL_ID",
    "OracleSelection",
    "build_oracle_artifacts",
    "select_oracle_rows",
    "validate_branch_score_payloads",
    "validate_sealed_branch_outputs",
]
