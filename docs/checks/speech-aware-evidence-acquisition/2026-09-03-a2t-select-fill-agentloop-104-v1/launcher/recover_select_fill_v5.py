#!/usr/bin/env python3
"""Seal the completed V5 SELECT/FILL flight without making new contacts.

The committed recovery plan supplies every source-artifact digest. This
program verifies those immutable bytes, mechanically derives score-ready
rows from transport records, and writes successor bundles in a new external
directory. It never starts a service, contacts a model, embeds text, opens
gold, or invokes a scorer.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Mapping, Sequence


REPO = Path(__file__).resolve().parents[5]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    ExecutionPlan,
    TraceRecord,
)
from speech_aware_evidence_acquisition.core.base import RunResult  # noqa: E402
from speech_aware_evidence_acquisition.core.bundle import (  # noqa: E402
    STATUS_COMPLETED,
    build_manifest,
    require_clean_study_repo,
    verify_bundle,
)
from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.split_receipt import (  # noqa: E402
    VerifiedSplit,
)
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    split_identity_hash,
)


PLAN_SCHEMA = "saea-a2t-select-fill-zero-contact-seal-recovery-plan-v1"
RECEIPT_SCHEMA = "saea-a2t-select-fill-zero-contact-seal-recovery-receipt-v1"
SOURCE_SEAL_SCHEMA = "saea-a2t-select-fill-zero-contact-source-seal-v1"
ARM = "speech-feature-query"
PHASE_ORDER = (
    "JOINT_ONE_CALL",
    "SELECT",
    "JOINT_DRAFT_REVISE",
    "FILL",
)
PHASE_ROLES = {
    "JOINT_ONE_CALL": ("joint_one_call", True, None),
    "SELECT": ("diagnostic_select", False, None),
    "JOINT_DRAFT_REVISE": (
        "joint_draft_revise",
        True,
        "JOINT_ONE_CALL",
    ),
    "FILL": ("select_then_fill", True, "SELECT"),
}
SERVICE_KINDS = frozenset(
    {
        "embedding_session",
        "embedding_stop",
        "generation_session",
        "generation_stop",
    }
)
CONFIG_FRAGMENTS = {
    "model": "q4km-mmproj-free-speech-native-np2-a2t-select-fill-max1024",
    "dataset": "audio2tool-semantic-agentloop-select-fill-104-v1",
    "baseline": "a2t-semantic-agentloop-select-fill-top32",
    "experiment": "a2t-semantic-agentloop-select-fill-104-v1",
}
_SHA256 = frozenset("0123456789abcdef")


class RecoveryError(RuntimeError):
    """The recovery plan, immutable source, or successor failed closed."""


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _SHA256


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RecoveryError(f"{label} is not readable UTF-8 JSON: {error}") from error
    if not isinstance(value, dict):
        raise RecoveryError(f"{label} must be a JSON object")
    return value


def _read_jsonl(path: Path, label: str) -> tuple[dict[str, object], ...]:
    try:
        raw = Path(path).read_bytes()
    except OSError as error:
        raise RecoveryError(f"{label} is unreadable: {error}") from error
    if not raw or not raw.endswith(b"\n"):
        raise RecoveryError(f"{label} must be non-empty and end with LF")
    rows: list[dict[str, object]] = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        try:
            value = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RecoveryError(
                f"{label} line {line_number} is not UTF-8 JSON"
            ) from error
        if not isinstance(value, dict):
            raise RecoveryError(f"{label} line {line_number} is not an object")
        rows.append(value)
    return tuple(rows)


def _write_json_exclusive(path: Path, value: object) -> None:
    raw = json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="ascii", newline="\n") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def _write_jsonl_exclusive(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    raw = "".join(
        json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="ascii", newline="\n") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def _artifact(path: Path) -> dict[str, object]:
    path = Path(path).resolve()
    return {"path": str(path), "sha256": _sha256(path), "bytes": path.stat().st_size}


def _require_exact_keys(
    value: Mapping[str, object], expected: set[str], label: str
) -> None:
    if set(value) != expected:
        raise RecoveryError(f"{label} key set drift")


def _artifact_spec(value: object, label: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise RecoveryError(f"{label} must be an artifact object")
    _require_exact_keys(value, {"relpath", "sha256"}, label)
    relpath = value.get("relpath")
    digest = value.get("sha256")
    if (
        not isinstance(relpath, str)
        or not relpath
        or Path(relpath).is_absolute()
        or "\\" in relpath
        or any(part in {"", ".", ".."} for part in relpath.split("/"))
        or not _is_sha256(digest)
    ):
        raise RecoveryError(f"{label} artifact identity is malformed")
    return {"relpath": relpath, "sha256": str(digest)}


def _path_spec(value: object, label: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise RecoveryError(f"{label} must be a path artifact object")
    _require_exact_keys(value, {"path", "sha256"}, label)
    path = value.get("path")
    digest = value.get("sha256")
    if not isinstance(path, str) or not path or not _is_sha256(digest):
        raise RecoveryError(f"{label} artifact identity is malformed")
    return {"path": path, "sha256": str(digest)}


def _trace_spec(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise RecoveryError(f"{label} must be a trace artifact object")
    _require_exact_keys(value, {"relpath", "sha256", "records"}, label)
    artifact = _artifact_spec(
        {"relpath": value.get("relpath"), "sha256": value.get("sha256")},
        label,
    )
    records = value.get("records")
    if isinstance(records, bool) or not isinstance(records, int) or records <= 0:
        raise RecoveryError(f"{label} record count is malformed")
    return {**artifact, "records": records}


def _confined(root: Path, relpath: str, label: str) -> Path:
    root = Path(root).resolve()
    target = (root / relpath).resolve()
    if target == root or root not in target.parents:
        raise RecoveryError(f"{label} escapes its configured root")
    return target


def _require_hash(path: Path, expected: object, label: str) -> Path:
    if not _is_sha256(expected):
        raise RecoveryError(f"{label} expected SHA-256 is malformed")
    path = Path(path)
    if not path.is_file() or _sha256(path) != expected:
        raise RecoveryError(f"{label} SHA-256 drift")
    return path


def _git_blob_sha256(commit: str, relpath: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relpath}"],
        cwd=REPO,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RecoveryError(f"cannot read authorized code blob {relpath!r}")
    return hashlib.sha256(result.stdout).hexdigest()


def _validate_plan(plan: Mapping[str, object], *, data_root: Path) -> None:
    required = {
        "schema",
        "status",
        "run_id",
        "source_mission",
        "recovery_target_dirname",
        "expected",
        "authority",
        "source",
    }
    _require_exact_keys(plan, required, "recovery plan")
    if plan.get("schema") != PLAN_SCHEMA or plan.get("status") != "RECOVERY_AUTHORIZED":
        raise RecoveryError("recovery plan is not authorized")
    run_id = plan.get("run_id")
    mission = plan.get("source_mission")
    target = plan.get("recovery_target_dirname")
    if (
        not isinstance(run_id, str)
        or not run_id
        or not isinstance(mission, str)
        or not Path(mission).is_absolute()
        or not isinstance(target, str)
        or not target
        or "/" in target
        or "\\" in target
        or target in {".", ".."}
    ):
        raise RecoveryError("recovery plan path or run identity is malformed")
    mission_path = Path(mission).resolve()
    runs_root = (Path(data_root).resolve() / "runs").resolve()
    if runs_root not in mission_path.parents or not mission_path.is_dir():
        raise RecoveryError("source mission is not an existing data-root run")

    expected = plan.get("expected")
    if not isinstance(expected, Mapping):
        raise RecoveryError("recovery expected accounting is missing")
    _require_exact_keys(
        expected,
        {
            "sample_count",
            "generation_contacts",
            "phase_contacts",
            "embedding_logical_items",
            "embedding_physical_requests",
            "attempt_audio_seconds",
        },
        "recovery expected accounting",
    )
    sample_count = expected.get("sample_count")
    phase_contacts = expected.get("phase_contacts")
    generation_contacts = expected.get("generation_contacts")
    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or sample_count <= 0
        or phase_contacts != sample_count
        or generation_contacts != sample_count * len(PHASE_ORDER)
        or expected.get("embedding_logical_items") != sample_count
        or expected.get("embedding_physical_requests") != 4
        or isinstance(expected.get("attempt_audio_seconds"), bool)
        or not isinstance(expected.get("attempt_audio_seconds"), (int, float))
        or not math.isfinite(float(expected["attempt_audio_seconds"]))
        or float(expected["attempt_audio_seconds"]) <= 0
    ):
        raise RecoveryError("recovery expected accounting is inconsistent")


def _validate_authority(
    plan: Mapping[str, object], *, plan_path: Path
) -> dict[str, object]:
    authority_spec = plan.get("authority")
    if not isinstance(authority_spec, Mapping):
        raise RecoveryError("recovery authority specification is missing")
    _require_exact_keys(
        authority_spec,
        {
            "path",
            "sha256",
            "implementation_commit",
            "preregistration",
            "code",
        },
        "recovery authority specification",
    )
    authority_path_spec = _path_spec(
        {"path": authority_spec.get("path"), "sha256": authority_spec.get("sha256")},
        "execution authority",
    )
    authority_path = _confined(REPO, authority_path_spec["path"], "execution authority")
    _require_hash(authority_path, authority_path_spec["sha256"], "execution authority")
    authority = _read_object(authority_path, "execution authority")
    commit = authority_spec.get("implementation_commit")
    if (
        not isinstance(commit, str)
        or len(commit) != 40
        or set(commit) - _SHA256
        or authority.get("implementation_commit") != commit
        or authority.get("run_id") != plan.get("run_id")
        or authority.get("status") != "CONTACT_AUTHORIZED"
    ):
        raise RecoveryError("execution authority identity drift")

    prereg = _path_spec(authority_spec.get("preregistration"), "preregistration")
    prereg_path = _confined(REPO, prereg["path"], "preregistration")
    _require_hash(prereg_path, prereg["sha256"], "preregistration")
    hashes = authority.get("hashes")
    if (
        not isinstance(hashes, Mapping)
        or hashes.get("exposure_preregistration_sha256") != prereg["sha256"]
    ):
        raise RecoveryError("authority preregistration binding drift")
    code = authority_spec.get("code")
    if not isinstance(code, list) or len(code) != 2:
        raise RecoveryError("authority must bind exactly two flight code files")
    code_by_path: dict[str, str] = {}
    for index, raw in enumerate(code):
        spec = _path_spec(raw, f"authorized code {index}")
        if Path(spec["path"]).is_absolute() or spec["path"] in code_by_path:
            raise RecoveryError("authorized code paths are malformed or duplicate")
        if _git_blob_sha256(commit, spec["path"]) != spec["sha256"]:
            raise RecoveryError(f"authorized code blob {spec['path']!r} SHA-256 drift")
        code_by_path[spec["path"]] = spec["sha256"]
    if set(code_by_path.values()) != {
        hashes.get("coordinator_launcher_sha256"),
        hashes.get("local_runtime_factory_sha256"),
    }:
        raise RecoveryError("authority code hash binding drift")

    try:
        relative_plan = Path(plan_path).resolve().relative_to(REPO).as_posix()
    except ValueError as error:
        raise RecoveryError("recovery plan must be inside the study repository") from error
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative_plan],
        cwd=REPO,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if tracked.returncode != 0:
        raise RecoveryError("recovery plan must be committed before use")
    return authority


def _phase_specs(source: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    phases = source.get("phases")
    if not isinstance(phases, list) or len(phases) != len(PHASE_ORDER):
        raise RecoveryError("source phase plan must contain exactly four phases")
    result: dict[str, Mapping[str, object]] = {}
    for item in phases:
        if not isinstance(item, Mapping):
            raise RecoveryError("source phase plan entry must be an object")
        _require_exact_keys(
            item,
            {
                "phase",
                "role",
                "score_ready",
                "source_dir",
                "attempt",
                "trace",
                "source_trace_manifest",
                "preflight",
                "predecessor_phase",
            },
            "source phase plan entry",
        )
        phase = item.get("phase")
        if not isinstance(phase, str) or phase in result:
            raise RecoveryError("source phase identities are malformed or duplicate")
        expected_role, expected_score_ready, expected_predecessor = PHASE_ROLES.get(
            phase, (None, None, None)
        )
        if (
            item.get("role") != expected_role
            or item.get("score_ready") is not expected_score_ready
            or item.get("predecessor_phase") != expected_predecessor
            or not isinstance(item.get("source_dir"), str)
            or not item.get("source_dir")
        ):
            raise RecoveryError(f"source phase {phase!r} role or lineage drift")
        result[phase] = item
    if tuple(result) != PHASE_ORDER:
        raise RecoveryError("source phase order drift")
    return result


def _validate_send_accounting(
    rows: Sequence[Mapping[str, object]],
    *,
    phases: Sequence[str],
    sample_ids: Sequence[str],
) -> None:
    expected_pairs = {(phase, sample_id) for phase in phases for sample_id in sample_ids}
    actual_pairs: set[tuple[str, str]] = set()
    for row in rows:
        phase = row.get("phase")
        sample_id = row.get("sample_id")
        pair = (phase, sample_id)
        if (
            not isinstance(phase, str)
            or not isinstance(sample_id, str)
            or pair in actual_pairs
            or row.get("status") != "CONSUMED_BEFORE_IO"
            or not _is_sha256(row.get("body_sha256"))
        ):
            raise RecoveryError("generation send accounting row drift")
        actual_pairs.add(pair)
    if actual_pairs != expected_pairs or len(rows) != len(expected_pairs):
        raise RecoveryError("generation send accounting is not the exact phase/sample cross-product")


def _derive_trace_material(
    documents: Sequence[Mapping[str, object]],
    *,
    phase: str,
    sample_ids: Sequence[str],
) -> tuple[tuple[dict[str, object], ...], dict[str, object], dict[str, str]]:
    """Derive output rows and cost without interpreting response meaning."""

    channels: dict[str, dict[str, Mapping[str, object]]] = {
        "MODEL_REQUEST": {},
        "MODEL_RESPONSE": {},
        "COST": {},
    }
    suffixes = {
        "MODEL_REQUEST": "/request",
        "MODEL_RESPONSE": "/response",
        "COST": "/cost",
    }
    counts: Counter[str] = Counter()
    record_hashes: dict[str, str] = {}
    for document in documents:
        channel = document.get("channel")
        record_id = document.get("record_id")
        payload = document.get("payload")
        if (
            not isinstance(channel, str)
            or not isinstance(record_id, str)
            or not isinstance(payload, Mapping)
            or record_id in record_hashes
        ):
            raise RecoveryError(f"{phase} trace record is malformed or duplicate")
        record_hashes[record_id] = TraceRecord(
            channel, record_id, payload
        ).content_hash()
        counts[channel] += 1
        if channel not in channels:
            continue
        suffix = suffixes[channel]
        if not record_id.endswith(suffix):
            raise RecoveryError(f"{phase} transport trace suffix drift")
        request_id = record_id[: -len(suffix)]
        if not request_id or request_id in channels[channel]:
            raise RecoveryError(f"{phase} transport request identity drift")
        channels[channel][request_id] = payload

    expected_count = len(sample_ids)
    if any(counts[channel] != expected_count for channel in channels):
        raise RecoveryError(f"{phase} transport channel counts drift")
    requests = channels["MODEL_REQUEST"]
    responses = channels["MODEL_RESPONSE"]
    costs = channels["COST"]
    if set(requests) != set(responses) or set(requests) != set(costs):
        raise RecoveryError(f"{phase} request/response/cost identities differ")

    request_by_sample: dict[str, str] = {}
    for request_id, request in requests.items():
        inner = request.get("payload")
        sample_id = inner.get("sample_id") if isinstance(inner, Mapping) else None
        if (
            not isinstance(sample_id, str)
            or sample_id in request_by_sample
            or request.get("arm") != ARM
            or request.get("payload_sha256") != _canonical_sha256(inner)
        ):
            raise RecoveryError(f"{phase} request payload identity drift")
        request_by_sample[sample_id] = request_id
    if set(request_by_sample) != set(sample_ids):
        raise RecoveryError(f"{phase} trace sample set drift")

    totals: dict[str, object] = {
        "calls_used": 0,
        "audio_seconds_used": 0.0,
        "latency_seconds_total": 0.0,
        "prompt_tokens_total": 0,
        "completion_tokens_total": 0,
        "tool_calls": 0,
    }
    rows: list[dict[str, object]] = []
    for sample_id in sample_ids:
        request_id = request_by_sample[sample_id]
        request = requests[request_id]
        response = responses[request_id]
        text = response.get("text")
        if not isinstance(text, str) or not text.isascii():
            raise RecoveryError(f"{phase}/{sample_id} response is not ASCII text")
        text_hash = hashlib.sha256(text.encode("ascii")).hexdigest()
        if response.get("response_text_sha256") != text_hash:
            raise RecoveryError(f"{phase}/{sample_id} response text hash drift")
        if not _is_sha256(response.get("response_sha256")):
            raise RecoveryError(f"{phase}/{sample_id} response hash is malformed")
        rows.append(
            {
                "request_id": request_id,
                "sample_id": sample_id,
                "carrier_lock_key": "audio2tool",
                "arm": ARM,
                "text": text,
                "admitted": True,
                "request_sha256": request["payload_sha256"],
                "response_sha256": response["response_sha256"],
                "response_text_sha256": text_hash,
                "phase": phase,
            }
        )
        cost = costs[request_id]
        for key in (
            "calls",
            "audio_seconds",
            "latency_seconds",
            "prompt_tokens",
            "completion_tokens",
        ):
            value = cost.get(key)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or value < 0
            ):
                raise RecoveryError(f"{phase} cost field {key!r} is invalid")
        if cost["calls"] != 1:
            raise RecoveryError(f"{phase} cost is not one call per sample")
        totals["calls_used"] = int(totals["calls_used"]) + 1
        totals["audio_seconds_used"] = float(totals["audio_seconds_used"]) + float(
            cost["audio_seconds"]
        )
        totals["latency_seconds_total"] = float(
            totals["latency_seconds_total"]
        ) + float(cost["latency_seconds"])
        totals["prompt_tokens_total"] = int(totals["prompt_tokens_total"]) + int(
            cost["prompt_tokens"]
        )
        totals["completion_tokens_total"] = int(
            totals["completion_tokens_total"]
        ) + int(cost["completion_tokens"])
    return tuple(rows), totals, record_hashes


def _validate_attempt(
    document: Mapping[str, object],
    *,
    run_id: str,
    attempt_id: str,
    state: str,
    calls: int,
    audio_seconds: float,
) -> None:
    actual = document.get("actual")
    if (
        document.get("run_id") != run_id
        or document.get("attempt_id") != attempt_id
        or document.get("state") != state
        or not isinstance(actual, Mapping)
        or actual.get("calls") != calls
        or abs(float(actual.get("audio_seconds", -1)) - audio_seconds) > 1e-9
    ):
        raise RecoveryError(f"attempt {attempt_id!r} terminal accounting drift")


def _candidate_rows(
    checkpoint: Mapping[str, object], sample_count: int
) -> tuple[tuple[str, ...], dict[str, Mapping[str, object]]]:
    rows = checkpoint.get("rows")
    if (
        checkpoint.get("count") != sample_count
        or not isinstance(rows, list)
        or len(rows) != sample_count
    ):
        raise RecoveryError("candidate checkpoint count drift")
    by_sample: dict[str, Mapping[str, object]] = {}
    for row in rows:
        sample_id = row.get("sample_id") if isinstance(row, Mapping) else None
        names = row.get("candidate_tool_names") if isinstance(row, Mapping) else None
        scores = row.get("candidate_scores") if isinstance(row, Mapping) else None
        if (
            not isinstance(sample_id, str)
            or sample_id in by_sample
            or not isinstance(names, list)
            or len(names) != 32
            or len(set(names)) != 32
            or not all(isinstance(name, str) and name.isascii() for name in names)
            or not isinstance(scores, list)
            or len(scores) != 32
            or not _is_sha256(row.get("candidate_set_sha256"))
            or not _is_sha256(row.get("candidate_query_state_sha256"))
            or not _is_sha256(row.get("observation_state_sha256"))
            or row.get("candidate_set_sha256")
            != _canonical_sha256(
                {
                    "sample_id": sample_id,
                    "tool_names": names,
                    "scores": scores,
                    "query_state_sha256": row.get("candidate_query_state_sha256"),
                }
            )
        ):
            raise RecoveryError("candidate checkpoint row drift")
        by_sample[sample_id] = row
    return tuple(by_sample), by_sample


def _source_paths_and_seal(
    plan: Mapping[str, object], *, data_root: Path
) -> tuple[dict[str, Path], dict[str, object]]:
    mission = Path(str(plan["source_mission"])).resolve()
    source = plan.get("source")
    if not isinstance(source, Mapping):
        raise RecoveryError("source artifact plan is missing")
    _require_exact_keys(
        source,
        {
            "authority_binding",
            "failure_receipt",
            "send_accounting",
            "checkpoint",
            "checkpoint_receipt",
            "embedding_tool_receipt",
            "embedding_attempt",
            "service_receipts",
            "phases",
            "recovered_direct_bundle",
        },
        "source artifact plan",
    )
    paths: dict[str, Path] = {}
    seal: dict[str, object] = {}
    for key in (
        "authority_binding",
        "failure_receipt",
        "send_accounting",
        "checkpoint",
        "checkpoint_receipt",
        "embedding_tool_receipt",
    ):
        spec = _artifact_spec(source.get(key), f"source {key}")
        path = _confined(mission, spec["relpath"], f"source {key}")
        _require_hash(path, spec["sha256"], f"source {key}")
        paths[key] = path
        seal[key] = _artifact(path)

    embedding_attempt = _path_spec(source.get("embedding_attempt"), "embedding attempt")
    embedding_attempt_path = _confined(
        data_root, embedding_attempt["path"], "embedding attempt"
    )
    _require_hash(
        embedding_attempt_path, embedding_attempt["sha256"], "embedding attempt"
    )
    paths["embedding_attempt"] = embedding_attempt_path
    seal["embedding_attempt"] = _artifact(embedding_attempt_path)

    services = source.get("service_receipts")
    if not isinstance(services, list) or len(services) != len(SERVICE_KINDS):
        raise RecoveryError("source service receipt set is incomplete")
    service_by_kind: dict[str, Path] = {}
    for raw in services:
        if not isinstance(raw, Mapping):
            raise RecoveryError("source service receipt entry must be an object")
        _require_exact_keys(raw, {"kind", "relpath", "sha256"}, "service receipt")
        kind = raw.get("kind")
        if not isinstance(kind, str) or kind in service_by_kind:
            raise RecoveryError("source service receipt kind is malformed or duplicate")
        spec = _artifact_spec(
            {"relpath": raw.get("relpath"), "sha256": raw.get("sha256")},
            f"service receipt {kind}",
        )
        path = _confined(mission, spec["relpath"], f"service receipt {kind}")
        _require_hash(path, spec["sha256"], f"service receipt {kind}")
        service_by_kind[kind] = path
        seal[f"service:{kind}"] = _artifact(path)
    if set(service_by_kind) != SERVICE_KINDS:
        raise RecoveryError("source service receipt kinds drift")
    paths.update({f"service:{key}": value for key, value in service_by_kind.items()})

    for phase, phase_spec in _phase_specs(source).items():
        for field in ("trace", "preflight"):
            spec = (
                _trace_spec(phase_spec.get(field), f"{phase} {field}")
                if field == "trace"
                else _artifact_spec(phase_spec.get(field), f"{phase} {field}")
            )
            path = _confined(mission, spec["relpath"], f"{phase} {field}")
            _require_hash(path, spec["sha256"], f"{phase} {field}")
            paths[f"{phase}:{field}"] = path
            seal[f"{phase}:{field}"] = _artifact(path)
        trace_manifest_raw = phase_spec.get("source_trace_manifest")
        if trace_manifest_raw is not None:
            spec = _artifact_spec(trace_manifest_raw, f"{phase} source trace manifest")
            path = _confined(
                mission, spec["relpath"], f"{phase} source trace manifest"
            )
            _require_hash(path, spec["sha256"], f"{phase} source trace manifest")
            paths[f"{phase}:source_trace_manifest"] = path
            seal[f"{phase}:source_trace_manifest"] = _artifact(path)
        attempt = _path_spec(phase_spec.get("attempt"), f"{phase} attempt")
        attempt_path = _confined(data_root, attempt["path"], f"{phase} attempt")
        _require_hash(attempt_path, attempt["sha256"], f"{phase} attempt")
        paths[f"{phase}:attempt"] = attempt_path
        seal[f"{phase}:attempt"] = _artifact(attempt_path)

    direct = source.get("recovered_direct_bundle")
    if not isinstance(direct, Mapping):
        raise RecoveryError("recovered direct bundle plan is missing")
    _require_exact_keys(
        direct,
        {"manifest", "outputs", "trace", "trace_manifest"},
        "recovered direct bundle",
    )
    for field in ("manifest", "outputs", "trace", "trace_manifest"):
        spec = _artifact_spec(direct.get(field), f"recovered direct {field}")
        path = _confined(mission, spec["relpath"], f"recovered direct {field}")
        _require_hash(path, spec["sha256"], f"recovered direct {field}")
        paths[f"direct:{field}"] = path
        seal[f"direct:{field}"] = _artifact(path)
    return paths, {
        "schema": SOURCE_SEAL_SCHEMA,
        "run_id": plan["run_id"],
        "mission": str(mission),
        "artifacts": seal,
    }


def _validate_source(
    plan: Mapping[str, object],
    authority: Mapping[str, object],
    *,
    data_root: Path,
) -> tuple[
    dict[str, Path],
    dict[str, object],
    tuple[str, ...],
    dict[str, Mapping[str, object]],
    dict[str, tuple[dict[str, object], ...]],
    dict[str, tuple[dict[str, object], ...]],
]:
    paths, seal = _source_paths_and_seal(plan, data_root=data_root)
    expected = plan["expected"]
    assert isinstance(expected, Mapping)
    sample_count = int(expected["sample_count"])
    run_id = str(plan["run_id"])

    failure = _read_object(paths["failure_receipt"], "source failure receipt")
    if (
        failure.get("status") != "ABORTED"
        or "FileNotFoundError" not in str(failure.get("reason", ""))
    ):
        raise RecoveryError("source failure is not the registered missing trace refusal")
    binding = _read_object(paths["authority_binding"], "source authority binding")
    if binding.get("authority_sha256") != _canonical_sha256(authority):
        raise RecoveryError("source authority binding digest drift")
    plans = binding.get("contact_plans")
    authority_plans = authority.get("execution_plans")
    if not isinstance(plans, Mapping) or not isinstance(authority_plans, Mapping):
        raise RecoveryError("source authority plan set is missing")
    bound_plans = {
        phase: {
            key: value
            for key, value in authority_plans[phase].items()
            if key != "exposure_preregistration_sha256"
        }
        for phase in PHASE_ORDER
        if isinstance(authority_plans.get(phase), Mapping)
    }
    authority_embedding = authority.get("embedding_execution_plan")
    bound_embedding = (
        {
            key: value
            for key, value in authority_embedding.items()
            if key != "exposure_preregistration_sha256"
        }
        if isinstance(authority_embedding, Mapping)
        else None
    )
    protocol_config = binding.get("protocol_config")
    local_runtime = authority.get("local_runtime")
    if (
        plans != bound_plans
        or binding.get("embedding_plan") != bound_embedding
        or not isinstance(protocol_config, Mapping)
        or protocol_config.get("run_id") != plan.get("run_id")
        or protocol_config.get("generation_contacts")
        != expected["generation_contacts"]
        or protocol_config.get("generation_phases") != list(PHASE_ORDER)
        or not isinstance(local_runtime, Mapping)
        or binding.get("recovery_source") != local_runtime.get("recovery_source")
        or binding.get("bundle_split_identity_sha256")
        != authority.get("bundle_split_identity_hash")
        or binding.get("bundle_protocol_sha256")
        != authority.get("bundle_protocol_sha256")
    ):
        raise RecoveryError("source authority binding material drift")

    checkpoint_receipt = _read_object(
        paths["checkpoint_receipt"], "candidate checkpoint receipt"
    )
    if (
        checkpoint_receipt.get("checkpoint_sha256") != _sha256(paths["checkpoint"])
        or checkpoint_receipt.get("count") != sample_count
        or checkpoint_receipt.get("top_k") != 32
    ):
        raise RecoveryError("candidate checkpoint receipt drift")
    checkpoint = _read_object(paths["checkpoint"], "candidate checkpoint")
    if checkpoint.get("source_report_sha256") != binding.get(
        "recovered_prefix_sha256"
    ):
        raise RecoveryError("candidate checkpoint recovered-prefix binding drift")
    sample_ids, candidates = _candidate_rows(checkpoint, sample_count)

    send_rows = _read_jsonl(paths["send_accounting"], "generation send accounting")
    _validate_send_accounting(send_rows, phases=PHASE_ORDER, sample_ids=sample_ids)
    send_by_phase_sample = {
        (str(row["phase"]), str(row["sample_id"])): row["body_sha256"]
        for row in send_rows
    }

    phase_documents: dict[str, tuple[dict[str, object], ...]] = {}
    outputs: dict[str, tuple[dict[str, object], ...]] = {}
    source = plan["source"]
    assert isinstance(source, Mapping)
    phase_specs = _phase_specs(source)
    for phase in PHASE_ORDER:
        phase_spec = phase_specs[phase]
        preflight = _read_object(paths[f"{phase}:preflight"], f"{phase} preflight")
        if (
            preflight.get("phase") != phase
            or preflight.get("status") != "COMPLETE_NO_GENERATION_SENT"
            or preflight.get("sample_ids") != list(sample_ids)
            or not isinstance(preflight.get("audits"), list)
            or len(preflight["audits"]) != sample_count
        ):
            raise RecoveryError(f"{phase} preflight completeness drift")
        allowlists = preflight.get("allowed_body_hashes_by_slot")
        if (
            not isinstance(allowlists, list)
            or len(allowlists) != 2
            or any(not isinstance(slot, list) or len(slot) != sample_count for slot in allowlists)
            or any(
                not _is_sha256(body_hash)
                for slot in allowlists
                for body_hash in slot
            )
            or any(
                send_by_phase_sample[(phase, sample_id)]
                not in {allowlists[0][index], allowlists[1][index]}
                for index, sample_id in enumerate(sample_ids)
            )
        ):
            raise RecoveryError(f"{phase} send is outside its preflight allowlist")
        trace_spec = phase_spec["trace"]
        assert isinstance(trace_spec, Mapping)
        documents = _read_jsonl(paths[f"{phase}:trace"], f"{phase} trace")
        if trace_spec.get("records") != len(documents):
            raise RecoveryError(f"{phase} source trace record count drift")
        channel_counts = Counter(str(row.get("channel")) for row in documents)
        if channel_counts != Counter(
            {
                "MODEL_REQUEST": sample_count,
                "MODEL_RESPONSE": sample_count,
                "COST": sample_count,
                "ORG": sample_count,
                "SUPPLY": sample_count,
                "USE": sample_count * 2,
            }
        ):
            raise RecoveryError(f"{phase} full AgentLoop channel counts drift")
        rows, cost, record_hashes = _derive_trace_material(
            documents, phase=phase, sample_ids=sample_ids
        )
        source_trace_manifest_path = paths.get(f"{phase}:source_trace_manifest")
        if source_trace_manifest_path is not None:
            trace_manifest = _read_object(
                source_trace_manifest_path, f"{phase} source trace manifest"
            )
            if (
                trace_manifest.get("run_id") != run_id
                or trace_manifest.get("records") != record_hashes
            ):
                raise RecoveryError(f"{phase} source trace manifest content drift")
        if (
            cost["calls_used"] != sample_count
            or abs(
                float(cost["audio_seconds_used"])
                - float(expected["attempt_audio_seconds"])
            )
            > 1e-6
        ):
            raise RecoveryError(f"{phase} transport cost accounting drift")
        phase_documents[phase] = documents
        outputs[phase] = rows

        attempt_id = phase_spec["attempt"]["path"]  # type: ignore[index]
        attempt = _read_object(paths[f"{phase}:attempt"], f"{phase} attempt")
        authority_phase = authority_plans.get(phase)
        bound_phase = plans.get(phase)
        if (
            not isinstance(authority_phase, Mapping)
            or not isinstance(bound_phase, Mapping)
            or authority_phase.get("attempt_id") != bound_phase.get("attempt_id")
            or authority_phase.get("attempt_id") != attempt.get("attempt_id")
            or authority_phase.get("exposure_preregistration_sha256")
            != authority["hashes"]["exposure_preregistration_sha256"]  # type: ignore[index]
        ):
            raise RecoveryError(f"{phase} authority/attempt binding drift")
        _validate_attempt(
            attempt,
            run_id=run_id,
            attempt_id=str(attempt["attempt_id"]),
            state="ABORTED",
            calls=sample_count,
            audio_seconds=float(expected["attempt_audio_seconds"]),
        )
        if not str(attempt_id).endswith(f"{attempt['attempt_id']}.json"):
            raise RecoveryError(f"{phase} attempt path identity drift")

    embedding = _read_object(paths["embedding_tool_receipt"], "embedding receipt")
    if (
        embedding.get("status") != "FINALIZED"
        or embedding.get("logical_items") != expected["embedding_logical_items"]
        or embedding.get("physical_requests") != expected["embedding_physical_requests"]
    ):
        raise RecoveryError("embedding receipt is not FINALIZED 104/4")
    embedding_plan = authority.get("embedding_execution_plan")
    embedding_attempt = _read_object(paths["embedding_attempt"], "embedding attempt")
    if not isinstance(embedding_plan, Mapping):
        raise RecoveryError("embedding authority plan is missing")
    _validate_attempt(
        embedding_attempt,
        run_id=f"{run_id}-EMBED",
        attempt_id=str(embedding_plan.get("attempt_id")),
        state="FINALIZED",
        calls=sample_count,
        audio_seconds=0.0,
    )

    service_docs = {
        kind: _read_object(paths[f"service:{kind}"], f"{kind} receipt")
        for kind in SERVICE_KINDS
    }
    for family in ("embedding", "generation"):
        session = service_docs[f"{family}_session"]
        stop = service_docs[f"{family}_stop"]
        if (
            session.get("schema") not in {"saea-session-receipt-v1", "saea-session-receipt-v2"}
            or stop.get("schema") != "saea-session-stop-receipt-v1"
            or stop.get("session_id") != session.get("session_id")
            or stop.get("pid") != session.get("pid")
            or not isinstance(stop.get("stopped_at"), str)
            or stop.get("forced") is not False
        ):
            raise RecoveryError(f"{family} service is not cleanly stopped")
    if embedding.get("stop") != service_docs["embedding_stop"]:
        raise RecoveryError("embedding finalization and stop receipt differ")

    direct = verify_bundle(paths["direct:manifest"])
    if len(direct.outputs_rows) != sample_count or direct.attempt_state != "ABORTED":
        raise RecoveryError("recovered direct bundle is not a verified 104-row source")
    return paths, seal, sample_ids, candidates, phase_documents, outputs


def _transport_indexes(
    documents: Sequence[Mapping[str, object]],
) -> tuple[dict[str, Mapping[str, object]], dict[str, Mapping[str, object]]]:
    requests: dict[str, Mapping[str, object]] = {}
    responses: dict[str, Mapping[str, object]] = {}
    for row in documents:
        channel = row.get("channel")
        payload = row.get("payload")
        if not isinstance(payload, Mapping):
            continue
        if channel == "MODEL_REQUEST":
            inner = payload.get("payload")
            sample_id = inner.get("sample_id") if isinstance(inner, Mapping) else None
            if isinstance(sample_id, str):
                requests[sample_id] = payload
        elif channel == "MODEL_RESPONSE":
            record_id = row.get("record_id")
            if isinstance(record_id, str) and record_id.endswith("/response"):
                responses[record_id.removesuffix("/response")] = payload
    return requests, responses


def _lineage_rows(
    *,
    phase: str,
    sample_ids: Sequence[str],
    candidates: Mapping[str, Mapping[str, object]],
    documents_by_phase: Mapping[str, Sequence[Mapping[str, object]]],
    send_rows: Sequence[Mapping[str, object]],
) -> tuple[dict[str, object], ...]:
    current_requests, current_responses = _transport_indexes(documents_by_phase[phase])
    response_by_sample: dict[str, Mapping[str, object]] = {}
    for sample_id, request in current_requests.items():
        inner = request["payload"]
        assert isinstance(inner, Mapping)
        request_id = inner.get("request_id")
        if isinstance(request_id, str) and request_id in current_responses:
            response_by_sample[sample_id] = current_responses[request_id]
    predecessor_phase = PHASE_ROLES[phase][2]
    predecessor_by_sample: dict[str, Mapping[str, object]] = {}
    if predecessor_phase is not None:
        predecessor_requests, predecessor_responses = _transport_indexes(
            documents_by_phase[predecessor_phase]
        )
        for sample_id, request in predecessor_requests.items():
            inner = request["payload"]
            assert isinstance(inner, Mapping)
            request_id = inner.get("request_id")
            if isinstance(request_id, str) and request_id in predecessor_responses:
                predecessor_by_sample[sample_id] = predecessor_responses[request_id]
    body_hashes = {
        (str(row["phase"]), str(row["sample_id"])): row["body_sha256"]
        for row in send_rows
    }
    result = []
    for sample_id in sample_ids:
        request = current_requests[sample_id]
        inner = request["payload"]
        assert isinstance(inner, Mapping)
        history = inner.get("history")
        control_hash = None
        if isinstance(history, list) and len(history) == 1 and isinstance(history[0], Mapping):
            content = history[0].get("content")
            if (
                isinstance(content, str)
                and history[0].get("content_sha256")
                == hashlib.sha256(content.encode("ascii")).hexdigest()
            ):
                control_hash = history[0]["content_sha256"]
        if not _is_sha256(control_hash):
            raise RecoveryError(f"{phase}/{sample_id} control-content hash drift")
        candidate = candidates[sample_id]
        names = candidate["candidate_tool_names"]
        response = response_by_sample[sample_id]
        predecessor = predecessor_by_sample.get(sample_id)
        result.append(
            {
                "sample_id": sample_id,
                "phase": phase,
                "source_request_payload_sha256": request["payload_sha256"],
                "source_request_body_sha256": body_hashes[(phase, sample_id)],
                "source_control_content_sha256": control_hash,
                "source_response_sha256": response["response_sha256"],
                "source_response_text_sha256": response["response_text_sha256"],
                "observation_state_sha256": candidate["observation_state_sha256"],
                "candidate_query_state_sha256": candidate[
                    "candidate_query_state_sha256"
                ],
                "candidate_set_sha256": candidate["candidate_set_sha256"],
                "candidate_order_sha256": _canonical_sha256(names),
                "candidate_tool_names": names,
                "candidate_scores": candidate["candidate_scores"],
                "predecessor_phase": predecessor_phase,
                "predecessor_response_sha256": (
                    predecessor.get("response_sha256") if predecessor else None
                ),
                "predecessor_response_text_sha256": (
                    predecessor.get("response_text_sha256") if predecessor else None
                ),
            }
        )
    return tuple(result)


def _reuse_direct_bundle(
    paths: Mapping[str, Path], *, sample_count: int
) -> dict[str, object]:
    """Reference the already verified direct bundle without rewriting it."""

    source = {
        field: paths[f"direct:{field}"]
        for field in ("manifest", "outputs", "trace", "trace_manifest")
    }
    verified = verify_bundle(source["manifest"])
    if len(verified.outputs_rows) != sample_count or verified.attempt_state != "ABORTED":
        raise RecoveryError("source direct manifest no longer verifies")
    return {
        "role": "direct_m0",
        "status": "COMPLETE",
        "complete_rows": sample_count,
        "manifest": str(source["manifest"].resolve()),
        "manifest_sha256": _sha256(source["manifest"]),
        "source_bundle": {field: _artifact(path) for field, path in source.items()},
        "source_manifest_reused_without_rewriting": True,
    }


def recover(plan_path: Path, data_root: Path) -> dict[str, object]:
    plan = _read_object(plan_path, "recovery plan")
    _validate_plan(plan, data_root=data_root)
    authority = _validate_authority(plan, plan_path=plan_path)
    recovery_study_commit = require_clean_study_repo(REPO)
    (
        source_paths,
        initial_source_seal,
        sample_ids,
        candidates,
        phase_documents,
        phase_outputs,
    ) = _validate_source(plan, authority, data_root=data_root)

    mission = Path(str(plan["source_mission"])).resolve()
    target = mission / str(plan["recovery_target_dirname"])
    if target.exists():
        raise RecoveryError(f"recovery target already exists: {target}")
    target.mkdir(parents=False, exist_ok=False)
    source_seal_path = target / "source-seal.json"
    _write_json_exclusive(source_seal_path, initial_source_seal)
    expected = plan["expected"]
    assert isinstance(expected, Mapping)
    sample_count = int(expected["sample_count"])
    descriptors = [_reuse_direct_bundle(source_paths, sample_count=sample_count)]

    authority_plans = authority["execution_plans"]
    assert isinstance(authority_plans, Mapping)
    composed = compose(REPO, **CONFIG_FRAGMENTS)
    if composed.config_hash != authority.get("composed_config_sha256"):
        raise RecoveryError("current composed config differs from V5 authority")
    direct_manifest = _read_object(source_paths["direct:manifest"], "direct manifest")
    split = direct_manifest.get("split")
    if not isinstance(split, Mapping) or not isinstance(split.get("ids"), list):
        raise RecoveryError("direct manifest split is malformed")
    bare_ids = tuple(str(item) for item in split["ids"])
    prefixed_ids = tuple(f"audio2tool/{sample_id}" for sample_id in bare_ids)
    bundle_split = str(authority["bundle_split_identity_hash"])
    if (
        set(bare_ids) != set(sample_ids)
        or split_identity_hash(prefixed_ids) != bundle_split
    ):
        raise RecoveryError("direct bundle split differs from V5 sample roster")
    verified_split = VerifiedSplit(
        name=str(split.get("name", "")),
        carrier_lock_key="audio2tool",
        split_role="discovery",
        ids=bare_ids,
        prefixed_ids=prefixed_ids,
        identity_hash=bundle_split,
    )
    send_rows = _read_jsonl(source_paths["send_accounting"], "send accounting")
    generation_session = source_paths["service:generation_session"]

    for phase in PHASE_ORDER:
        role, score_ready, _predecessor = PHASE_ROLES[phase]
        if not score_ready:
            continue
        assert role is not None
        directory = target / role
        directory.mkdir(parents=False, exist_ok=False)
        raw_trace = directory / f"{plan['run_id']}.trace.jsonl"
        shutil.copyfile(source_paths[f"{phase}:trace"], raw_trace)
        if _sha256(raw_trace) != _sha256(source_paths[f"{phase}:trace"]):
            raise RecoveryError(f"{phase} trace copy drift")
        rows, cost, record_hashes = _derive_trace_material(
            phase_documents[phase], phase=phase, sample_ids=sample_ids
        )
        outputs_path = directory / f"{plan['run_id']}.outputs.jsonl"
        _write_jsonl_exclusive(outputs_path, rows)
        trace_manifest = directory / f"{plan['run_id']}.trace-manifest.json"
        _write_json_exclusive(
            trace_manifest,
            {"run_id": plan["run_id"], "records": record_hashes},
        )
        lineage = directory / "select-fill-lineage.json"
        lineage_rows = _lineage_rows(
            phase=phase,
            sample_ids=sample_ids,
            candidates=candidates,
            documents_by_phase=phase_documents,
            send_rows=send_rows,
        )
        _write_json_exclusive(
            lineage,
            {
                "schema": "saea-a2t-select-fill-score-ready-lineage-v1",
                "role": role,
                "phase": phase,
                "source_trace": _artifact(source_paths[f"{phase}:trace"]),
                "rows": lineage_rows,
            },
        )
        raw_plan = authority_plans[phase]
        assert isinstance(raw_plan, Mapping)
        plan_fields = {
            key: raw_plan[key] for key in ExecutionPlan.__dataclass_fields__ if key in raw_plan
        }
        execution_plan = replace(
            ExecutionPlan(**plan_fields).validate(),
            split_identity_hash=bundle_split,
            protocol_hash=str(authority["bundle_protocol_sha256"]),
        ).validate()
        result = RunResult(
            run_id=str(plan["run_id"]),
            arm=ARM,
            outputs_path=outputs_path,
            trace_manifest_hash=_sha256(trace_manifest),
            cost=cost,
        )
        manifest_path = build_manifest(
            repo_root=REPO,
            data_root=data_root,
            composed=composed,
            plan=execution_plan,
            verified_split=verified_split,
            session_receipt_path=generation_session,
            run_dir=directory,
            status=STATUS_COMPLETED,
            result=result,
        )
        manifest = _read_object(manifest_path, f"{phase} successor manifest")
        manifest["recovery_provenance"] = {
            "schema": "saea-a2t-select-fill-v5-zero-contact-successor-v1",
            "status": "EXTERNALLY_SEALED_SOURCE",
            "source_attempt_state": "ABORTED",
            "source_attempt": _artifact(source_paths[f"{phase}:attempt"]),
            "source_trace": _artifact(source_paths[f"{phase}:trace"]),
            "source_failure": _artifact(source_paths["failure_receipt"]),
            "source_authority_binding": _artifact(source_paths["authority_binding"]),
            "lineage": _artifact(lineage),
            "model_contacts": 0,
            "embedding_contacts": 0,
            "scorer_contacts": 0,
            "gold_opened": False,
            "response_bytes_programmatically_materialized": True,
            "response_meanings_interpreted_by_investigator": False,
        }
        manifest_path.unlink()
        _write_json_exclusive(manifest_path, manifest)
        verified = verify_bundle(manifest_path)
        if len(verified.outputs_rows) != sample_count or verified.attempt_state != "ABORTED":
            raise RecoveryError(f"{phase} successor bundle verification failed")
        descriptors.append(
            {
                "role": role,
                "phase": phase,
                "status": "COMPLETE",
                "complete_rows": sample_count,
                "manifest": str(manifest_path.resolve()),
                "manifest_sha256": _sha256(manifest_path),
                "outputs_sha256": _sha256(outputs_path),
                "raw_trace_sha256": _sha256(raw_trace),
                "trace_manifest_sha256": _sha256(trace_manifest),
                "lineage": str(lineage.resolve()),
                "lineage_sha256": _sha256(lineage),
            }
        )

    _source_paths, final_source_seal = _source_paths_and_seal(
        plan, data_root=data_root
    )
    if final_source_seal != initial_source_seal:
        raise RecoveryError("immutable source artifacts changed during recovery")
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "SEALED",
        "run_id": plan["run_id"],
        "source_mission": str(mission),
        "recovery_directory": str(target.resolve()),
        "recovery_plan": _artifact(Path(plan_path)),
        "recovery_implementation": _artifact(Path(__file__)),
        "recovery_study_commit": recovery_study_commit,
        "source_seal": _artifact(source_seal_path),
        "source_generation_contacts": expected["generation_contacts"],
        "source_embedding_logical_items": expected["embedding_logical_items"],
        "source_embedding_physical_requests": expected[
            "embedding_physical_requests"
        ],
        "recovery_model_contacts": 0,
        "recovery_embedding_contacts": 0,
        "recovery_tokenizer_contacts": 0,
        "recovery_scorer_contacts": 0,
        "gold_opened": False,
        "scorer_started": False,
        "response_meanings_opened": False,
        "source_attempt_states": ["ABORTED"],
        "embedding_attempt_state": "FINALIZED",
        "services_stopped": True,
        "manifests": descriptors,
        "score_ready_manifest_count": len(descriptors),
    }
    if len(descriptors) != 4:
        raise RecoveryError("recovery did not produce exactly four score-ready manifests")
    receipt_path = target / "recovery-receipt.json"
    _write_json_exclusive(receipt_path, receipt)
    return {**receipt, "recovery_receipt": _artifact(receipt_path)}


def preflight(plan_path: Path, data_root: Path) -> dict[str, object]:
    plan = _read_object(plan_path, "recovery plan")
    _validate_plan(plan, data_root=data_root)
    authority = _validate_authority(plan, plan_path=plan_path)
    recovery_study_commit = require_clean_study_repo(REPO)
    paths, seal, sample_ids, _candidates, _documents, _outputs = _validate_source(
        plan, authority, data_root=data_root
    )
    target = Path(str(plan["source_mission"])) / str(
        plan["recovery_target_dirname"]
    )
    if target.exists():
        raise RecoveryError(f"recovery target already exists: {target}")
    return {
        "status": "ZERO_CONTACT_RECOVERY_READY",
        "run_id": plan["run_id"],
        "sample_count": len(sample_ids),
        "source_artifact_count": len(seal["artifacts"]),  # type: ignore[arg-type]
        "source_direct_manifest": _artifact(paths["direct:manifest"]),
        "recovery_study_commit": recovery_study_commit,
        "target_absent": True,
        "model_contacts": 0,
        "embedding_contacts": 0,
        "tokenizer_contacts": 0,
        "scorer_contacts": 0,
        "gold_opened": False,
        "response_meanings_opened": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("SPEECHRL_DATA_DIR", "")),
    )
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--preflight-only", action="store_true")
    actions.add_argument("--recover", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    data_root = Path(args.data_root)
    if not str(data_root) or not data_root.is_dir():
        raise RecoveryError(
            "SPEECHRL_DATA_DIR or --data-root must name the existing data root"
        )
    result = (
        preflight(args.plan, data_root)
        if args.preflight_only
        else recover(args.plan, data_root)
    )
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
