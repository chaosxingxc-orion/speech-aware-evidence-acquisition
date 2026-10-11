"""The Earnings-22 runtime adapter is a thin derivation of the Earnings-21 one (design 2b.2).

Model-free, on the synthetic world: the carrier and split are Earnings-22's, every other rule is
Earnings-21's, and the shared factory can resolve the carrier. No flight is registered.
"""

from __future__ import annotations

import json

import pytest
import test_e21_repair_loop as fixtures

from speech_aware_evidence_acquisition.core.base import CoreError, Registry
from speech_aware_evidence_acquisition.rails.adapters import earnings22_runtime as e22
from speech_aware_evidence_acquisition.rails.adapters.earnings_runtime import Earnings21RuntimeAdapter

repair_repo = fixtures.repair_repo


def _values(repo, digest, *, split="dev", carrier="earnings22-original"):
    values = dict(fixtures._composed(digest, policy="obs-repair-loop-ojw").values)
    values["serving_geometry"] = {"slots": 6, "slot_tokens": 6144, "max_tokens": 1024}
    values["decoding_params"]["max_tokens"] = 1024
    values["obs_controller_program"] = "phase-direct-only-v1"
    values["carrier_lock_key"] = carrier
    values["split_name"] = split
    path = repo / "configs/dataset/e22.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"carrier_lock_key": carrier, "split_name": split}))
    return values


def test_the_adapter_is_a_thin_derivation_of_the_e21_runtime_adapter():
    assert issubclass(e22.Earnings22RuntimeAdapter, Earnings21RuntimeAdapter)
    assert e22.Earnings22RuntimeAdapter.CARRIER_LOCK_KEY == "earnings22-original"
    assert e22.Earnings22RuntimeAdapter.DEFAULT_SPLIT == "dev"
    own = {name for name in vars(e22.Earnings22RuntimeAdapter)
           if not name.startswith("__") and name != "_abc_impl"}
    assert own == {"CARRIER_LOCK_KEY", "DEFAULT_SPLIT"}


def test_the_adapter_loads_the_e22_dev_split_with_the_e21_rules(synthetic_world, repair_repo):
    lock, repo, digest = repair_repo
    values = _values(repo, digest)
    adapter = e22.build_runtime_adapter(values, lock, synthetic_world.data_root, repo, dataset_fragment="e22")
    samples = adapter.load_split("dev")
    assert samples and {s.carrier_lock_key for s in samples} == {"earnings22-original"}
    assert adapter.serving_geometry() == values["serving_geometry"]
    assert adapter.preprocess_plan()["kind"] == "raw-speech-windows"
    adapter.bind_runtime(object(), values)
    with pytest.raises(CoreError, match="split"):
        adapter.load_split("discovery")
    with pytest.raises(CoreError, match="complete manifest"):
        adapter.score_response(None, "text")


def test_the_adapter_refuses_the_other_carrier_and_any_subset(synthetic_world, repair_repo):
    lock, repo, digest = repair_repo
    values = _values(repo, digest, carrier="earnings21-original")
    with pytest.raises(CoreError, match="E22 runtime adapter requires earnings22-original"):
        e22.build_runtime_adapter(values, lock, synthetic_world.data_root, repo, dataset_fragment="e22")
    values = _values(repo, digest, split="e22-synthetic-construction")
    with pytest.raises(CoreError, match="requires e21_runtime_subset metadata"):
        e22.build_runtime_adapter(values, lock, synthetic_world.data_root, repo, dataset_fragment="e22")


def _subset_values(repo, digest, *, sample_id, parent="dev", role="dev", carrier="earnings22-original", stored_hash=None):
    from speech_aware_evidence_acquisition.reproduction.sampling import split_identity_hash

    name = "e22-synthetic-construction"
    values = _values(repo, digest, split=name)
    (repo / "configs/dataset/e22.json").write_text(json.dumps({
        "carrier_lock_key": "earnings22-original", "split_name": name,
        "e21_runtime_subset": {"receipt_split_name": name, "parent_split": parent, "subset_role": "construction"},
    }))
    key = f"{carrier}:{sample_id}"
    receipt = repo / f"docs/receipts/probe-samples/{name}.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({
        "carrier": carrier, "split_role": role, "items": [{"id": sample_id, "key": key}],
        "split_identity_hash": stored_hash or split_identity_hash([key]),
    }))
    return values


def test_the_adapter_loads_a_verified_dev_subset_and_refuses_a_foreign_one(synthetic_world, repair_repo):
    lock, repo, digest = repair_repo
    whole = e22.build_runtime_adapter(
        _values(repo, digest), lock, synthetic_world.data_root, repo, dataset_fragment="e22")
    first = whole.load_split("dev")[0].sample_id
    values = _subset_values(repo, digest, sample_id=first)
    adapter = e22.build_runtime_adapter(values, lock, synthetic_world.data_root, repo, dataset_fragment="e22")
    assert tuple(s.sample_id for s in adapter.load_split(values["split_name"])) == (first,)
    with pytest.raises(CoreError, match="must derive from frozen dev"):
        e22.build_runtime_adapter(_subset_values(repo, digest, sample_id=first, parent="discovery"),
                                  lock, synthetic_world.data_root, repo, dataset_fragment="e22")
    with pytest.raises(CoreError, match="with dev role"):
        e22.build_runtime_adapter(_subset_values(repo, digest, sample_id=first, role="discovery"),
                                  lock, synthetic_world.data_root, repo, dataset_fragment="e22")
    with pytest.raises(CoreError, match="outside frozen dev"):
        e22.build_runtime_adapter(_subset_values(repo, digest, sample_id="9999999"),
                                  lock, synthetic_world.data_root, repo, dataset_fragment="e22")
    with pytest.raises(CoreError, match="receipt refused"):
        e22.build_runtime_adapter(_subset_values(repo, digest, sample_id=first, stored_hash="0" * 64),
                                  lock, synthetic_world.data_root, repo, dataset_fragment="e22")


def test_registration_is_idempotent_and_never_replaces_an_owner(monkeypatch):
    from speech_aware_evidence_acquisition.core import base

    registry = Registry("task adapters (test)")
    monkeypatch.setattr(base, "TASK_ADAPTERS", registry)
    e22.register_runtime_adapter()
    e22.register_runtime_adapter()
    assert registry.resolve("earnings22-original") is e22.build_runtime_adapter
    other = Registry("task adapters (test 2)")
    other.register("earnings22-original", object())
    monkeypatch.setattr(base, "TASK_ADAPTERS", other)
    with pytest.raises(CoreError, match="registered differently"):
        e22.register_runtime_adapter()


def test_the_shared_factory_registers_the_e22_adapter():
    from speech_aware_evidence_acquisition.core.base import TASK_ADAPTERS
    from speech_aware_evidence_acquisition.core.flight.factory import register_builtin_task_adapters

    register_builtin_task_adapters()
    assert TASK_ADAPTERS.resolve("earnings22-original") is e22.build_runtime_adapter
    assert TASK_ADAPTERS.resolve("earnings21-original") is not e22.build_runtime_adapter
