from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.slurp_hypothesis_candidate_contract_view import (
    SlurpHypothesisCandidateContractStateView,
    SlurpHypothesisCandidateContractViewError,
    build_slurp_hypothesis_candidate_contract_view,
)
from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import (
    HYPOTHESIS_SEMANTICS,
    HYPOTHESIS_STATE_SCHEMA,
)

SAMPLE_ID = "slurp:devel:000101:audio-101.flac"


def _artifact(*intent_ids: str, sample_id: str = SAMPLE_ID) -> AgentStateArtifact:
    payload = {
        "schema": HYPOTHESIS_STATE_SCHEMA,
        "semantics": HYPOTHESIS_SEMANTICS,
        "sample_id": sample_id,
        "candidates": [
            {
                "intent_id": intent_id,
                "distinction": f"Alternative {intent_id}.",
                "evidence_refs": ["speech:current-query"],
                "unresolved_fields": ["entity"],
            }
            for intent_id in intent_ids
        ],
    }
    content = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    return AgentStateArtifact(
        state_id=f"hypotheses:{sample_id}",
        state_kind="phase:hypotheses",
        content=content,
        source_query_state_sha256="a" * 64,
        source_response_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        producer_policy_id="phase-hypotheses-v1",
        cited_value_ids=(),
    ).validate()


def _provider(slurp_world):
    adapter = SlurpAdapter(
        load_lock(slurp_world.lock_path), slurp_world.data_root
    )
    return adapter.candidate_contract_provider()


def _view(slurp_world):
    provider = _provider(slurp_world)
    return build_slurp_hypothesis_candidate_contract_view(
        load_lock(slurp_world.lock_path),
        slurp_world.data_root,
        candidate_source_sha256=provider.source_sha256,
        max_candidates=3,
    )


def test_real_train_provider_view_is_compact_ordered_and_filler_free(slurp_world):
    view = _view(slurp_world)
    rendered = view.render_state(
        _artifact("weather_query", "iot_hue_lightdim"),
        sample_id=SAMPLE_ID,
    )

    document = json.loads(rendered)
    assert list(document) == ["candidates"]
    assert [item["candidate_id"] for item in document["candidates"]] == [
        "weather_query",
        "iot_hue_lightdim",
    ]
    assert all(set(item) == {"candidate_id", "schema", "contrast"} for item in document["candidates"])
    assert document["candidates"][0]["schema"] == []
    assert document["candidates"][1]["schema"] == [
        {"name": "house_place", "type": "observed TRAIN string slot"}
    ]
    assert "observed associations, not required or forbidden fields" in rendered
    assert "kitchen" not in rendered
    assert "source_sha256" not in rendered
    assert "evidence_status" not in rendered


def test_hard_first_and_joint_consumers_get_byte_identical_view(slurp_world):
    view = _view(slurp_world)
    artifact = _artifact("iot_hue_lightdim", "weather_query")
    assert view.render_state(artifact, sample_id=SAMPLE_ID) == view.render_state(
        artifact, sample_id=SAMPLE_ID
    )


def test_view_validates_source_bound_sample_and_candidate_limit(slurp_world):
    view = _view(slurp_world)
    with pytest.raises(SlurpHypothesisCandidateContractViewError, match="sample_id"):
        view.render_state(_artifact("weather_query", sample_id="slurp:devel:foreign"), sample_id=SAMPLE_ID)

    three = _artifact("weather_query", "iot_hue_lightdim", "alarm_set")
    with pytest.raises(SlurpHypothesisCandidateContractViewError, match="at most 1"):
        view.with_max_candidates(1).render_state(three, sample_id=SAMPLE_ID)


def test_factory_refuses_foreign_source_pin(slurp_world):
    provider = _provider(slurp_world)
    with pytest.raises(SlurpHypothesisCandidateContractViewError, match="source"):
        build_slurp_hypothesis_candidate_contract_view(
            load_lock(slurp_world.lock_path),
            slurp_world.data_root,
            candidate_source_sha256="b" * 64,
            max_candidates=3,
        )
    assert provider.source_sha256


def test_factory_builds_the_canonical_provider_once(monkeypatch, slurp_world):
    import speech_aware_evidence_acquisition.rails.slurp_hypothesis_candidate_contract_view as module

    provider = _provider(slurp_world)
    calls = []

    def build_once(lock, root):
        calls.append((lock, root))
        return provider

    monkeypatch.setattr(module, "build_slurp_candidate_contract_provider", build_once)
    view = module.build_slurp_hypothesis_candidate_contract_view(
        load_lock(slurp_world.lock_path),
        slurp_world.data_root,
        candidate_source_sha256=provider.source_sha256,
        max_candidates=3,
    )
    assert len(calls) == 1
    assert view.provider is provider


def test_view_rejects_tampered_hypothesis_response(slurp_world):
    view = _view(slurp_world)
    tampered = replace(_artifact("weather_query"), source_response_sha256="b" * 64)
    with pytest.raises(SlurpHypothesisCandidateContractViewError, match="source response"):
        view.render_state(tampered, sample_id=SAMPLE_ID)


def test_view_rejects_a_provider_result_from_a_foreign_source(slurp_world):
    canonical = _provider(slurp_world)

    class ForeignResultProvider:
        source_sha256 = canonical.source_sha256
        candidate_ids = canonical.candidate_ids

        def lookup(self, candidate_ids):
            result = canonical.lookup(candidate_ids)
            return replace(result, source_sha256="c" * 64)

    view = SlurpHypothesisCandidateContractStateView(
        provider=ForeignResultProvider(),
        candidate_source_sha256=canonical.source_sha256,
        max_candidates=3,
    )
    with pytest.raises(SlurpHypothesisCandidateContractViewError, match="result source"):
        view.render_state(_artifact("weather_query"), sample_id=SAMPLE_ID)


def test_view_rejects_a_same_source_result_for_the_wrong_request(slurp_world):
    canonical = _provider(slurp_world)

    class WrongRequestProvider:
        source_sha256 = canonical.source_sha256
        candidate_ids = canonical.candidate_ids

        def lookup(self, candidate_ids):
            assert candidate_ids == ("weather_query",)
            return canonical.lookup(("iot_hue_lightdim",))

    view = SlurpHypothesisCandidateContractStateView(
        provider=WrongRequestProvider(),
        candidate_source_sha256=canonical.source_sha256,
        max_candidates=3,
    )
    with pytest.raises(SlurpHypothesisCandidateContractViewError, match="different candidate request"):
        view.render_state(_artifact("weather_query"), sample_id=SAMPLE_ID)


def test_callable_view_requires_the_full_source_bound_artifact(slurp_world):
    view = _view(slurp_world)
    with pytest.raises(SlurpHypothesisCandidateContractViewError, match="full AgentStateArtifact"):
        view("hypothesis text")
