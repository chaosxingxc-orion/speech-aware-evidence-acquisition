"""Create an append-only, no-contact recovery seal for an invalid G5 flight.

This is deliberately not an alternate ``core.bundle`` finalizer.  A G5
candidate whose pre-contact :class:`ExecutionPlan` split hash disagrees with
the generic split-hash convention cannot pass ``verify_bundle`` without
rewriting the plan and its protocol binding after model contact.  That would
turn a detected integrity failure into a retrospective protocol change.

The seal instead preserves the original candidate bytes, hashes every durable
flight artifact, rechecks the locally recorded G5 geometry, and records the
precise reason that the candidate is not scoreable or formally verified.  It
does not construct a replacement run manifest, call a model, start a session,
contact a service, load a tokenizer, or invoke a scorer.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from ...contracts import ExecutionPlan, ExecutionScopeError
from ...core.config import protocol_hash
from ...core.bundle.outputs import _verify_outputs, _verify_outputs_trace_binding, _verify_raw_trace
from ...data.splits import prefixed, split_identity_hash


G5_RECOVERY_SEAL_SCHEMA = "saea-a2t-g5-fixed16-external-recovery-seal-v1"
G5_RECOVERY_SEAL_NAME = "g5-recovery-seal.json"
_NO_CONTACT_FOLLOW_UP = ("model", "network", "retriever", "scorer", "tokenizer")


class G5RecoverySealError(RuntimeError):
    """The durable flight does not support an honest G5 recovery seal."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_object(path: Path, label: str) -> Mapping[str, object]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise G5RecoverySealError(f"{label} is not a readable UTF-8 JSON object: {error}") from error
    if not isinstance(document, Mapping):
        raise G5RecoverySealError(f"{label} must be a JSON object")
    return document


