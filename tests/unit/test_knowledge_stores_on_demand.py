"""Keep explicitly tool-owned stores dormant until a role requests them."""
import pytest

from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    KnowledgeStoreError, build_knowledge_store_supply, load_knowledge_store_binding,
)
from test_knowledge_stores import _config


def _dormant(tmp_path):
    config, _ = _config(tmp_path)
    for store in config["knowledge_stores"].values():
        store.pop("phase_supply", None)
    return load_knowledge_store_binding(config, data_root=tmp_path)


def test_explicit_dormant_stores_have_custody_but_zero_automatic_supply(tmp_path):
    binding = _dormant(tmp_path)
    router = build_knowledge_store_supply(
        binding, program=default_phase_program("native-answer-or-tool-v1"),
        data_root=tmp_path, on_demand_store_ids=binding.store_ids,
    )
    assert not hasattr(router, "automatic_for_phase")
    assert all(not specs for specs in router.specs_by_store.values())
    assert router.bootstrap_first_phase(speech_packet_bindings={}, split_identity_hash="a"*64) == ({}, {})
    for store_id in binding.store_ids:
        assert router.receipt["stores"][store_id]["on_demand_target_lookup"] is True
        assert router.receipt["stores"][store_id]["phase_supply"] is None
        assert router.receipt["stores"][store_id]["store_snapshot_sha256"] == binding.store(store_id).snapshot.content_hash()


def test_an_orphan_store_still_requires_an_explicit_route(tmp_path):
    binding = _dormant(tmp_path)
    with pytest.raises(KnowledgeStoreError, match="no phase_supply"):
        build_knowledge_store_supply(
            binding, program=default_phase_program("native-answer-or-tool-v1"), data_root=tmp_path,
        )


@pytest.mark.parametrize("stores", ["slot-contracts", ("foreign",), ("slot-contracts", "slot-contracts")])
def test_dormant_store_declarations_reject_unbound_or_ambiguous_ids(tmp_path, stores):
    binding = _dormant(tmp_path)
    with pytest.raises(KnowledgeStoreError, match="on-demand stores"):
        build_knowledge_store_supply(
            binding, program=default_phase_program("native-answer-or-tool-v1"),
            data_root=tmp_path, on_demand_store_ids=stores,
        )
