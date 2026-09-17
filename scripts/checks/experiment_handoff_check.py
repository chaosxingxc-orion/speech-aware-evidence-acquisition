#!/usr/bin/env python3
"""Inspect a file-based handoff without granting execution or changing its state.

Only local handoff files and Git metadata are read. A complete reply is ready
for review; an explicit owner decision can instead authorize reconstruction
and merging when a reply is unavailable; an explicit owner decision plus a
Fable takeover receipt records that Fable5.1 has become the coordinator and
execution owner (phase ``fable_directed_execution``, 2026-09-16). No state
grants experiment launch: every model contact is gated per flight elsewhere.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PureWindowsPath
import re
import subprocess


STATE_PATH = "docs/superpowers/plans/experiment-handoff/state.json"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _confined_path(root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("path must be a nonempty relative string")
    windows_path = PureWindowsPath(value)
    if (
        Path(value).is_absolute()
        or windows_path.drive
        or windows_path.root
        or ".." in windows_path.parts
    ):
        raise ValueError("path must be relative and contain no parent traversal")
    try:
        target = (root / value.replace("\\", "/")).resolve()
    except RuntimeError:
        raise ValueError("path contains a symbolic-link cycle") from None
    if not target.is_relative_to(root) or target == root:
        raise ValueError("path resolves outside the repository or to its root")
    return target


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "-C", str(root), *args],
        capture_output=True,
        check=True,
        timeout=30,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )
    return result.stdout


def _git_snapshot(root: Path) -> dict:
    actual_root = Path(os.fsdecode(_git(root, "rev-parse", "--show-toplevel")).strip())
    if actual_root.resolve() != root:
        raise ValueError("repo root must identify the Git repository itself")
    head = _git(root, "rev-parse", "--verify", "HEAD").decode("ascii").strip()
    entries = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all").split(b"\x00")
    counts = {"tracked": 0, "untracked": 0, "staged": 0, "unstaged": 0}
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        status = entry[:2]
        if status == b"??":
            counts["untracked"] += 1
            continue
        counts["tracked"] += 1
        counts["staged"] += status[:1] != b" "
        counts["unstaged"] += status[1:2] != b" "
        if b"R" in status or b"C" in status:
            index += 1  # Porcelain -z includes an additional source pathname.
    counts["total"] = counts["tracked"] + counts["untracked"]
    return {"current_head": head, "dirty_file_counts": counts}


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("state contains duplicate JSON keys")
        result[key] = value
    return result


def _validate_state(state: object, root: Path) -> tuple[Path, Path]:
    if not isinstance(state, dict):
        raise ValueError("state must be a JSON object")
    if type(state.get("schema_version")) is not int or state["schema_version"] != 1:
        raise ValueError("schema_version must be 1")
    if type(state.get("generation")) is not int or state["generation"] < 1:
        raise ValueError("generation must be a positive integer")
    phase = state.get("phase")
    if phase not in (
        "awaiting_fable_reply", "owner_directed_recovery", "owner_directed_execution",
        "fable_directed_execution",
    ):
        raise ValueError(
            "phase must be awaiting_fable_reply, owner_directed_recovery, "
            "owner_directed_execution or fable_directed_execution"
        )
    expected_response = "awaiting_reply" if phase == "awaiting_fable_reply" else "unavailable"
    if state.get("response_status") != expected_response:
        raise ValueError(f"response_status must be {expected_response} for this phase")
    if state.get("launch_allowed") is not False:
        raise ValueError("launch_allowed must be false during handoff or owner recovery")
    for field in ("coordinator", "execution_owner", "request_id", "next_action"):
        if not isinstance(state.get(field), str) or not state[field].strip():
            raise ValueError(f"{field} must be a nonempty string")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", state["request_id"]):
        raise ValueError("request_id must contain only letters, numbers, dots, underscores or hyphens")
    if not isinstance(state.get("snapshot_commit"), str) or not re.fullmatch(
        r"[0-9a-fA-F]{40}", state["snapshot_commit"]
    ):
        raise ValueError("snapshot_commit must be a 40-character hexadecimal commit")
    try:
        updated = datetime.fromisoformat(state["updated_at_utc"])
        if updated.tzinfo is None or updated.utcoffset() != timezone.utc.utcoffset(updated):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise ValueError("updated_at_utc must be an ISO timestamp with UTC timezone") from None
    request = _confined_path(root, state.get("request_path"))
    response = _confined_path(root, state.get("response_path"))
    if len({request, response, _confined_path(root, STATE_PATH)}) != 3:
        raise ValueError("state, request and response paths must be distinct")
    if not request.is_file():
        raise ValueError("request file is missing or is not a regular file")
    if response.exists() and not response.is_file():
        raise ValueError("response path exists but is not a regular file")
    return request, response


def _validate_owner_recovery(state: dict, root: Path, request: Path, response: Path) -> None:
    """Require a bounded owner decision, without treating it as a Fable release."""
    if state["generation"] < 2:
        raise ValueError("owner recovery must supersede the initial handoff generation")
    if state["coordinator"] != "Codex" or state["execution_owner"] != "Codex":
        raise ValueError("owner recovery coordinator and execution_owner must be Codex")
    decision_id = state.get("owner_decision_id")
    if not isinstance(decision_id, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]*", decision_id
    ):
        raise ValueError("owner_decision_id must be a nonempty identifier")
    decision = _confined_path(root, state.get("owner_decision_path"))
    if decision in (request, response, _confined_path(root, STATE_PATH)):
        raise ValueError("owner decision must be distinct from state, request and response")
    if not decision.is_file():
        raise ValueError("owner decision file is missing or is not a regular file")
    content = decision.read_text(encoding="utf-8")
    markers = {
        "Decision ID": decision_id,
        "Request ID": state["request_id"],
        "Owner decision": "AUTHORIZE_RECOVERY",
        "Execution owner": "Codex",
        "Scope": "RECONSTRUCTION_AND_MERGE_ONLY",
        "Launch allowed": "false",
    }
    if state["phase"] == "owner_directed_execution":
        markers.update({"Owner decision": "IMPLEMENT_ACCEPTED_CONTINUATION_PLAN",
                        "Scope": "BOUNDED_STAGE2_SLURP_E21_CONTINUATION",
                        "Per-flight gates": "required"})
        markers.pop("Launch allowed")
    for marker, expected in markers.items():
        values = re.findall(
            rf"^\s*(?:#{{1,6}} +)?{re.escape(marker)}: ([^\r\n]+?)\s*$",
            content,
            re.MULTILINE,
        )
        if values != [expected]:
            raise ValueError(f"owner decision requires one exact {marker} marker")


def _require_markers(content: str, markers: dict[str, str], what: str) -> None:
    for marker, expected in markers.items():
        values = re.findall(
            rf"^\s*(?:#{{1,6}} +)?{re.escape(marker)}: ([^\r\n]+?)\s*$",
            content,
            re.MULTILINE,
        )
        if values != [expected]:
            raise ValueError(f"{what} requires one exact {marker} marker")


def _validate_fable_takeover(state: dict, root: Path, request: Path, response: Path) -> Path:
    """Require an explicit owner decision AND a Fable takeover receipt.

    The takeover is recorded, never inferred: the owner decision names Fable5.1
    as execution owner for a bounded scope, and the receipt is Fable's own
    acknowledgement bound to the same request id. Neither grants a launch.
    """
    if state["generation"] < 2:
        raise ValueError("fable takeover must supersede the initial handoff generation")
    if state["coordinator"] != "Fable5.1" or state["execution_owner"] != "Fable5.1":
        raise ValueError("fable takeover coordinator and execution_owner must be Fable5.1")
    reserved = {request, response, _confined_path(root, STATE_PATH)}
    decision_id = state.get("owner_decision_id")
    if not isinstance(decision_id, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]*", decision_id
    ):
        raise ValueError("owner_decision_id must be a nonempty identifier")
    decision = _confined_path(root, state.get("owner_decision_path"))
    if decision in reserved:
        raise ValueError("owner decision must be distinct from state, request and response")
    if not decision.is_file():
        raise ValueError("owner decision file is missing or is not a regular file")
    _require_markers(decision.read_text(encoding="utf-8"), {
        "Decision ID": decision_id,
        "Request ID": state["request_id"],
        "Owner decision": "AUTHORIZE_FABLE_TAKEOVER",
        "Execution owner": "Fable5.1",
        "Scope": "SLURP_V2_BASE_PROGRAM",
        "Per-flight gates": "required",
    }, "owner takeover decision")
    receipt_id = state.get("takeover_receipt_id")
    if not isinstance(receipt_id, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]*", receipt_id
    ):
        raise ValueError("takeover_receipt_id must be a nonempty identifier")
    receipt = _confined_path(root, state.get("takeover_receipt_path"))
    if receipt in reserved or receipt == decision:
        raise ValueError("takeover receipt must be distinct from state, request, response and decision")
    if not receipt.is_file():
        raise ValueError("takeover receipt file is missing or is not a regular file")
    _require_markers(receipt.read_text(encoding="utf-8"), {
        "Takeover ID": receipt_id,
        "Request ID": state["request_id"],
        "Takeover status": "ACKNOWLEDGED",
        "Execution owner": "Fable5.1",
        "Per-flight gates": "required",
    }, "fable takeover receipt")
    return receipt


def _reply_status(response: Path, request_id: str, warnings: list[str]) -> str:
    if not response.exists():
        return "WAITING_FOR_REPLY"
    content = response.read_text(encoding="utf-8")
    statuses = re.findall(r"^\s*(?:#{1,6} +)?Reply status: ([^\r\n]+?)\s*$", content, re.MULTILINE)
    ids = re.findall(r"^\s*(?:#{1,6} +)?Request ID: ([^\r\n]+?)\s*$", content, re.MULTILINE)
    if len(statuses) > 1 or len(ids) > 1:
        raise ValueError("response contains duplicate status or request ID markers")
    if ids and ids != [request_id]:
        raise ValueError("response request ID does not match the active request")
    if statuses and statuses[0] not in ("PENDING", "COMPLETE"):
        raise ValueError("response status marker must be PENDING or COMPLETE")
    if statuses == ["COMPLETE"]:
        if ids != [request_id]:
            raise ValueError("a complete response must identify the active request")
        return "REPLY_READY"
    if not statuses:
        warnings.append("Response exists without a reply status marker; completion is unconfirmed.")
    return "WAITING_FOR_REPLY"


def inspect_handoff(repo_root: Path) -> dict:
    """Return only validation facts and counts, never reply text or launch authority."""
    root = repo_root.resolve()
    report = {
        "schema_version": 1,
        "status": "INVALID",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "current_head": None,
        "dirty_file_counts": None,
        "warnings": [],
        "errors": [],
        "execution_authority": "NOT_EVALUATED",
        "launch_allowed": False,
    }
    try:
        report.update(_git_snapshot(root))
        state = json.loads(
            _confined_path(root, STATE_PATH).read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
        )
        request, response = _validate_state(state, root)
        report["request_id"] = state["request_id"]
        report["generation"] = state["generation"]
        report["snapshot_commit"] = state["snapshot_commit"]
        if report["current_head"] != state["snapshot_commit"].lower():
            report["warnings"].append("Current HEAD differs from the handoff snapshot; reconcile newer changes.")
        if report["dirty_file_counts"]["total"]:
            report["warnings"].append("The working tree has local changes; preserve and reconcile them.")
        if state["phase"] in ("owner_directed_recovery", "owner_directed_execution"):
            _validate_owner_recovery(state, root, request, response)
            report["execution_owner"] = state["execution_owner"]
            report["owner_decision_path"] = state["owner_decision_path"]
            report["status"] = state["phase"].upper()
        elif state["phase"] == "fable_directed_execution":
            _validate_fable_takeover(state, root, request, response)
            report["execution_owner"] = state["execution_owner"]
            report["owner_decision_path"] = state["owner_decision_path"]
            report["takeover_receipt_path"] = state["takeover_receipt_path"]
            report["status"] = state["phase"].upper()
        else:
            report["status"] = _reply_status(response, state["request_id"], report["warnings"])
    except (json.JSONDecodeError, UnicodeError):
        report["errors"].append("A handoff file is not valid UTF-8 text or valid state JSON.")
    except ValueError as exc:
        report["errors"].append(str(exc))
    except (OSError, subprocess.SubprocessError):
        report["errors"].append("A required handoff file or local Git metadata could not be read.")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path, help="Write a new JSON file; refuse to overwrite any existing path.")
    args = parser.parse_args(argv)
    report = inspect_handoff(args.repo_root)
    if args.output is not None:
        try:
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(report, indent=2) + "\n")
        except OSError:
            report["status"] = "INVALID"
            report["errors"].append("Output could not be created; use a new path with an existing parent directory.")
    print(json.dumps(report, indent=2))
    return int(report["status"] == "INVALID")


if __name__ == "__main__":
    raise SystemExit(main())
