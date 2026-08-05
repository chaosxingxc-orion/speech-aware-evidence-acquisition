"""MLflow linkage and the umbrella experiment-index row renderer (R0).

mlflow is an optional extra (`pip install -e ".[tracking]"`); the import is
lazy so the model-free test environment never needs it.
"""

from __future__ import annotations

from typing import Mapping

from ..contracts import ExecutionPlan
from .base import RunResult
from .config import ComposedConfig

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
