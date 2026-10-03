"""Whole-family source custody for root-only context engineering descriptions.

The caller must verify the exact ledger READ before invoking these functions.
No scorer, model, proposer, queue or immutable source is modified here.
"""
import hashlib
import json
import math
from pathlib import Path

from ..core.bundle.verify import verify_bundle
from ..core.config import model_materialization_root, resolve_runtime_receipt_path
from ..core.configured_transport import build_configured_transport
from ..core.session.receipt import SessionReceipt, load_runtime_receipt, resolve_pinned_session_receipt
from ..rails.system_text_feedback import _row_cost_and_terminal
from ..rails.system_text_policy import _read_pin, require
from ..rails.hashing import content_hash
from .native_episode_source import verify_native_episode_source
from .system_cache_cost import export_system_node_timing, export_system_sample_timing
from .system_feedback import load_system_feedback
from .system_semantic_trajectory import materialize_semantic_trajectories
from .system_wire_context import audit_context_execution, load_actor_wire_requests, prepare_actor_wire_requests


def _identity(value):
    require(isinstance(value, str) and value and value not in (".", "..")
            and "/" not in value and "\\" not in value, "invalid member path identity")
    return value


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _pin(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    require(path.is_relative_to(root), "source escaped the registered data root")
    return {"relpath": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def describe_stage_timing(flight, batch):
    """Retain observed experiment-stage durations, never infer sample latency.

    Call only after the reader qualifies the original complete source. Missing
    historical timers remain unknown; nested scoring timers are not additive.
    """
    stages = flight.get("stages", {})
    jobs = batch.get("jobs", [])
    require(isinstance(jobs, list) and len(jobs) <= 1, "stage timing requires at most one official worker")
    fields = {
        "preprocess_seconds": (stages.get("preprocess", {}), "duration_seconds"),
        "packet_validation_seconds": (stages.get("preprocess", {}), "packet_validation_seconds"),
        "service_startup_seconds": (stages.get("serve", {}), "startup_seconds"),
        "generation_wall_seconds": (stages.get("run_phases", {}), "wall_seconds"),
        "client_initialization_seconds": (stages.get("run_phases", {}), "client_initialization_seconds"),
        "score_stage_seconds": (stages.get("score", {}), "duration_seconds"),
        "score_batch_seconds": (batch, "elapsed_seconds"),
        "official_finalize_worker_seconds": (jobs[0] if jobs else {}, "elapsed_seconds"),
    }
    result = {}
    for name, (row, key) in fields.items():
        value = row.get(key)
        require(value is None or type(value) in (int, float) and math.isfinite(value) and value >= 0,
                "stage timing must be a finite nonnegative number or unavailable")
        result[name] = value
    result["measurement_boundary"] = (
        "Whole experiment stages, not sample latency. Scoring stage, batch and worker timers are nested, "
        "not additive. Do not divide generation wall by rows to estimate sample latency. "
        "Driver admission, inter-step waits and unmeasured work are not reconstructed."
    )
    return result


def preflight_members(registration, *, data_root, sample_ids, commit):
    """Check all operational members before parsing any seal or task result."""
    root = Path(data_root).resolve()
    members = registration["members"]
    runs = [member["run_id"] for member in members]
    attempts = [member["attempt_id"] for member in members]
    require(len(runs) >= 2 and len(set(runs)) == len(runs) and len(set(attempts)) == len(attempts),
            "complete unique member identities are required")
    require(len(set(sample_ids)) == len(sample_ids) == registration["rows_per_member"]
            and all(sid.startswith("slurp:train:") for sid in sample_ids), "complete TRAIN cohort differs")
    sources = []
    for member in members:
        run, attempt = _identity(member["run_id"]), _identity(member["attempt_id"])
        directory = root / "runs" / run / attempt
        record = _json(root / "attempts" / run / (attempt + ".json"))
        manifest_path = directory / (run + ".run-manifest.json")
        manifest = _json(manifest_path)
        jobs_path = directory / "score-jobs.jsonl"
        jobs = [json.loads(line) for line in jobs_path.read_text().splitlines() if line.strip()]
        summary_path = directory / "score-batch/batch-summary.json"
        summary = _json(summary_path)
        require(record.get("state") == "FINALIZED" and manifest.get("status") == "COMPLETED"
                and manifest.get("run_id") == run and manifest.get("attempt", {}).get("attempt_id") == attempt
                and manifest.get("study_commit") == commit
                and manifest.get("config", {}).get("config_hash") == member["config_hash"]
                and manifest.get("plan", {}).get("protocol_hash") == member["protocol_hash"]
                and manifest.get("plan", {}).get("split_role") == "discovery",
                "member operational identity or finalization differs")
        require(manifest.get("split", {}).get("count") == len(sample_ids)
                and len(manifest["split"]["ids"]) == len(sample_ids)
                and set(manifest["split"]["ids"]) == set(sample_ids), "member cohort differs")
        require(len(jobs) == 1 and jobs[0].get("job_id") == attempt
                and Path(jobs[0]["manifest"]).resolve() == manifest_path.resolve()
                and summary.get("job_count") == summary.get("succeeded") == 1
                and summary.get("failed") == 0 and summary.get("include_per_sample") is True
                and len(summary.get("jobs", [])) == 1,
                "exactly one successful complete official job and zero failures are required")
        scored = summary["jobs"][0]
        require(scored.get("job_id") == attempt and scored.get("status") == "succeeded"
                and scored.get("returncode") == 0 and scored.get("operation") == "finalize"
                and Path(scored["manifest"]).resolve() == manifest_path.resolve(),
                "official finalize job differs")
        sources.append({"manifest": manifest, "manifest_path": manifest_path, "member": dict(member),
                        "metadata_pins": [_pin(path, root) for path in (manifest_path, jobs_path, summary_path)]})
    for source in sources:
        verified = verify_bundle(source["manifest_path"])
        require(verified.attempt_state == "FINALIZED", "complete member seal verification failed")
    return sources


def context_member_identity(member):
    """Resolve exact schedule owners without aliasing another research family."""
    label = member["label"]
    placement = "before-speech-v1" if label.startswith("before-speech-") else "legacy"
    old = {f"{layout}-{scheduler}-{repeat}" for layout in ("legacy", "before-speech")
           for scheduler in ("trajectory", "role") for repeat in ("primary", "aa")}
    if label in old:
        return placement, "role" if "-role-" in label else "trajectory", "context-matrix-n20", None
    labels = [f"{layout}-{scheduler}-pair{pair}-{repeat}" for scheduler in ("trajectory", "panel")
              for layout in ("legacy", "before-speech") for pair in (1, 2) for repeat in ("primary", "aa")]
    require(label in labels, "unknown registered context matrix label")
    schedule = "panel" if "-panel-" in label else "trajectory"
    layout = "legacy" if placement == "legacy" else "before-speech"
    require(member.get("run_id") == f"SAEA-SLURP-NODE-PANEL-SCHEDULE-N20-{label.upper()}-V1"
            and member.get("layout") == layout and member.get("schedule") == schedule,
            "schedule owner or policy binding differs")
    keys = member.get("job_keys", [])
    require(len(keys) == 20 and all(isinstance(k, list) and len(k) == 2
            and isinstance(k[0], str) and k[0] and k[1] is None for k in keys)
            and len({k[0] for k in keys}) == 20, "schedule owner requires twenty distinct original jobs")
    panel = None if schedule == "trajectory" else {
        "panel_id": "SAEA-SLURP-NODE-PANEL-SCHEDULE-N20-V1", "group_index": labels.index(label) - 8,
        "group_size": 20, "max_jobs": 160, "job_keys": keys}
    return placement, schedule, "node-panel-schedule-n20", panel


def _audit_context_source(source, *, member, flight_pin, data_root, frozen_repo):
    """Render only through the shared transport; its normal identity check stays.

    The retained serving process and feature files must still be available for
    initial materialization. Preserve verified bodies in an analysis-only
    archive; subsequent reads reverify the original FIT without a live service.
    Never invoke the transport or restart a missing service for this reader.
    """
    placement, scheduler, namespace, panel_identity = context_member_identity(member)
    materialized = materialize_semantic_trajectories(source, round_id=namespace + "-root-audit-v1")
    renderer = None
    def render(raw):
        nonlocal renderer
        if renderer is None:
            pin = source.bundle.manifest["session_receipt"]
            session = SessionReceipt.from_json(json.loads(resolve_pinned_session_receipt(Path(pin["path"]), pin["sha256"])))
            values = source.composed.values
            runtime_root = model_materialization_root(values)
            require(runtime_root is not None, "context matrix requires its recorded model materialization root")
            renderer = build_configured_transport(values, Path(data_root), repo_root=Path(frozen_repo), session=session,
                runtime_receipt=load_runtime_receipt(resolve_runtime_receipt_path(Path(frozen_repo), values)),
                runtime_root=Path(runtime_root))
        return renderer.render_request(raw)
    identity = hashlib.sha256(source.bundle.manifest_path.read_bytes()).hexdigest()
    archive = Path(data_root).resolve() / "analysis" / (namespace + "-wire") / (identity + ".json")
    require(archive.resolve().is_relative_to(Path(data_root).resolve() / "analysis"),
            "context wire archive escaped analysis storage")
    prepare_actor_wire_requests(source, materialized, flight_pin, archive,
                                data_root=data_root, render_request=render)
    spec = {"artifact": _pin(archive, data_root), "flight_receipts": dict(flight_pin)}
    requests = load_actor_wire_requests(source, materialized, spec, data_root=data_root)
    result = audit_context_execution(source, materialized, flight_pin, data_root=data_root,
        render_request=lambda raw: requests[json.loads(raw)["request_id"] + "/request"],
        placement=placement, scheduler=scheduler, panel_identity=panel_identity)
    result["wire_requests"] = spec
    result.pop("content_sha256", None)
    result["content_sha256"] = content_hash(result)
    return result


def read_numeric_members(sources, *, data_root, frozen_repo):
    """Use existing complete official custody and original timing exporters.

Invoke only on all results of preflight_members after exact root READ authority.
Never return answer text or a learning-feedback object from this numeric view.
    """
    root = Path(data_root).resolve()
    members = {}
    for entry in sources:
        manifest, path = entry["manifest"], entry["manifest_path"]
        run = manifest["run_id"]
        phases = path.parent / (run + ".phases.json")
        binding = {
            "schema": "saea-system-feedback-binding-v1", "execution_profile": "model-free-check",
            "feedback_role": "construction", "scorer_id": "slurp-slu-official-train",
            "manifest": _pin(path, root), "phases": _pin(phases, root),
            "flight_receipts": _pin(path.parent / "flight-receipts.json", root),
            "score_jobs": _pin(path.parent / "score-jobs.jsonl", root),
        }
        source = verify_native_episode_source(
            manifest_path=path, expected_manifest_sha256=binding["manifest"]["sha256"],
            phase_artifact_path=phases, expected_phase_sha256=binding["phases"]["sha256"],
            repo_root=Path(frozen_repo), data_root=root,
        )
        execution = _audit_context_source(source, member=entry["member"], flight_pin=binding["flight_receipts"],
                                          data_root=root, frozen_repo=Path(frozen_repo))
        feedback = load_system_feedback(data_root=root, repo_root=Path(frozen_repo), binding=binding)
        costs = _row_cost_and_terminal(manifest)
        rows = {}
        for row in feedback["terminal_feedback"]:
            sid = row["sample_id"]
            rows[sid] = {**costs[sid], **{key: row[key] for key in ("tp", "fp", "fn")},
                         "intent": row["intent_exact"], "fallback_flags": row["fallback_flags"],
                         "format_ok": row["format_ok"]}
        require(set(rows) == set(costs) == set(source.sample_ids), "numeric views differ from complete source")
        score_pin = feedback["resolved_auxiliary_sources"]["scores"]
        score_path = root / score_pin["relpath"]
        require(_pin(score_path, root) == score_pin, "score changed during numeric read")
        score = _json(score_path)["slurp-slu-official-train"]["aggregate"]
        stage_timing = describe_stage_timing(
            json.loads(_read_pin(binding["flight_receipts"], root)),
            json.loads(_read_pin(entry["metadata_pins"][2], root)),
        )
        members[run] = {
            "rows": rows, "official": {"slu_f1": score["official"]["slu_f1"],
                                       "intent": score["port_micro"]["intent_accuracy"]},
            "sample_timing": export_system_sample_timing(source),
            "node_timing": export_system_node_timing(source),
            "context_execution": execution,
            "experiment_stage_timing": stage_timing,
            "source_bindings": binding, "metadata_pins": entry["metadata_pins"],
            "official_feedback_content_sha256": feedback["content_sha256"],
        }
    return members
