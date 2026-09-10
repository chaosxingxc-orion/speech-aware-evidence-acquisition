"""Build a source-bound window predecessor for an offline two-stage flight.

Recover terminal windows through the existing stitch proof. Never select by
quality or reopen a model, reference, scorer, tokenizer or audio decoder.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

from ..analysis import e21_window_pairing as wp
from .bundle import verify_bundle
from .bundle.git_commit import require_clean_study_repo
from .predecessor_snapshot import (
    BINDING_SCHEMA, SNAPSHOT_SCHEMA, PredecessorSnapshotError,
    window_text_chain_sha256,
)
from .preparation import digest, hash_stable_file

CONTRACT_SCHEMA = "saea-sealed-window-parent-contract-v1"


def _require_equal(actual, expected, label):
    if actual != expected:
        raise PredecessorSnapshotError(f"{label} differs from the frozen parent contract")


def verify_parent_contract(bundle, contract: Mapping):
    """Check prospectively fixed source identity before accessing window text."""
    required = {
        "schema", "run_id", "attempt_id", "config_hash", "protocol_hash",
        "split_identity_hash", "sample_ids", "window_geometry",
    }
    if set(contract) != required or contract["schema"] != CONTRACT_SCHEMA:
        raise PredecessorSnapshotError("invalid sealed window parent contract")
    m = bundle.manifest
    for actual, expected, label in (
        (m["status"], "COMPLETED", "parent status"),
        (m["run_id"], contract["run_id"], "run"),
        (m["attempt"]["attempt_id"], contract["attempt_id"], "attempt"),
        (m["plan"]["carrier_lock_key"], "earnings21-original", "carrier"),
        (m["config"]["config_hash"], contract["config_hash"], "configuration"),
        (m["protocol_hash"], contract["protocol_hash"], "protocol"),
        (m["split"]["identity_hash"], contract["split_identity_hash"], "split"),
    ):
        _require_equal(actual, expected, label)
    ids = contract["sample_ids"]
    if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)):
        raise PredecessorSnapshotError("parent contract needs a complete unique call roster")
    _require_equal(set(bundle.split_ids), set(ids), "call roster")
    geometry = contract["window_geometry"]
    if not isinstance(geometry, list) or not geometry:
        raise PredecessorSnapshotError("parent contract needs complete window geometry")
    expected = {}
    for row in geometry:
        if not isinstance(row, Mapping) or set(row) != {
            "sample_id", "window_index", "start_seconds", "end_seconds"
        }:
            raise PredecessorSnapshotError("invalid expected window geometry")
        sid, index = row["sample_id"], row["window_index"]
        key = wp.window_id(sid, index)
        if sid not in ids or key in expected:
            raise PredecessorSnapshotError("duplicate or foreign expected window")
        start, end = row["start_seconds"], row["end_seconds"]
        if (isinstance(start, bool) or isinstance(end, bool)
                or not isinstance(start, (int, float)) or not isinstance(end, (int, float))
                or not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start):
            raise PredecessorSnapshotError("invalid expected window bounds")
        expected[key] = dict(row)
    _require_equal({v["sample_id"] for v in expected.values()}, set(ids), "window call roster")
    return expected


def recover_parent_rows(bundle, contract: Mapping):
    """Reuse the terminal-window recovery and verify its complete source geometry."""
    expected = verify_parent_contract(bundle, contract)
    m = bundle.manifest
    trace = Path(m["raw_trace"]["path"])
    windows = wp.stitched_windows_from_trace(trace)
    outputs = {row["sample_id"]: row["text"] for row in bundle.outputs_rows}
    wp.assert_stitch_reproduces_outputs(windows, outputs)
    # VerifiedBundle maps record id to the already-verified payload, not
    # to the raw channel/record_id/payload envelope.
    costs = {
        record_id.removesuffix("/cost"): payload
        for record_id, payload in bundle.trace_records.items()
        if record_id.endswith("/cost")
    }
    rows = []
    for sid in sorted(windows):
        for span in windows[sid]:
            geometry = {
                "sample_id": span.sample_id, "window_index": span.window_index,
                "start_seconds": span.start_seconds, "end_seconds": span.end_seconds,
            }
            _require_equal(geometry, expected.get(span.identifier), "window source geometry")
            cost = costs.get(span.request_id)
            if not isinstance(cost, Mapping):
                raise PredecessorSnapshotError("terminal window lacks its original cost")
            for field in ("prompt_tokens", "completion_tokens"):
                if (isinstance(cost.get(field), bool) or not isinstance(cost.get(field), int)
                        or cost[field] < 0):
                    raise PredecessorSnapshotError("window cost is unavailable or invalid")
            rows.append({
                **geometry, "window_id": span.identifier, "request_id": span.request_id,
                "audio_seconds": span.audio_seconds, "saturated": span.saturated,
                "text": span.text,
                "text_sha256": hashlib.sha256(span.text.encode("utf-8")).hexdigest(),
                "text_chars": len(span.text), "text_whitespace_tokens": len(span.text.split()),
                "prompt_tokens": cost["prompt_tokens"],
                "completion_tokens": cost["completion_tokens"],
            })
    ids = [row["window_id"] for row in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise PredecessorSnapshotError("recovered terminal windows do not cover the contract")
    # Select the successful terminal requests already named by the stitch.
    # Charge every recorded attempt, including a bounded retry, to the parent.
    # Saturated terminal text remains empty exactly as the stitch delivered it.
    _require_equal(m["cost"]["calls_used"], len(costs), "generation contact count")
    _require_equal(m["cost"].get("skipped_slice_count", 0), 0, "skipped windows")
    for field in ("prompt_tokens", "completion_tokens"):
        for cost in costs.values():
            if isinstance(cost.get(field), bool) or not isinstance(cost.get(field), int) or cost[field] < 0:
                raise PredecessorSnapshotError("attempt cost is unavailable or invalid")
        _require_equal(sum(cost[field] for cost in costs.values()), m["cost"][field + "_total"],
                       field + " total")
    _require_equal(sum(row["saturated"] for row in rows),
                   m["cost"]["saturated_slice_count"], "saturation count")
    return rows


def _write_new_json(path: Path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    # An existing derivative is immutable. A second producer cannot overwrite it.
    with path.open("xb") as stream:
        stream.write(json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True).encode() + b"\n")


def build_predecessor_snapshot(*, manifest_path: Path, repo_root: Path, data_root: Path,
                               contract: Mapping, receipt_path: Path, exposure_row: str):
    """Verify, recover and bind a newly sealed parent without a model contact."""
    repo_root, data_root = Path(repo_root).resolve(), Path(data_root).resolve()
    manifest_path = Path(manifest_path).resolve()
    receipt_path = Path(receipt_path).resolve()
    if not manifest_path.is_relative_to(data_root):
        raise PredecessorSnapshotError("parent manifest must live below the data root")
    if not receipt_path.is_relative_to(repo_root / "docs" / "receipts"):
        raise PredecessorSnapshotError("content-free receipt must live under docs/receipts")
    if not isinstance(exposure_row, str) or not exposure_row.strip():
        raise PredecessorSnapshotError("a model-free exposure registration is required")
    ledger = (repo_root / "docs/exposure-ledger.md").read_text()
    if f"| {exposure_row} |" not in ledger:
        raise PredecessorSnapshotError("model-free predecessor exposure row is not registered")
    commit = require_clean_study_repo(repo_root)
    before = hash_stable_file(manifest_path, "parent manifest")[1]
    bundle = verify_bundle(manifest_path)
    rows = recover_parent_rows(bundle, contract)
    _require_equal(hash_stable_file(manifest_path, "parent manifest")[1], before,
                   "unchanged sealed manifest")
    m = bundle.manifest
    for identifier in (m["run_id"], m["attempt"]["attempt_id"]):
        if not isinstance(identifier, str) or Path(identifier).name != identifier or identifier in {".", ".."}:
            raise PredecessorSnapshotError("parent identity is not a path component")
    relative = f"derived/e21-predecessor/{m['run_id']}/{m['attempt']['attempt_id']}/window-hypotheses.json"
    artifact = (data_root / relative).resolve()
    if not artifact.is_relative_to(data_root):
        raise PredecessorSnapshotError("predecessor artifact escaped data root")
    if artifact.exists() or receipt_path.exists():
        raise PredecessorSnapshotError("predecessor artifact or receipt already exists; preserve it")
    source = {"manifest_sha256": before, "outputs_sha256": m["outputs"]["sha256"],
              "trace_sha256": m["raw_trace"]["sha256"]}
    common = {
        "study": "speech-aware-evidence-acquisition", "run_id": m["run_id"],
        "attempt_id": m["attempt"]["attempt_id"], "carrier_lock_key": "earnings21-original",
        "split_identity_hash": contract["split_identity_hash"],
        "generated_at": datetime.now(timezone.utc).isoformat(), "study_commit": commit,
        "source": source, "parent_contract_sha256": digest(contract),
        "windows": len(rows), "calls": len(bundle.split_ids),
    }
    snapshot = {**common, "schema": SNAPSHOT_SCHEMA, "rows": rows,
                "recovery": "Existing stitched_windows_from_trace plus byte-for-byte sealed output proof"}
    _write_new_json(artifact, snapshot)
    size, sha, _ = hash_stable_file(artifact, "new predecessor artifact")
    receipt = {
        **common, "schema": BINDING_SCHEMA, "exposure_row": exposure_row,
        "built_by": "core.predecessor_builder.build_predecessor_snapshot",
        "artifact": {"relpath": relative, "sha256": sha, "bytes": size, "root": "SPEECHRL_DATA_DIR"},
        "window_text_sha256_chain": window_text_chain_sha256(rows),
        "saturated_windows": sum(row["saturated"] for row in rows),
        "prompt_tokens_total": sum(row["prompt_tokens"] for row in rows),
        "completion_tokens_total": sum(row["completion_tokens"] for row in rows),
        "parent_generation_cost": m["cost"],
        "token_total_scope": "Selected terminal windows; parent_generation_cost also includes any bounded retries.",
        "stitch_rebuilds_sealed_outputs_byte_for_byte": "PASS",
        "content_free": True, "additional_model_contacts": 0,
        "cost_rule": "Charge the original parent once and add the downstream repair; this derivative adds zero generation.",
    }
    _write_new_json(receipt_path, receipt)
    return {"receipt_path": str(receipt_path),
            "receipt_sha256": hash_stable_file(receipt_path, "predecessor receipt")[1],
            "artifact_sha256": sha, "windows": len(rows), "calls": len(bundle.split_ids)}
