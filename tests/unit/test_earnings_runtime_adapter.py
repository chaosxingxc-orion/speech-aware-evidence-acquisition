"""The E21 factory adapter preserves the frozen call roster and config geometry."""

from __future__ import annotations

import json

import pytest
import test_e21_repair_loop as fixtures

from speech_aware_evidence_acquisition.core.base import CoreError, Registry
from speech_aware_evidence_acquisition.rails.adapters.earnings_runtime import (
    build_runtime_adapter,
    register_runtime_adapter,
)

repair_repo = fixtures.repair_repo


def _values(repo, digest):
    values = dict(fixtures._composed(digest, policy="obs-repair-loop-ojw").values)
    values["serving_geometry"] = {"slots": 6, "slot_tokens": 6144, "max_tokens": 1024}
    values["decoding_params"]["max_tokens"] = 1024
    values["obs_controller_program"] = "phase-direct-only-v1"
    path = repo / "configs/dataset/e21.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"carrier_lock_key": "earnings21-original", "split_name": "discovery"}
        )
    )
    return values


def test_runtime_adapter_reuses_calls_and_explicit_geometry(
    synthetic_world, repair_repo
):
    lock, repo, digest = repair_repo
    values = _values(repo, digest)
    adapter = build_runtime_adapter(
        values, lock, synthetic_world.data_root, repo, dataset_fragment="e21"
    )
    assert (
        tuple(sample.sample_id for sample in adapter.load_split("discovery"))
        == fixtures.E21_IDS
    )
    assert adapter.serving_geometry() == values["serving_geometry"]
    assert adapter.preprocess_plan()["kind"] == "raw-speech-windows"
    assert adapter.instruction(None) == values["task_instruction"]
    adapter.bind_runtime(object(), values)
    with pytest.raises(CoreError, match="split"):
        adapter.load_split("dev")
    with pytest.raises(CoreError, match="complete manifest"):
        adapter.score_response(None, "text")


@pytest.mark.parametrize(
    "change",
    [
        {"serving_geometry": {}},
        {"carrier_lock_key": "earnings22-original"},
        {"split_name": "new-roster"},
        {"policy": "phase-draft-revise-v1"},
        {"serving_geometry": {"slots": 4, "slot_tokens": 6144, "max_tokens": 512}},
    ],
)
def test_adapter_refuses_guessed_geometry_or_different_carrier(
    synthetic_world, repair_repo, change
):
    lock, repo, digest = repair_repo
    values = _values(repo, digest)
    values.update(change)
    with pytest.raises(CoreError):
        build_runtime_adapter(
            values, lock, synthetic_world.data_root, repo, dataset_fragment="e21"
        )


def test_adapter_registry_registration_is_idempotent_and_refuses_replacement(
    monkeypatch,
):
    from speech_aware_evidence_acquisition.core import base

    registry = Registry("task adapter")
    monkeypatch.setattr(base, "TASK_ADAPTERS", registry, raising=False)
    register_runtime_adapter()
    register_runtime_adapter()
    assert registry.resolve("earnings21-original") is build_runtime_adapter
    registry._entries["earnings21-original"] = object()
    with pytest.raises(CoreError):
        register_runtime_adapter()


def test_adapter_refuses_instruction_loss_and_rebinding(synthetic_world, repair_repo):
    lock, repo, digest = repair_repo
    values = _values(repo, digest)
    adapter = build_runtime_adapter(
        values, lock, synthetic_world.data_root, repo, dataset_fragment="e21"
    )
    changed = dict(values, task_instruction="Changed prompt.")
    with pytest.raises(CoreError, match="changed"):
        adapter.bind_runtime(object(), changed)
    with pytest.raises(CoreError, match="task_instruction"):
        build_runtime_adapter(
            dict(values, task_instruction=""),
            lock,
            synthetic_world.data_root,
            repo,
            dataset_fragment="e21",
        )
