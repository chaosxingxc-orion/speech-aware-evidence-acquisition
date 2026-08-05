"""MLflow linkage and the umbrella experiment-index row renderer (R0).

mlflow is an optional extra (`pip install -e ".[tracking]"`); the import is
lazy so the model-free test environment never needs it.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Mapping

from ..contracts import ExecutionPlan
from .base import RunResult
from .config import ComposedConfig

if TYPE_CHECKING:  # pragma: no cover -- type-checking only, avoids a core.bundle cycle
    from .bundle import VerifiedBundle

LEDGER_COLUMNS: tuple[str, ...] = (
    "experiment_id", "date", "speech task/carrier", "changed axes", "study commit",
    "shared code revision", "config hash", "protocol hash", "model rev", "dataset rev",
    "split role", "split identity hash", "consumed", "MLflow run", "artifact location",
    "artifact hashes", "effectiveness", "reasonableness", "efficiency", "deviations",
    "decision",
)


class MlflowUnavailable(RuntimeError):
    """mlflow is not installed in this environment."""


def _require_mlflow():
    try:
        import mlflow
    except ImportError as error:
        raise MlflowUnavailable(
            'mlflow is required for run tracking: pip install -e ".[tracking]"'
        ) from error
    return mlflow


def ledger_row(cells: Mapping[str, str]) -> str:
    if set(cells) != set(LEDGER_COLUMNS):
        raise ValueError(
            f"ledger row must have exactly the columns {LEDGER_COLUMNS}; got {sorted(cells)}"
        )
    for column, value in cells.items():
        if "|" in value:
            raise ValueError(f"ledger cell {column!r} contains a pipe character")
        if "\n" in value or "\r" in value:
            raise ValueError(f"ledger cell {column!r} contains a newline character")
    return "| " + " | ".join(cells[column] for column in LEDGER_COLUMNS) + " |"


def log_run(
    result: RunResult,
    composed: ComposedConfig,
    plan: ExecutionPlan,
    protocol: str,
    tracking_uri: str,
    metrics: Mapping[str, float] | None = None,
) -> str:
    mlflow = _require_mlflow()
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("speech-aware-evidence-acquisition")
    with mlflow.start_run(run_name=plan.run_id) as active:
        mlflow.log_params(
            {
                "arm": result.arm,
                "config_hash": composed.config_hash,
                "protocol_hash": protocol,
                "split_role": plan.split_role,
                "split_identity_hash": plan.split_identity_hash,
                "execution_profile": plan.execution_profile,
                "carrier_lock_key": plan.carrier_lock_key,
            }
        )
        numeric_cost = {
            key: float(value)
            for key, value in result.cost.items()
            if isinstance(value, (int, float))
        }
        mlflow.log_metrics({**numeric_cost, **(dict(metrics) if metrics else {})})
        mlflow.log_artifact(str(result.outputs_path))
        manifest = result.outputs_path.with_name(f"{result.run_id}.trace-manifest.json")
        mlflow.log_artifact(str(manifest))
        return active.info.run_id


# ---------------------------------------------------------------------------
# R0 repair T6 (invariant I7): the run-bundle-aware counterparts. ``log_run``
# above is left exactly as it was (still used standalone, still tested
# standalone) -- these are additive, driven by a verified
# ``core.bundle.VerifiedBundle`` rather than a bare ``RunResult``.
# ---------------------------------------------------------------------------

_MANIFEST_ARTIFACT_KEYS = ("outputs", "raw_trace", "trace_manifest", "scores", "session_receipt")


def _artifact_hash_summary(manifest: Mapping[str, object]) -> str:
    parts = []
    for key in _MANIFEST_ARTIFACT_KEYS:
        entry = manifest.get(key)
        if isinstance(entry, Mapping) and isinstance(entry.get("sha256"), str):
            parts.append(f"{key}={entry['sha256']}")
    return ";".join(parts)


def bundle_ledger_cells(bundle: "VerifiedBundle") -> dict[str, str]:
    """The subset of :data:`LEDGER_COLUMNS` strictly derivable from a
    verified run manifest -- study identity/config/protocol/split hashes,
    the artifact location and every artifact's own hash, ``consumed`` (a
    manifest only ever reaches this function via ``finalize_bundle``, which
    is the one path that marks an attempt consumed), and ``date`` (from the
    manifest's own ``created_at``). Deliberately NOT the full column set:
    ``experiment_id``/``speech task/carrier``/``changed axes``/
    ``shared code revision``/``model rev``/``dataset rev``/``MLflow run``/
    ``effectiveness``/``reasonableness``/``efficiency``/``deviations``/
    ``decision`` are human judgment or external-index facts this module has
    no basis to invent, and stay the caller's responsibility.
    """

    manifest = bundle.manifest
    created_at = str(manifest.get("created_at") or "")
    return {
        "study commit": str(manifest["study_commit"]),
        "config hash": str(manifest["config"]["config_hash"]),
        "protocol hash": str(manifest["protocol_hash"]),
        "split role": str(manifest["plan"]["split_role"]),
        "split identity hash": str(manifest["split"]["identity_hash"]),
        "consumed": "yes",
        "artifact location": str(Path(bundle.manifest_path).resolve().parent),
        "artifact hashes": _artifact_hash_summary(manifest),
        "date": created_at[:10],
    }


def ledger_row_for_bundle(
    bundle: "VerifiedBundle", cells: Mapping[str, str]
) -> tuple[str, dict[str, str]]:
    """Render one ledger row where the machine-derivable cells
    (:func:`bundle_ledger_cells`) come ONLY from the verified bundle. A
    hand-supplied cell naming one of those columns is accepted only if it
    agrees byte-for-byte with the verified value, and refused
    (``ValueError``) otherwise: a caller cannot talk a finalized row into a
    study commit, config hash, protocol hash, split identity hash, or
    artifact-hash summary the bundle did not actually verify. Every other
    column (the human/judgment ones) is taken from ``cells`` as given; the
    merged mapping must still carry exactly :data:`LEDGER_COLUMNS`
    (``ledger_row`` enforces that) or this raises too.
    """

    derived = bundle_ledger_cells(bundle)
    conflicts = {
        column: (cells[column], derived[column])
        for column in derived
        if column in cells and cells[column] != derived[column]
    }
    if conflicts:
        detail = "; ".join(
            f"{column!r} hand-supplied={hand!r} verified={verified!r}"
            for column, (hand, verified) in conflicts.items()
        )
        raise ValueError(
            f"hand-supplied ledger cells contradict the verified run manifest: {detail}"
        )
    merged = {**cells, **derived}
    row = ledger_row(merged)
    return row, merged


def log_bundle(
    bundle: "VerifiedBundle",
    tracking_uri: str,
    metrics: Mapping[str, float] | None = None,
) -> str:
    """Upload a FULL bundle: outputs, raw trace, trace manifest, scores (once
    attached) and the manifest itself -- the closure ``log_run`` never had
    (only outputs + trace manifest were ever uploaded; never the raw trace,
    never a score artifact, never the manifest binding them together)."""

    mlflow = _require_mlflow()
    manifest = bundle.manifest
    plan = manifest["plan"]
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("speech-aware-evidence-acquisition")
    with mlflow.start_run(run_name=str(manifest["run_id"])) as active:
        mlflow.log_params(
            {
                "config_hash": manifest["config"]["config_hash"],
                "protocol_hash": manifest["protocol_hash"],
                "split_role": plan["split_role"],
                "split_identity_hash": manifest["split"]["identity_hash"],
                "execution_profile": plan["execution_profile"],
                "carrier_lock_key": plan["carrier_lock_key"],
                "study_commit": manifest["study_commit"],
            }
        )
        numeric_cost = {
            key: float(value)
            for key, value in dict(manifest.get("cost") or {}).items()
            if isinstance(value, (int, float))
        }
        mlflow.log_metrics({**numeric_cost, **(dict(metrics) if metrics else {})})
        for key in _MANIFEST_ARTIFACT_KEYS[:4]:  # outputs, raw_trace, trace_manifest, scores
            entry = manifest.get(key)
            if isinstance(entry, Mapping) and entry.get("path"):
                mlflow.log_artifact(str(entry["path"]))
        mlflow.log_artifact(str(bundle.manifest_path))
        return active.info.run_id
