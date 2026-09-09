"""One four-fragment factory for carrier-scoped shared FlightRuntime workers."""
from __future__ import annotations

from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse

from ...data.carriers import get_carrier_descriptor
from ...data.lock import load_lock, umbrella_lock_path
from ...rails.task_adapter import TaskAdapter
from ..base import TASK_ADAPTERS, CoreError, declared_derived_media_roots
from ..config import compose
from .runtime import FlightRuntime


def register_builtin_task_adapters() -> None:
    from ...rails.adapters.slurp_runtime import register_runtime_adapter
    register_runtime_adapter()


def build_flight_runtime(
    repo_root: Path, data_root: Path, *, model: str, dataset: str, baseline: str,
    experiment: str, run_id: str, attempt_id: str, runtime_root: Path,
    lock_path: Path | None = None, lock: Mapping[str, object] | None = None,
    campaign_active: bool = True, **runtime_seams,
) -> FlightRuntime:
    """Resolve one carrier adapter; all arms keep the same controller and executor."""
    repo_root, data_root = Path(repo_root), Path(data_root)
    values = compose(repo_root, model, dataset, baseline, experiment).values
    descriptor = get_carrier_descriptor(str(values["carrier_lock_key"]))
    register_builtin_task_adapters()
    builder = TASK_ADAPTERS.resolve(descriptor.lock_key)
    resolved_lock = lock if lock is not None else load_lock(
        Path(lock_path) if lock_path is not None else umbrella_lock_path(repo_root)
    )
    adapter = builder(values, resolved_lock, data_root, repo_root, dataset_fragment=dataset)
    if not isinstance(adapter, TaskAdapter):
        raise CoreError("registered task adapter builder must return TaskAdapter")
    url = urlparse(str(values.get("base_url", "http://127.0.0.1:8080")))
    if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise CoreError("flight workers require the loopback resident service")
    options = {"host": url.hostname, "port": url.port or 8080}
    roots = declared_derived_media_roots(values, data_root)
    if len(roots) > 1:
        raise CoreError("runtime carrier view must select one derived media root")
    if roots:
        options["carrier_root_resolver"] = lambda *_args: roots[0]
    options.update(runtime_seams)
    runtime = FlightRuntime(
        repo_root, data_root, model=model, dataset=dataset, baseline=baseline,
        experiment=experiment, run_id=run_id, attempt_id=attempt_id,
        runtime_root=runtime_root, adapter_factory=lambda *_args: adapter,
        lock=resolved_lock, campaign_active=campaign_active, **options,
    )
    adapter.bind_runtime(runtime, values)
    return runtime
