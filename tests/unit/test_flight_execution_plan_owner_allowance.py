"""``FlightRuntime._build_execution_plan`` carries the config's owner allowance.

``preflight`` builds its ``contracts.ExecutionPlan`` through
``_build_execution_plan``; before this fix the builder dropped the composed
config's top-level ``owner_allowance``, so every ``final-report`` cell was
refused with "no owner_allowance was declared" even when its config pinned
one. The allowance is an ``InitVar`` on the plan, so train/devel plans (no
allowance declared; roles "discovery"/"dev") must build field- and byte-identically to before.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.contracts import (
    FINAL_REPORT_EXECUTION_PROFILE,
    FINAL_REPORT_SPLIT_ROLE,
    OWNER_SPLIT_ALLOWANCE_RELDIR,
    OWNER_SPLIT_ALLOWANCE_SCHEMA,
    ExecutionPlan,
    ExecutionScopeError,
    OwnerSplitAllowance,
)
from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    compute_protocol_hash,
)

CARRIER = "slurp"
RUN_ID = "SAEA-FAKE-FINAL-REPORT-READ-V1"
ATTEMPT_ID = "attempt-fake-final-report-v1"
CONFIG_HASH = "c" * 64
ARM = "fake-arm"
ALLOWANCE_RELPATH = f"{OWNER_SPLIT_ALLOWANCE_RELDIR}/2026-09-30-fake-allowance-v1.json"
IDENTITY = hashlib.sha256(b"slurp/slurp:test:000000:fake").hexdigest()
DEV_IDENTITY = hashlib.sha256(b"slurp/slurp:devel:000000:fake").hexdigest()


def _allowance_document() -> dict:
    return {
        "schema": OWNER_SPLIT_ALLOWANCE_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "status": "authorised",
        "dated_owner_decision": "fake owner decision of 2026-09-30",
        "venue": "fake venue: the read stays in the study carrier because ...",
        "split": {
            "carrier_lock_key": CARRIER,
            "split_name": "TEST-SAMPLE",
            "split_identity_hash": IDENTITY,
        },
        "permitted_run_ids": [RUN_ID],
        "read_run_ids": [RUN_ID],
        "preparation_run_ids": [],
    }


def _write_allowance(root: Path) -> str:
    path = root / ALLOWANCE_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(_allowance_document(), indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _runtime(repo_root: Path) -> FlightRuntime:
    runtime = object.__new__(FlightRuntime)
    runtime._run_id = RUN_ID
    runtime._attempt_id = ATTEMPT_ID
    runtime._composed = SimpleNamespace(config_hash=CONFIG_HASH)
    runtime._repo_root = Path(repo_root)
    return runtime


def _values(split_role: str, profile: str, allowance: object = None) -> dict:
    values = {
        "arm": ARM,
        "execution_plan": {
            "execution_profile": profile,
            "split_role": split_role,
            "planned_model_calls": 11,
            "planned_gpu_hours": 0.5,
            "planned_speech_audio_seconds": 30,
        },
    }
    if allowance is not None:
        values["owner_allowance"] = allowance
    return values


def test_final_report_plan_with_pinned_allowance_passes(tmp_path):
    digest = _write_allowance(tmp_path)
    allowance = {"path": ALLOWANCE_RELPATH, "sha256": digest}
    plan = _runtime(tmp_path)._build_execution_plan(
        _values(FINAL_REPORT_SPLIT_ROLE, FINAL_REPORT_EXECUTION_PROFILE, allowance),
        CARRIER,
        IDENTITY,
    )
    assert plan.split_role == FINAL_REPORT_SPLIT_ROLE
    assert plan.owner_allowance == OwnerSplitAllowance(path=ALLOWANCE_RELPATH, sha256=digest)


def test_final_report_plan_without_allowance_is_refused(tmp_path):
    _write_allowance(tmp_path)
    with pytest.raises(ExecutionScopeError, match="no owner_allowance was declared"):
        _runtime(tmp_path)._build_execution_plan(
            _values(FINAL_REPORT_SPLIT_ROLE, FINAL_REPORT_EXECUTION_PROFILE),
            CARRIER,
            IDENTITY,
        )


def test_final_report_plan_with_drifted_allowance_is_refused(tmp_path):
    digest = _write_allowance(tmp_path)
    path = tmp_path / ALLOWANCE_RELPATH
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ExecutionScopeError, match="not the pinned"):
        _runtime(tmp_path)._build_execution_plan(
            _values(
                FINAL_REPORT_SPLIT_ROLE,
                FINAL_REPORT_EXECUTION_PROFILE,
                {"path": ALLOWANCE_RELPATH, "sha256": digest},
            ),
            CARRIER,
            IDENTITY,
        )


@pytest.mark.parametrize("split_role", ["discovery", "dev"])
def test_plan_without_allowance_is_unchanged(tmp_path, split_role):
    profile = "bounded-discovery-probe"
    plan = _runtime(tmp_path)._build_execution_plan(
        _values(split_role, profile), CARRIER, DEV_IDENTITY
    )
    expected = ExecutionPlan(
        run_id=RUN_ID,
        execution_profile=profile,
        carrier_lock_key=CARRIER,
        split_role=split_role,
        split_identity_hash=DEV_IDENTITY,
        planned_model_calls=11,
        planned_gpu_hours=0.5,
        planned_speech_audio_seconds=30,
        protocol_hash=compute_protocol_hash(CONFIG_HASH, ARM, DEV_IDENTITY),
        attempt_id=ATTEMPT_ID,
    )
    assert plan.owner_allowance is None
    assert asdict(plan) == asdict(expected)
    assert json.dumps(asdict(plan), sort_keys=True).encode("utf-8") == json.dumps(
        asdict(expected), sort_keys=True
    ).encode("utf-8")
    assert "owner_allowance" not in asdict(plan)


def test_non_final_report_plan_declaring_an_allowance_is_refused(tmp_path):
    digest = _write_allowance(tmp_path)
    with pytest.raises(ExecutionScopeError, match="only meaningful for split role"):
        _runtime(tmp_path)._build_execution_plan(
            _values(
                "dev",
                "bounded-discovery-probe",
                {"path": ALLOWANCE_RELPATH, "sha256": digest},
            ),
            CARRIER,
            DEV_IDENTITY,
        )


@pytest.mark.parametrize("role", ["final-report", "discovery"])
def test_manifest_retains_allowance_and_validates_round_trip(tmp_path, monkeypatch, role):
    from datetime import datetime, timezone
    from speech_aware_evidence_acquisition.core.bundle import manifest as module

    digest = _write_allowance(tmp_path)
    allowance = {"path": ALLOWANCE_RELPATH, "sha256": digest}
    plan = _runtime(tmp_path)._build_execution_plan(
        _values(role, "bounded-discovery-probe", allowance if role == "final-report" else None),
        CARRIER, IDENTITY if role == "final-report" else DEV_IDENTITY,
    )
    monkeypatch.setattr(module, "_resolve_study_commit", lambda *args: ("a" * 40, []))
    composed = SimpleNamespace(values={}, fragments={}, config_hash=CONFIG_HASH)
    split = SimpleNamespace(split_role=role, carrier_lock_key=CARRIER,
                            identity_hash=plan.split_identity_hash, ids=())
    doc = module._manifest_document(
        repo_root=tmp_path, data_root=tmp_path / "data", composed=composed, plan=plan,
        verified_split=split, session_receipt_path=None, run_dir=tmp_path / "run",
        status="ABORTED", failure_reason="synthetic custody test", result=None,
        now=lambda: datetime.now(timezone.utc),
    )
    expected = asdict(plan)
    if role == "final-report":
        expected["owner_allowance"] = allowance
    assert doc["plan"] == expected
    restored = ExecutionPlan(**doc["plan"])
    restored.validate(source_root=tmp_path)
    if role == "final-report":
        (tmp_path / ALLOWANCE_RELPATH).write_text("{}")
        with pytest.raises(ExecutionScopeError, match="not the pinned"):
            restored.validate(source_root=tmp_path)
