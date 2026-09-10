"""Root coordination of registered fits after all model-free request preparation."""
from __future__ import annotations

import argparse
from functools import partial
import json
import os
from pathlib import Path
import time

from ..bundle.git_commit import require_clean_study_repo
from ..preparation import PreparationError, canonical_bytes, load_artifact
from ..preparation_fit import fit_phase_runtime, materialize_phase_fit
from ..session.serving import find_resident_session
from .campaign import CampaignError, load_campaign_cells
from .coordinator import coordinate_fit
from .factory import build_flight_runtime


def coordinate_fit_batch(
    flights, jobs, *, repo_root, data_root, runtime_root, owner,
    expected_session_id, event_sink=lambda event: None,
    materializer=materialize_phase_fit, coordinator=coordinate_fit,
):
    """Materialize every request before the first root-owned service attachment.

    Keep batches in memory. Each ordinary fitter still revalidates source,
    configuration, custody and committed exposure before accessing an endpoint.
    Stop dispatch after the first failure; retain completed fit artifacts.
    """
    if not flights or len(flights) != len(jobs):
        raise CampaignError("fit batch must contain matching nonempty flights and jobs")
    identities = [(flight.run_id, flight.attempt_id) for flight in flights]
    if len(set(identities)) != len(identities):
        raise CampaignError("fit batch repeats a run and attempt")
    outputs = [str(Path(job["output"]).resolve()) for job in jobs]
    if len(set(outputs)) != len(outputs):
        raise CampaignError("fit batch repeats an output artifact")
    root = Path(data_root).resolve()
    for job in jobs:
        cap = job["contact_cap"]
        if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
            raise CampaignError("fit batch requires positive integer endpoint caps")
        if not Path(job["output"]).resolve().is_relative_to(root):
            raise CampaignError("fit output must stay beneath data root")
    contexts = [flight.preparation_context() for flight in flights]
    serving = [canonical_bytes(context["required_identity"]) for context in contexts]
    if len(set(serving)) != 1:
        raise CampaignError("fit batch requires one complete serving identity")
    prepared = []
    for flight in flights:
        started = time.monotonic()
        event_sink({"event": "materialize-start", "run_id": flight.run_id})
        batch = materializer(flight)
        prepared.append(batch)
        event_sink({
            "event": "materialize-complete", "run_id": flight.run_id,
            "elapsed_seconds": time.monotonic() - started,
        })
    event_sink({"event": "all-requests-materialized", "flights": len(flights)})
    results = []
    for flight, job, batch in zip(flights, jobs, prepared, strict=True):
        event_sink({"event": "fit-start", "run_id": flight.run_id})
        result = coordinator(
            flight, repo_root=Path(repo_root), data_root=root,
            runtime_root=Path(runtime_root), output=Path(job["output"]),
            owner=owner, expected_session_id=expected_session_id,
            contact_cap=job["contact_cap"], model_fragment=job["model_fragment"],
            fit_runner=partial(fit_phase_runtime, prepared_phase=batch),
            hold_wrapper_foreground=False,
        )
        checked = load_artifact(
            Path(result["path"]), expected_sha256=result["sha256"],
            kind="request-fit", inputs=json.loads(batch.inputs_bytes),
        )
        if checked.get("every_request_fits") is not True:
            raise PreparationError("fit batch stopped: at least one actual request does not fit")
        results.append({"run_id": flight.run_id, **result})
        event_sink({"event": "fit-complete", "run_id": flight.run_id, "artifact": result})
    return {"schema": "saea-fit-batch-completion-v1", "results": results}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo-root", "data-root", "runtime-root", "lock-path", "plan",
                 "owner", "expected-session-id", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    repo = Path(args.repo_root).resolve()
    data = Path(args.data_root).resolve()
    if repo != Path(__file__).resolve().parents[4]:
        parser.error("imported package must belong to repo-root")
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        parser.error("PYTHONDONTWRITEBYTECODE=1 is required")
    plan_path = Path(args.plan).resolve()
    if not plan_path.is_relative_to(repo):
        parser.error("fit batch plan must be committed within repo-root")
    output = Path(args.output).resolve()
    if not output.is_relative_to(data) or output.exists():
        parser.error("use a fresh batch completion path under data-root")
    plan = json.loads(plan_path.read_bytes())
    if plan.get("schema") != "saea-fit-batch-plan-v1" or not isinstance(plan.get("fits"), list):
        parser.error("invalid fit batch plan")
    require_clean_study_repo(repo)
    flights, jobs = [], []
    for item in plan["fits"]:
        cells = [
            c for c in load_campaign_cells(repo, item["experiment"])
            if c.document["cell_id"] == item["cell"]
        ]
        if len(cells) != 1:
            parser.error("fit batch cell must resolve exactly once")
        cell = cells[0]
        cell.assert_mode("prompt-fit")
        if not cell.run_id.endswith("-FIT-V1"):
            parser.error("fit batch requires a separately registered capacity run")
        relative = Path(item["output_relpath"])
        if relative.is_absolute() or ".." in relative.parts or "\\" in item["output_relpath"]:
            parser.error("fit output path must be confined")
        jobs.append({
            "output": data / relative, "contact_cap": item["contact_cap"],
            "model_fragment": cell.document["model_fragment"],
        })
        flights.append(build_flight_runtime(
            repo, data, model=cell.document["model_fragment"],
            dataset=cell.document["dataset_fragment"], baseline=cell.document["baseline_fragment"],
            experiment=item["experiment"], run_id=cell.run_id, attempt_id=cell.attempt_id,
            runtime_root=Path(args.runtime_root), lock_path=Path(args.lock_path),
        ))
    output.parent.mkdir(parents=True, exist_ok=True)
    journal = output.with_name(output.name + ".events.jsonl")
    with journal.open("x", encoding="utf-8") as stream:
        def event_sink(event):
            row = {"timestamp_unix": time.time(), **event}
            line = json.dumps(row, sort_keys=True, default=str)
            stream.write(line + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            print(line, flush=True)

        error = None
        try:
            result = coordinate_fit_batch(
                flights, jobs, repo_root=repo, data_root=data,
                runtime_root=Path(args.runtime_root), owner=args.owner,
                expected_session_id=args.expected_session_id, event_sink=event_sink,
            )
            with output.open("x", encoding="utf-8") as target:
                target.write(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n")
            event_sink({"event": "batch-complete", "output": str(output)})
        except Exception as caught:
            error = caught
            event_sink({"event": "batch-failed", "error_type": type(caught).__name__,
                        "error": str(caught), "automatic_retry": False})
        # Keep root's WSL host alive while subsequent workers use the session.
        # Service stop/recovery and monitor cleanup remain explicit root actions.
        while True:
            resident = find_resident_session(data)
            if resident is None or resident[1].get("session_id") != args.expected_session_id:
                break
            time.sleep(1)
        if error is not None:
            raise error
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