def _jsonl_objects(path: Path, label: str) -> list[Mapping[str, object]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise G5RecoverySealError(f"cannot read {label}: {error}") from error
    if not lines:
        raise G5RecoverySealError(f"{label} is empty")
    rows: list[Mapping[str, object]] = []
    for number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise G5RecoverySealError(f"{label} line {number} is not JSON: {error}") from error
        if not isinstance(row, Mapping):
            raise G5RecoverySealError(f"{label} line {number} must be a JSON object")
        rows.append(row)
    return rows


def _artifact_inventory(mission_dir: Path) -> dict[str, dict[str, object]]:
    inventory: dict[str, dict[str, object]] = {}
    for path in sorted(mission_dir.rglob("*")):
        if not path.is_file() or path.name == G5_RECOVERY_SEAL_NAME:
            continue
        inventory[path.relative_to(mission_dir).as_posix()] = {
            "sha256": _sha256(path), "bytes": path.stat().st_size
        }
    return inventory


def _require_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise G5RecoverySealError(f"{label} disagrees: {actual!r} != {expected!r}")


def _validate_plan(plan_document: Mapping[str, object]) -> ExecutionPlan:
    try:
        return ExecutionPlan(**plan_document).validate()
    except (ExecutionScopeError, TypeError, ValueError) as error:
        raise G5RecoverySealError(f"execution-plan.json is not a valid ExecutionPlan: {error}") from error


def build_recovery_seal(mission_dir: Path, *, attempts_root: Path) -> dict[str, object]:
    """Write one external seal for a G5 flight that failed only at bundle bind.

    The function is intentionally write-once and writes only
    ``g5-recovery-seal.json``.  In particular, it never modifies the failed
    candidate manifest, outputs, trace, plan, or durable attempt state.
    """

    mission_dir = Path(mission_dir).resolve()
    run_dir = mission_dir / "g5"
    seal_path = mission_dir / G5_RECOVERY_SEAL_NAME
    if seal_path.exists():
        raise G5RecoverySealError(f"recovery seal already exists: {seal_path}")
    if not run_dir.is_dir():
        raise G5RecoverySealError(f"G5 run directory is absent: {run_dir}")

    plan_path = run_dir / "execution-plan.json"
    plan_document = _load_object(plan_path, "execution-plan.json")
    plan = _validate_plan(plan_document)
    run_id = plan.run_id
    attempt_id = plan.attempt_id
    if not isinstance(attempt_id, str):  # ExecutionPlan.validate makes this unreachable.
        raise G5RecoverySealError("execution plan lacks an attempt_id")

    candidate_path = run_dir / f"{run_id}.run-manifest.json"
    candidate = _load_object(candidate_path, "candidate run manifest")
    _require_equal(candidate.get("run_id"), run_id, "candidate run_id")
    _require_equal(candidate.get("plan"), plan_document, "candidate plan bytes")
    _require_equal(candidate.get("status"), "COMPLETED", "candidate status")

    split = candidate.get("split")
    if not isinstance(split, Mapping):
        raise G5RecoverySealError("candidate lacks a split block")
    ids = split.get("ids")
    carrier = split.get("carrier_lock_key")
    if not isinstance(ids, list) or not ids or not all(isinstance(item, str) and item for item in ids):
        raise G5RecoverySealError("candidate split.ids must be a nonempty list of strings")
    if ids != sorted(ids) or len(set(ids)) != len(ids):
        raise G5RecoverySealError("candidate split.ids must be sorted and unique")
    if not isinstance(carrier, str) or not carrier:
        raise G5RecoverySealError("candidate split carrier is invalid")
    _require_equal(split.get("count"), len(ids), "candidate split count")
    _require_equal(split.get("identity_hash"), plan.split_identity_hash, "candidate versus pre-contact split hash")
    generic_split_hash = split_identity_hash(prefixed(carrier, ids))
    if generic_split_hash == plan.split_identity_hash:
        raise G5RecoverySealError(
            "this candidate has no split identity mismatch; use the ordinary bundle verifier"
        )

    arm = candidate.get("arm")
    config = candidate.get("config")
    if not isinstance(arm, str) or not isinstance(config, Mapping) or not isinstance(config.get("config_hash"), str):
        raise G5RecoverySealError("candidate lacks the arm/config binding needed for protocol analysis")
    generic_protocol_hash = protocol_hash(config["config_hash"], arm, generic_split_hash)
    _require_equal(candidate.get("protocol_hash"), plan.protocol_hash, "candidate protocol hash")
    if generic_protocol_hash == plan.protocol_hash:
        raise G5RecoverySealError("generic split hash unexpectedly preserves the original protocol hash")

    outputs_meta = candidate.get("outputs")
    raw_trace_meta = candidate.get("raw_trace")
    trace_manifest_meta = candidate.get("trace_manifest")
    if not all(isinstance(item, Mapping) for item in (outputs_meta, raw_trace_meta, trace_manifest_meta)):
        raise G5RecoverySealError("candidate lacks output-trace artifact bindings")
    outputs_path = Path(str(outputs_meta["path"]))
    raw_trace_path = Path(str(raw_trace_meta["path"]))
    trace_manifest_path = Path(str(trace_manifest_meta["path"]))
    for path, meta, label in (
        (outputs_path, outputs_meta, "outputs"),
        (raw_trace_path, raw_trace_meta, "output trace"),
        (trace_manifest_path, trace_manifest_meta, "output trace manifest"),
    ):
        if not path.is_file() or _sha256(path) != meta.get("sha256"):
            raise G5RecoverySealError(f"candidate {label} bytes no longer match its original hash")
    outputs_rows = _verify_outputs(outputs_path.read_bytes(), frozenset(ids), carrier, arm)
    output_trace = _verify_raw_trace(raw_trace_path.read_bytes(), trace_manifest_path.read_bytes())
    _verify_outputs_trace_binding(outputs_rows, output_trace)

    agent_trace_path = run_dir / "agent-trace" / f"{run_id}.trace.jsonl"
    agent_manifest_path = run_dir / "agent-trace" / f"{run_id}.trace-manifest.json"
    agent_trace = _verify_raw_trace(agent_trace_path.read_bytes(), agent_manifest_path.read_bytes())
    model_requests = [
        record_id for record_id, payload in agent_trace.items()
        if record_id.endswith("/request") and payload.get("arm") == arm and isinstance(payload.get("payload"), Mapping)
    ]
    model_responses = [record_id for record_id in agent_trace if record_id.endswith("/response") and record_id.split("/", 1)[0] + "/request" in agent_trace]
    _require_equal(len(model_requests), plan.planned_model_calls, "agent-trace model request count")
    _require_equal(len(model_responses), plan.planned_model_calls, "agent-trace model response count")

    for row in outputs_rows:
        source = row.get("composite_source")
        if not isinstance(source, Mapping):
            raise G5RecoverySealError("G5 output lacks its agent-trace composite source")
        _require_equal(source.get("source_artifact_sha256"), _sha256(agent_trace_path), "output source agent trace hash")
        _require_equal(source.get("source_agent_trace_manifest_sha256"), _sha256(agent_manifest_path), "output source agent trace manifest hash")

    states_path = run_dir / "g5-plan-states.jsonl"
    states = _jsonl_objects(states_path, "G5 plan states")
    if len(states) != len(ids) or {row.get("sample_id") for row in states} != set(ids):
        raise G5RecoverySealError("G5 plan states do not cover the candidate split exactly once")
    if any(row.get("contact_id") != "g5-plan" or row.get("nonfinal") is not True for row in states):
        raise G5RecoverySealError("G5 plan states are not all nonfinal g5-plan records")

    attempt_path = Path(attempts_root) / run_id / f"{attempt_id}.json"
    attempt = _load_object(attempt_path, "durable attempt state")
    _require_equal(attempt.get("run_id"), run_id, "attempt run_id")
    _require_equal(attempt.get("attempt_id"), attempt_id, "attempt id")
    _require_equal(attempt.get("state"), "ABORTED", "attempt state")
    actual = attempt.get("actual")
    if not isinstance(actual, Mapping):
        raise G5RecoverySealError("attempt lacks actual usage")
    _require_equal(actual.get("calls"), plan.planned_model_calls, "attempt calls")

    failure = _load_object(mission_dir / "failure-receipt.json", "failure receipt")
    _require_equal(failure.get("run_id"), run_id, "failure receipt run_id")
    _require_equal(failure.get("attempt_id"), attempt_id, "failure receipt attempt_id")
    error = failure.get("error")
    if not isinstance(error, str) or generic_split_hash[:12] not in error or plan.split_identity_hash[:12] not in error:
        raise G5RecoverySealError("failure receipt does not attest the observed split hash mismatch")

    document: dict[str, object] = {
        "schema": G5_RECOVERY_SEAL_SCHEMA,
        "status": "EXTERNALLY_SEALED_UNVERIFIABLE",
        "run_id": run_id,
        "attempt_id": attempt_id,
        "candidate_manifest": {"path": str(candidate_path), "sha256": _sha256(candidate_path)},
        "original_execution_plan": {"path": str(plan_path), "sha256": _sha256(plan_path), "split_identity_hash": plan.split_identity_hash, "protocol_hash": plan.protocol_hash},
        "generic_recomputation": {"split_identity_hash": generic_split_hash, "protocol_hash": generic_protocol_hash},
        "formal_verify_bundle": {
            "achievable": False,
            "reasons": ["split_identity_hash_mismatch", "attempt_aborted"],
            "required_retrospective_changes": ["execution_plan.split_identity_hash", "execution_plan.protocol_hash", "candidate manifest identity fields", "durable attempt terminal state"],
        },
        "attempt": {"path": str(attempt_path), "sha256": _sha256(attempt_path), "state": "ABORTED", "actual": dict(actual)},
        "observed": {"final_outputs": len(outputs_rows), "plan_states": len(states), "model_contacts": len(model_requests), "model_responses": len(model_responses)},
        "prohibited_follow_up": list(_NO_CONTACT_FOLLOW_UP),
        "artifacts": _artifact_inventory(mission_dir),
    }
    try:
        with seal_path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(document, handle, ensure_ascii=True, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as error:
        raise G5RecoverySealError(f"recovery seal already exists: {seal_path}") from error
    return document
