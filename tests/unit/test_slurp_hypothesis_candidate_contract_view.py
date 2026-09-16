from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.candidate_contract_lookup import (
    CandidateContractEvidence,
    CandidateContractLookupResult,
    CandidateContractRequest,
)
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


def test_view_renders_five_candidates_and_rejects_bounds_above_inventory(slurp_world):
    intent_ids = tuple(f"intent_{index}" for index in range(5))

    class FiveProvider:
        source_sha256 = "d" * 64
        candidate_ids = intent_ids

        def lookup(self, candidate_ids):
            request = CandidateContractRequest.from_ids(candidate_ids)
            return CandidateContractLookupResult(
                request=request,
                source_sha256=self.source_sha256,
                candidates=tuple(
                    CandidateContractEvidence(
                        candidate_id=candidate_id,
                        operation=candidate_id,
                        schema=(),
                        contrast=f"Contrast for {candidate_id}.",
                    ).validate()
                    for candidate_id in candidate_ids
                ),
            ).validate()

    provider = FiveProvider()
    view = SlurpHypothesisCandidateContractStateView(
        provider=provider,
        candidate_source_sha256=provider.source_sha256,
        max_candidates=5,
    )
    document = json.loads(
        view.render_state(_artifact(*intent_ids), sample_id=SAMPLE_ID)
    )
    assert [row["candidate_id"] for row in document["candidates"]] == list(
        intent_ids
    )
    with pytest.raises(
        SlurpHypothesisCandidateContractViewError, match="legal intent count"
    ):
        view.with_max_candidates(6)


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


def test_registered_state_view_supplies_identical_bytes_through_phase_builder(
    slurp_world, monkeypatch
):
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.data import lock as lock_module
    from speech_aware_evidence_acquisition.rails.phase_material import (
        PhaseMaterialSpec, build_material_for_phase,
    )

    monkeypatch.setattr(lock_module, "umbrella_lock_path", lambda: slurp_world.lock_path)
    monkeypatch.setattr(lock_module, "data_root", lambda: slurp_world.data_root)
    provider = _provider(slurp_world)
    artifact = _artifact("iot_hue_lightdim", "weather_query")
    spec = PhaseMaterialSpec(
        phase="slots", purpose="fill", instruction_template="probes/slots.txt",
        predecessor_binding="append-sealed-state",
        state_fill="slurp-hypothesis-candidate-contracts-for-state-v1",
        fill_params={"candidate_source_sha256": provider.source_sha256, "max_candidates": 3},
    ).validate()
    suffixes = []
    for instruction in ("Keep the first intent.", "Select among the candidates."):
        material = build_material_for_phase(
            {"slots": spec}, program_id="phase-slots-given-intent-v1",
            static_text_by_phase={"slots": instruction}, response_format_by_phase={},
        )("slots", SimpleNamespace(sample_id=SAMPLE_ID), {SAMPLE_ID: artifact})
        suffixes.append(material.instruction[len(instruction):])
    assert suffixes[0] == suffixes[1]
    assert "observed associations, not required or forbidden fields" in suffixes[0]


def test_capacity_and_live_material_render_identical_full_state_view(slurp_world):
    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.core.flight.runtime import render_phase_prompt_envelopes
    from speech_aware_evidence_acquisition.rails.phase_material import (
        PhaseMaterialSpec, build_material_for_phase, render_phase_envelope,
    )

    view = _view(slurp_world)
    artifact = _artifact("weather_query", "iot_hue_lightdim")
    spec = PhaseMaterialSpec(
        phase="slots", purpose="fill", instruction_template="probes/slots.txt",
        predecessor_binding="append-sealed-state",
        state_fill="slurp-hypothesis-candidate-contracts-for-state-v1",
    ).validate()
    specs = {"slots": spec}
    static = {"slots": "Select one candidate and extract its entities."}
    material = build_material_for_phase(
        specs, program_id="phase-slots-given-intent-v1",
        static_text_by_phase=static, response_format_by_phase={},
        state_fill_by_phase={"slots": view},
    )("slots", SimpleNamespace(sample_id=SAMPLE_ID), {SAMPLE_ID: artifact})
    packet = {"packet_id": "slurp/devel/query", "sha256": "a" * 64}
    measured = render_phase_prompt_envelopes(
        program_id="phase-slots-given-intent-v1", phase_names=("slots",),
        specs=specs, static_text_by_phase=static, system_text="Speech task.",
        prompt_order="speech-query-prefix-v2", packet_descriptor=packet,
        sample_id=SAMPLE_ID, sealed_states_by_phase={"slots": {SAMPLE_ID: artifact}},
        state_fill_by_phase={"slots": view}, completion_token_ceiling=256,
    )["slots"]
    expected = render_phase_envelope(
        "Speech task.", material.instruction,
        prompt_order="speech-query-prefix-v2", packet_descriptor=packet,
        contact_id=f"phase-slots-given-intent-v1:slots:{SAMPLE_ID}",
    )
    assert measured == expected


def test_capacity_full_state_view_refuses_unknown_predecessor(slurp_world):
    from speech_aware_evidence_acquisition.core.flight.runtime import render_phase_prompt_envelopes
    from speech_aware_evidence_acquisition.rails.phase_material import (
        PhaseMaterialError, PhaseMaterialSpec,
    )

    spec = PhaseMaterialSpec(
        phase="slots", purpose="fill", instruction_template="probes/slots.txt",
        predecessor_binding="append-sealed-state",
        state_fill="slurp-hypothesis-candidate-contracts-for-state-v1",
    ).validate()
    with pytest.raises(PhaseMaterialError, match="full predecessor artifact"):
        render_phase_prompt_envelopes(
            program_id="phase-slots-given-intent-v1", phase_names=("slots",),
            specs={"slots": spec}, static_text_by_phase={"slots": "Fill."},
            system_text="Speech task.", prompt_order="speech-query-prefix-v2",
            packet_descriptor={"packet_id": "slurp/devel/query", "sha256": "a" * 64},
            sample_id=SAMPLE_ID, state_fill_by_phase={"slots": _view(slurp_world)},
            completion_token_ceiling=256,
        )
