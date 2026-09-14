"""TRAIN-only tests for the canonical SLURP candidate-contract provider."""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.data import slurp as slurp_data
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.candidate_contract_lookup import (
    CandidateContractLookupError,
    CandidateContractRequest,
    canonical_sha256,
)
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.slurp_candidate_contracts import (
    PROVIDER_SCHEMA,
    SlurpCandidateContractProvider,
    build_slurp_candidate_contract_provider,
)
from speech_aware_evidence_acquisition.rails.task_adapter import TaskAdapter


class MinimalAdapter(TaskAdapter):
    def load_split(self, split_id):
        return ()

    def build_task_contract(self, sample, obs):
        return "contract"


def _adapter(world):
    return SlurpAdapter(load_lock(world.lock_path), world.data_root)


def test_task_adapter_default_has_no_candidate_contract_provider():
    assert MinimalAdapter().candidate_contract_provider() is None


def test_legacy_adapter_inventory_delegates_to_its_existing_provider(slurp_world):
    adapter = _adapter(slurp_world)
    provider = adapter.candidate_contract_provider()
    inventory = adapter.candidate_inventory()

    assert inventory.candidate_ids == provider.candidate_ids
    assert inventory.source_sha256 == provider.source_sha256
    assert inventory.source_authority == "task-adapter-candidate-contract-provider"


def test_slurp_adapter_prepares_provider_once_from_train_only(slurp_world, monkeypatch):
    real_read = slurp_data._read_jsonl
    seen = []

    def only_train(path):
        seen.append(path.name)
        if path.name != "train.jsonl":
            raise AssertionError(f"candidate provider opened forbidden split {path.name}")
        return real_read(path)

    monkeypatch.setattr(slurp_data, "_read_jsonl", only_train)
    adapter = _adapter(slurp_world)
    assert seen == []
    first = adapter.candidate_contract_provider()
    second = adapter.candidate_contract_provider()

    assert isinstance(first, SlurpCandidateContractProvider)
    assert first is second
    assert seen == ["train.jsonl"]


def test_lookup_returns_deterministic_nonempty_and_empty_profiles_in_request_order(
    slurp_world,
):
    provider = _adapter(slurp_world).candidate_contract_provider()
    result = provider.lookup(("weather_query", "iot_hue_lightdim"))

    assert result.request == CandidateContractRequest(
        ("weather_query", "iot_hue_lightdim")
    )
    assert result.source_sha256 == provider.source_sha256
    assert [item.candidate_id for item in result.candidates] == [
        "weather_query",
        "iot_hue_lightdim",
    ]
    weather, lights = result.candidates
    assert weather.operation == "weather_query"
    assert weather.schema == ()
    assert "0 slot mentions" in weather.contrast
    assert lights.operation == "iot_hue_lightdim"
    assert lights.schema == (("house_place", "observed TRAIN string slot"),)
    assert "1 utterance" in lights.contrast
    assert "1 slot mention" in lights.contrast
    assert "shared observed slot types: none" in lights.contrast
    assert "observed only for this candidate: house_place" in lights.contrast
    assert lights.required_keys == ()
    assert lights.optional_keys == ()
    assert lights.conditional_keys == ()
    assert lights.forbidden_keys == ()


def test_provider_exposes_no_fillers_or_nontrain_labels(slurp_world):
    provider = _adapter(slurp_world).candidate_contract_provider()
    rendered = json.dumps(
        provider.lookup(("iot_hue_lightdim", "weather_query")).as_json(),
        sort_keys=True,
    ) + json.dumps(provider.source_document, sort_keys=True)

    for forbidden in (
        "kitchen",
        "iot_hue_lighton",
        "email_query",
        "alarm_set",
        "audio-101",
        "audio-201",
    ):
        assert forbidden not in rendered


def test_unknown_candidate_is_rejected_against_full_train_inventory(slurp_world):
    provider = _adapter(slurp_world).candidate_contract_provider()
    with pytest.raises(CandidateContractLookupError, match="unknown candidate"):
        provider.lookup(("iot_hue_lighton",))


