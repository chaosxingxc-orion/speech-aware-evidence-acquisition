"""Synthetic contract coverage for local frozen retrieval tool-plan admission."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.contracts import (
    TEXT_ENCODER_PLAN_SCHEMA,
    ExecutionPlan,
    ExecutionScopeError,
    GateClosed,
)
from speech_aware_evidence_acquisition.contracts.tool_plan import (
    TEXT_FACET_ENCODING_PROTOCOL_SCHEMA,
    assert_registered_tool_plan,
)


_SHA_A = "a" * 64
_RUN_ID = "SAEA-TOOL-0001"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _world(tmp_path, *, consumed="no", carrier="slurp"):
    source_root = tmp_path / "source"
    config = source_root / "configs" / "experiment"
    config.mkdir(parents=True)
    (config / "e0-model-free-closure.yaml").write_text(
        "excluded_lock_keys:\n  - fsd50k\n", encoding="utf-8"
    )
    lock_path = tmp_path / "datasets.lock.json"
    lock_raw = json.dumps({"datasets": [{"name": "slurp", "kind": "dataset", "profiles": ["speech-aware-core"]}]}).encode()
    lock_path.write_bytes(lock_raw)
    protocol_path = tmp_path / "protocol.json"
    protocol_raw = b'{"schema":"synthetic-local-frozen-retrieval-v1"}\n'
    protocol_path.write_bytes(protocol_raw)
    ledger = tmp_path / "exposure-ledger.md"
    ledger.write_text(
        "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
        f"| 2026-09-11 | {_RUN_ID} | bounded-discovery-probe | synthetic | local-frozen-retrieval | {carrier} discovery | discovery | {_SHA_A} | {consumed} | 1 | 1 | 1.0 | none | pending | preregistered |\n",
        encoding="utf-8",
    )
    plan = ExecutionPlan(
        run_id=_RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="slurp",
        split_role="discovery",
        split_identity_hash=_SHA_A,
        planned_model_calls=1,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1,
        protocol_hash=_sha(protocol_raw),
        attempt_id="attempt-0001",
    )
    return dict(
        source_root=source_root,
        exposure_ledger=ledger,
        umbrella_lock=lock_path,
        umbrella_lock_sha256=_sha(lock_raw),
        protocol_path=protocol_path,
        protocol_sha256=_sha(protocol_raw),
        plan=plan,
    )


def _allow_wsl(monkeypatch):
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.contracts.tool_plan.assert_wsl_execution_environment",
        lambda: "wsl2",
    )


def _text_world(tmp_path):
    world = _world(tmp_path)
    protocol_raw = json.dumps(
        {"schema": TEXT_FACET_ENCODING_PROTOCOL_SCHEMA}, sort_keys=True
    ).encode("utf-8")
    world["protocol_path"].write_bytes(protocol_raw)
    world["protocol_sha256"] = _sha(protocol_raw)
    ledger = world["exposure_ledger"]
    ledger.write_text(
        ledger.read_text(encoding="utf-8").replace(
            "| 1 | 1 | 1.0 |", "| 1 | 0 | 1.0 |"
        ),
        encoding="utf-8",
    )
    world["plan"] = replace(
        world["plan"],
        schema=TEXT_ENCODER_PLAN_SCHEMA,
        planned_speech_audio_seconds=0,
        protocol_hash=_sha(protocol_raw),
    )
    return world


def test_admits_pinned_local_frozen_retrieval_tool_plan(monkeypatch, tmp_path):
    _allow_wsl(monkeypatch)
    assert assert_registered_tool_plan(**_world(tmp_path)) is None


def test_admits_pinned_text_facet_encoder_plan_with_zero_speech(monkeypatch, tmp_path):
    _allow_wsl(monkeypatch)

    assert assert_registered_tool_plan(**_text_world(tmp_path)) is None


def test_text_encoder_plan_refuses_a_different_pinned_protocol_schema(
    monkeypatch, tmp_path
):
    _allow_wsl(monkeypatch)
    world = _text_world(tmp_path)
    protocol_raw = b'{"schema":"other-text-encoding-protocol-v1"}\n'
    world["protocol_path"].write_bytes(protocol_raw)
    world["protocol_sha256"] = _sha(protocol_raw)
    world["plan"] = replace(world["plan"], protocol_hash=_sha(protocol_raw))

    with pytest.raises(GateClosed, match="text-facet-encoding protocol schema"):
        assert_registered_tool_plan(**world)


@pytest.mark.parametrize("field", ["umbrella_lock_sha256", "protocol_sha256"])
def test_refuses_wrong_pinned_bytes_before_using_documents(monkeypatch, tmp_path, field):
    _allow_wsl(monkeypatch)
    world = _world(tmp_path)
    world[field] = "b" * 64
    with pytest.raises(GateClosed, match="hashes to"):
        assert_registered_tool_plan(**world)


def test_refuses_protocol_plan_mismatch_and_missing_attempt(monkeypatch, tmp_path):
    _allow_wsl(monkeypatch)
    world = _world(tmp_path)
    world["plan"] = replace(world["plan"], protocol_hash="b" * 64)
    with pytest.raises(GateClosed, match="protocol_hash"):
        assert_registered_tool_plan(**world)
    world["plan"] = replace(world["plan"], protocol_hash=_sha(world["protocol_path"].read_bytes()), attempt_id=None)
    with pytest.raises(ExecutionScopeError, match="attempt_id"):
        assert_registered_tool_plan(**world)


@pytest.mark.parametrize("profile", ["model-free-check", "paper-scale-confirmatory"])
def test_refuses_non_admitting_execution_profiles(monkeypatch, tmp_path, profile):
    _allow_wsl(monkeypatch)
    world = _world(tmp_path)
    world["plan"] = replace(world["plan"], execution_profile=profile)
    with pytest.raises(ExecutionScopeError):
        assert_registered_tool_plan(**world)


@pytest.mark.parametrize("consumed, carrier, message", [
    ("yes", "slurp", "already consumed"),
    ("no", "other-carrier", "must name exactly one"),
])
def test_reuses_shared_exposure_carrier_refusals(monkeypatch, tmp_path, consumed, carrier, message):
    _allow_wsl(monkeypatch)
    with pytest.raises(GateClosed, match=message):
        assert_registered_tool_plan(
            **_world(tmp_path, consumed=consumed, carrier=carrier)
        )


def test_refuses_an_unregistered_exposure_row(monkeypatch, tmp_path):
    _allow_wsl(monkeypatch)
    world = _world(tmp_path)
    world["plan"] = replace(world["plan"], run_id="SAEA-TOOL-0002")
    with pytest.raises(GateClosed, match="no pre-registered exposure row"):
        assert_registered_tool_plan(**world)


def test_wsl_guard_precedes_missing_inputs(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.contracts.tool_plan.assert_wsl_execution_environment",
        lambda: (_ for _ in ()).throw(ExecutionScopeError("WSL2")),
    )
    world = _world(tmp_path)
    world["umbrella_lock"] = tmp_path / "missing-lock.json"
    with pytest.raises(ExecutionScopeError, match="WSL2"):
        assert_registered_tool_plan(**world)
