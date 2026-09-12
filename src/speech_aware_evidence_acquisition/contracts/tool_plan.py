"""Admission for one pinned local frozen retrieval-encoder preparation.

This is deliberately narrower than ``FrozenCoreGate``: it authorizes a
pre-registered local encoder *tool plan*, never a Qwen GGUF core touch.  It
does not load data, start a process, or contact an encoder.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from .errors import ExecutionScopeError, GateClosed
from .gate_exposure import _ExposureAndCarrierMixin
from .identifiers import _SHA256
from .plan import (
    MODEL_TOUCH_PROFILES,
    TEXT_ENCODER_PLAN_SCHEMA,
    ExecutionPlan,
    assert_wsl_execution_environment,
)

TEXT_FACET_ENCODING_PROTOCOL_SCHEMA = "saea-text-facet-encoding-protocol-v1"


class _ToolPlanExposureChecks(_ExposureAndCarrierMixin):
    """The carrier and exposure checks shared with ``FrozenCoreGate``."""

    def __init__(self, *, source_root: Path, exposure_ledger: Path) -> None:
        self.source_root = source_root
        self.exposure_ledger = exposure_ledger


def _require_sha256(value: object, *, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise GateClosed(f"{field} must be a 64-hex SHA-256")
    return value


def _read_pinned_bytes(path: Path, expected_sha256: object, *, label: str) -> bytes:
    """Read only after the configured digest itself has passed shape checks."""

    expected = _require_sha256(expected_sha256, field=f"{label}_sha256")
    try:
        raw = Path(path).read_bytes()
    except OSError as error:
        raise GateClosed(f"{label} missing or unreadable ({path}): {error}") from error
    measured = hashlib.sha256(raw).hexdigest()
    if measured != expected:
        raise GateClosed(
            f"{label} hashes to {measured}, not the configured {expected}"
        )
    return raw


def assert_registered_tool_plan(
    *,
    source_root: Path,
    exposure_ledger: Path,
    umbrella_lock: Path,
    umbrella_lock_sha256: str,
    protocol_path: Path,
    protocol_sha256: str,
    plan: ExecutionPlan,
) -> None:
    """Admit a pinned, local frozen retrieval-encoder preparation plan.

    The caller must perform its own encoder invocation only after this returns.
    This function checks WSL authority, the exact ``ExecutionPlan`` type and
    attempt id, pinned lock/protocol bytes, and the shared carrier/exposure
    preregistration checks.  It intentionally has no model-runtime or corpus
    dependency.
    """

    assert_wsl_execution_environment()
    if type(plan) is not ExecutionPlan:
        raise ExecutionScopeError("tool plan requires the exact ExecutionPlan contract type")
    plan.validate()
    if plan.execution_profile not in MODEL_TOUCH_PROFILES:
        raise ExecutionScopeError(
            "local frozen retrieval preparation requires a model-touch execution profile"
        )
    if plan.attempt_id is None:
        raise ExecutionScopeError("local frozen retrieval preparation requires attempt_id")

    lock_raw = _read_pinned_bytes(
        Path(umbrella_lock), umbrella_lock_sha256, label="umbrella_lock"
    )
    protocol_raw = _read_pinned_bytes(
        Path(protocol_path), protocol_sha256, label="protocol"
    )
    measured_protocol = hashlib.sha256(protocol_raw).hexdigest()
    if plan.protocol_hash != measured_protocol:
        raise GateClosed(
            "execution plan protocol_hash does not match the pinned protocol bytes"
        )
    if plan.schema == TEXT_ENCODER_PLAN_SCHEMA:
        try:
            protocol = json.loads(protocol_raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise GateClosed(
                f"text-facet-encoding protocol is not a JSON object: {error}"
            ) from error
        if not isinstance(protocol, Mapping):
            raise GateClosed("text-facet-encoding protocol must be a JSON object")
        if protocol.get("schema") != TEXT_FACET_ENCODING_PROTOCOL_SCHEMA:
            raise GateClosed(
                "text-encoder tool plan requires pinned text-facet-encoding "
                f"protocol schema {TEXT_FACET_ENCODING_PROTOCOL_SCHEMA!r}"
            )
    try:
        lock = json.loads(lock_raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise GateClosed(f"umbrella_lock is not a JSON object: {error}") from error
    if not isinstance(lock, Mapping):
        raise GateClosed("umbrella_lock must be a JSON object")

    checks = _ToolPlanExposureChecks(
        source_root=Path(source_root), exposure_ledger=Path(exposure_ledger)
    )
    checks._resolve_carrier_dataset_entry(plan.carrier_lock_key, lock)
    checks._require_exposure_preregistration(plan, lock)


__all__ = [
    "TEXT_FACET_ENCODING_PROTOCOL_SCHEMA",
    "assert_registered_tool_plan",
]