def test_source_hash_binds_exact_projection_and_is_deterministic(slurp_world):
    first = _adapter(slurp_world).candidate_contract_provider()
    second = _adapter(slurp_world).candidate_contract_provider()
    assert first.source_sha256 == second.source_sha256
    assert first.source_sha256 == (
        "51372165542c4a7c6065a8fe33cb4b8465f69dc18a4c8329b46d42409e73d4c1"
    )
    assert first.candidate_ids == ("iot_hue_lightdim", "weather_query")
    assert first.source_document == second.source_document
    assert first.source_sha256 == canonical_sha256(first.source_document)
    assert first.source_document["schema"] == PROVIDER_SCHEMA
    assert first.source_document["source_split"] == "train"
    assert first.source_document["source_schema_sha256"]
    assert first.source_document["projection_version"] == (
        "saea-slurp-candidate-contract-projection-v1"
    )
    assert first.source_document["retention"] == {
        "min_share": 0.02,
        "examples_per_type": 0,
    }
    assert first.source_document["profiles"] == [
        item.as_json() for item in first.profiles
    ]
    assert "construction_exclusions" not in first.source_document


def test_excluded_provider_binds_exclusions_and_retained_source(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    legacy = build_slurp_candidate_contract_provider(lock, slurp_world.data_root)
    explicit_empty = build_slurp_candidate_contract_provider(
        lock, slurp_world.data_root, excluded_train_utterance_ids=()
    )
    excluded = build_slurp_candidate_contract_provider(
        lock,
        slurp_world.data_root,
        excluded_train_utterance_ids=("slurp:train:000301",),
    )

    assert explicit_empty.source_document == legacy.source_document
    assert explicit_empty.source_sha256 == legacy.source_sha256
    assert excluded.source_sha256 != legacy.source_sha256
    assert excluded.source_sha256 == canonical_sha256(excluded.source_document)
    assert excluded.source_document["construction_exclusions"] == {
        "train_utterance_ids": ["slurp:train:000301"]
    }
    assert excluded.source_document["source_identity_sha256"] != (
        legacy.source_document["source_identity_sha256"]
    )
    assert excluded.source_document["source_utterance_count"] == 1
    profiles = {item.candidate_id: item for item in excluded.profiles}
    empty = profiles["iot_hue_lightdim"]
    assert empty.utterances == 0
    assert empty.slot_mentions == 0
    assert empty.types == ()
    assert excluded.lookup(("iot_hue_lightdim",)).candidates[0].schema == ()


def test_lookup_refuses_duplicate_ids_before_returning_a_result(slurp_world):
    provider = _adapter(slurp_world).candidate_contract_provider()
    with pytest.raises(CandidateContractLookupError, match="duplicate"):
        provider.lookup(("weather_query", "weather_query"))


def test_single_candidate_does_not_claim_a_relative_distinction(slurp_world):
    provider = _adapter(slurp_world).candidate_contract_provider()
    candidate = provider.lookup(("iot_hue_lightdim",)).candidates[0]
    assert "No alternative was requested" in candidate.contrast
    assert "observed only for this candidate" not in candidate.contrast


def test_comparative_projection_marks_shared_types_without_forcing_a_difference(
    slurp_world,
):
    train_path = slurp_world.metadata_dir / "train.jsonl"
    rows = [json.loads(line) for line in train_path.read_text().splitlines()]
    sibling = dict(rows[0])
    sibling.update(
        {
            "slurp_id": 303,
            "intent": "iot_hue_lighton",
            "scenario": "iot",
            "action": "hue_lighton",
        }
    )
    train_path.write_text(
        "\n".join(json.dumps(row) for row in [*rows, sibling]) + "\n",
        encoding="utf-8",
    )

    provider = _adapter(slurp_world).candidate_contract_provider()
    result = provider.lookup(("iot_hue_lightdim", "iot_hue_lighton"))
    for candidate in result.candidates:
        assert "shared observed slot types: house_place" in candidate.contrast
        assert "observed only for this candidate: none" in candidate.contrast


def test_source_document_is_a_detached_copy(slurp_world):
    provider = _adapter(slurp_world).candidate_contract_provider()
    document = provider.source_document
    document["profiles"].clear()
    assert provider.source_document["profiles"]
    assert canonical_sha256(provider.source_document) == provider.source_sha256


def test_adapter_keeps_excluded_and_legacy_catalogs_in_separate_cache_entries(slurp_world):
    adapter = _adapter(slurp_world)
    legacy = adapter.candidate_contract_provider()
    excluded = adapter.candidate_contract_provider(
        excluded_construction_ids=("slurp:train:000301",)
    )
    assert excluded.source_sha256 != legacy.source_sha256
    assert adapter.candidate_contract_provider() is legacy
    assert adapter.candidate_contract_provider(excluded_construction_ids=()) is legacy
    assert adapter.candidate_contract_provider(
        excluded_construction_ids=("slurp:train:000301",)
    ) is excluded
    assert excluded.source_document["source_utterance_count"] == 1
