"""C4b consolidation: ``rails.knowledge_provider`` -- one KnowledgeProvider
interface over the SLURP facet-KB layer (:class:`KbFacetProvider`), the
Audio2Tool dense-centroid layer (:class:`DenseCentroidProvider`), and the
ConEC evidence layer (:class:`ConecContextProvider`).

Every test here is model-free, filesystem-free, and network-free: every
provider is built from synthetic, caller-injected rows/vectors/evidence, and
the local embedding server is never started.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.core.base import EvidenceItem
from speech_aware_evidence_acquisition.rails.a2t_canonical_family_ground import (
    CanonicalContract,
    CanonicalFamilyGround,
)
from speech_aware_evidence_acquisition.rails.a2t_selected_tool_ground import (
    SelectedToolDecisionGround,
)
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.kb_policy import FUSE_POLICY_ID, FuseKnobs, RankWeights
from speech_aware_evidence_acquisition.rails.knowledge import (
    FusionDecision,
    QueryState,
)
from speech_aware_evidence_acquisition.rails.knowledge_build import (
    KB_BUILD_POLICY_ID,
    KbRow,
    KnowledgeBuildSpec,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import A2tKbRow
from speech_aware_evidence_acquisition.rails.knowledge_provider import (
    CONEC_FUSE_POLICY_ID,
    DENSE_CENTROID_FUSE_POLICY_ID,
    ConecContextProvider,
    DenseCentroidProvider,
    KbFacetProvider,
    KNOWLEDGE_PROVIDERS,
    Ranking,
    resolve_provider,
)

_SHA_A = "a" * 64


# ---------------------------------------------------------------------------
# KbFacetProvider
# ---------------------------------------------------------------------------


def _kb_row(uid: str, *, scenario: str, action: str, content: str, speaker: str) -> KbRow:
    sample_id = f"slurp:train:{uid}:audio"
    return KbRow(
        utterance_id=uid,
        content=content,
        scenario=scenario,
        action=action,
        intent=f"{scenario}_{action}",
        entity_types=(),
        entity_fillers={},
        sample_ids=(sample_id,),
        speaker_by_sample_id={sample_id: speaker},
        media_relpath_by_sample_id={sample_id: f"{uid}.flac"},
    )


def _kb_query_state(sample_id: str = "dev:q1", *, retrieved_value_ids: tuple[str, ...] = ()) -> QueryState:
    return QueryState(
        query_id="q1",
        query_sample_id=sample_id,
        speech_packet_id="pkt",
        speech_packet_sha256=_SHA_A,
        use_split_identity_hash=_SHA_A,
        retrieved_value_ids=retrieved_value_ids,
    ).validate()


def _kb_facet_provider() -> tuple[KbFacetProvider, tuple[KbRow, ...]]:
    from speech_aware_evidence_acquisition.data.slurp import SLURP_LOCK_KEY

    rows = (
        _kb_row("u1", scenario="alarm", action="set", content="wake me up at seven", speaker="spk1"),
        _kb_row("u2", scenario="weather", action="query", content="what is the weather today", speaker="spk2"),
    )
    spec = KnowledgeBuildSpec(carrier_lock_key=SLURP_LOCK_KEY, datastore_size=None, seed=20260901)
    provider = KbFacetProvider(
        build_spec=spec,
        forbidden_sample_ids=frozenset(),
        rank_weights=RankWeights(w_cos=0.5, w_prior=0.3, w_agree=0.2),
        fuse_knobs=FuseKnobs(tau=0.1, m=5, c=3, top_l=3),
        top_k_per_dimension=5,
        facet_vectors=lambda facet_id: {
            "facet:content:u1": {"content": (1.0, 0.0)},
            "facet:content:u2": {"content": (0.0, 1.0)},
        }.get(facet_id, {}),
    )
    return provider, rows


def test_kb_facet_provider_build_candidates_fuse_materialize_round_trip():
    provider, rows = _kb_facet_provider()
    snapshot = provider.build(rows, policy_id=KB_BUILD_POLICY_ID)
    assert snapshot.builder_policy_id == KB_BUILD_POLICY_ID

    query_state = _kb_query_state()
    query = {"query_state": query_state, "query_vectors": {"content": (1.0, 0.0)}}
    ranking = provider.candidates(query, k=5)
    assert isinstance(ranking, Ranking)
    assert ranking.entries  # something was recalled
    assert ranking.source == provider.provider_id

    fusion_decision = provider.fuse((ranking,), k=5, policy_id=FUSE_POLICY_ID)
    assert isinstance(fusion_decision, FusionDecision)
    assert fusion_decision.selected_value_ids == ("value:u1",)

    next_state = _kb_query_state(retrieved_value_ids=fusion_decision.selected_value_ids)
    packet = provider.materialize(fusion_decision, query_state=next_state)
    assert packet.dose.n_items == 1
    assert "[value value:u1]" in packet.prompt_block


def test_kb_facet_provider_materialize_matches_rails_runner_supply_for_state():
    # Local import (not module-level): rails.runner is owned and concurrently
    # edited by another agent in this same consolidation effort; this is the
    # one place this test suite depends on it, purely to prove
    # KbFacetProvider.materialize's own independent rendering is byte-
    # identical to the runner's own private _supply_for_state.
    from speech_aware_evidence_acquisition.rails.runner import _supply_for_state

    provider, rows = _kb_facet_provider()
    snapshot = provider.build(rows, policy_id=KB_BUILD_POLICY_ID)

    query = {
        "query_state": _kb_query_state(),
        "query_vectors": {"content": (1.0, 0.0)},
    }
    ranking = provider.candidates(query, k=5)
    fusion_decision = provider.fuse((ranking,), k=5, policy_id=FUSE_POLICY_ID)
    assert fusion_decision.selected_value_ids  # non-empty, otherwise this test is vacuous

    next_state = _kb_query_state(retrieved_value_ids=fusion_decision.selected_value_ids)
    provider_packet = provider.materialize(fusion_decision, query_state=next_state)
    runner_packet = _supply_for_state(snapshot, next_state)

    assert runner_packet is not None
    assert provider_packet.as_json() == runner_packet.as_json()
    assert provider_packet.content_hash() == runner_packet.content_hash()


def test_kb_facet_provider_materialize_refuses_selection_not_visible_in_query_state():
    provider, rows = _kb_facet_provider()
    provider.build(rows, policy_id=KB_BUILD_POLICY_ID)
    query = {"query_state": _kb_query_state(), "query_vectors": {"content": (1.0, 0.0)}}
    ranking = provider.candidates(query, k=5)
    fusion_decision = provider.fuse((ranking,), k=5, policy_id=FUSE_POLICY_ID)

    # query_state with EMPTY retrieved_value_ids -- the selection is not visible.
    stale_state = _kb_query_state(retrieved_value_ids=())
    with pytest.raises(RailsError):
        provider.materialize(fusion_decision, query_state=stale_state)


def test_kb_facet_provider_receipt_carries_hashes_and_policy_ids():
    provider, rows = _kb_facet_provider()
    snapshot = provider.build(rows, policy_id=KB_BUILD_POLICY_ID)
    receipt = provider.receipt()
    assert receipt["provider_id"] == "kb-facet-v1"
    assert receipt["snapshot_sha256"] == snapshot.content_hash()
    assert receipt["build_policy_id"] == KB_BUILD_POLICY_ID
    assert set(snapshot.source_sample_ids) <= set(receipt["source_ids"])
    assert receipt["built_at"] is not None


def test_kb_facet_provider_decontaminate_refuses_identity_overlap():
    provider, rows = _kb_facet_provider()
    snapshot = provider.build(rows, policy_id=KB_BUILD_POLICY_ID)
    overlapping = next(iter(snapshot.source_sample_ids))
    with pytest.raises(RailsError):
        provider.decontaminate([overlapping])
    # allow_overlap=True reports rather than refuses.
    report = provider.decontaminate([overlapping], allow_overlap=True)
    assert report["identity_overlap_count"] == 1
    assert report["identity_overlap_sample_ids"] == (overlapping,)
    # A disjoint evaluation roster never refuses.
    clean = provider.decontaminate(["some:other:sample"])
    assert clean["identity_overlap_count"] == 0


def test_kb_facet_provider_snapshot_sha256_requires_build_first():
    provider, _rows = _kb_facet_provider()
    with pytest.raises(RailsError):
        provider.snapshot_sha256()


# ---------------------------------------------------------------------------
# DenseCentroidProvider
# ---------------------------------------------------------------------------


def _a2t_row(uid: str, *, tool: str, sample_id: str) -> A2tKbRow:
    return A2tKbRow(
        unit_id=f"tier1_direct:{uid}",
        tier="tier1_direct",
        query_idx=int(uid),
        text=f"invocation text {uid}",
        domain="lighting",
        category="control",
        tool_id=1,
        tool_name=tool,
        arg_signature=(),
        arg_pairs=(),
        call_render=f"{tool}()",
        extra_call_names=(),
        call_count=1,
        sample_ids=(sample_id,),
        item_ids=(int(uid),),
        media_relpath_by_sample_id={sample_id: f"{uid}.wav"},
        speaker_ids=("voice1",),
    )


def _selected_tool_decision_ground() -> SelectedToolDecisionGround:
    lighting_contract = CanonicalContract(
        contract_id="c1",
        family_tag="lighting",
        tool_name="setLighting",
        operation="Turn lighting on or off.",
        types=(("state", "boolean"),),
        constraints="",
        legal_key_skeletons=(("state",),),
        required_keys=("state",),
        optional_keys=(),
        conditional_keys=(),
        forbidden_keys=(),
        ordered_keys=("state",),
        defaults="",
        omission_rules=(),
        canonicalization_rules=(),
    )
    weather_contract = CanonicalContract(
        contract_id="c2",
        family_tag="weather",
        tool_name="getWeather",
        operation="Report the current weather.",
        types=(("location", "string"),),
        constraints="",
        legal_key_skeletons=(("location",),),
        required_keys=("location",),
        optional_keys=(),
        conditional_keys=(),
        forbidden_keys=(),
        ordered_keys=("location",),
        defaults="",
        omission_rules=(),
        canonicalization_rules=(),
    )
    ground = CanonicalFamilyGround(
        corpus_sha256="0" * 64,
        family_tags=("lighting", "weather"),
        labels={"lighting": "Lighting", "weather": "Weather"},
        contracts_by_family={
            "lighting": (lighting_contract,),
            "weather": (weather_contract,),
        },
        canonicalizers={},
        compatibility_rules_by_tool={},
    )
    return SelectedToolDecisionGround(ground=ground, compatibility_rules=(), byte_cap=32_768)


def _dense_centroid_provider() -> tuple[DenseCentroidProvider, dict[str, object]]:
    rows = (
        _a2t_row("1", tool="setLighting", sample_id="tier1_direct:000001"),
        _a2t_row("2", tool="getWeather", sample_id="tier1_direct:000002"),
    )
    vectors_by_unit_id = {
        "tier1_direct:1": (1.0, 0.0),
        "tier1_direct:2": (0.0, 1.0),
    }
    provider = DenseCentroidProvider(
        registry_tool_names=("setLighting", "getWeather"),
        decision_ground=_selected_tool_decision_ground(),
    )
    source_rows = {"construction_rows": rows, "vectors_by_unit_id": vectors_by_unit_id}
    return provider, source_rows


def test_dense_centroid_provider_build_candidates_fuse_materialize_round_trip():
    provider, source_rows = _dense_centroid_provider()
    index = provider.build(source_rows, policy_id="saea-a2t-dense-centroid-v1")
    assert index.tool_tier_centroid_count == 2

    ranking = provider.candidates((0.9, 0.1), k=2)
    assert isinstance(ranking, Ranking)
    assert ranking.entries[0].entry_id == "setLighting"

    fused = provider.fuse((ranking,), k=2, policy_id=DENSE_CENTROID_FUSE_POLICY_ID)
    assert isinstance(fused, Ranking)
    assert fused.entries[0].entry_id == "setLighting"

    packet = provider.materialize(fused, query_state=None)
    assert packet.form.value == "text"
    assert "setLighting" in packet.prompt_block


def test_dense_centroid_provider_materialize_prompt_block_equals_selected_tool_decision_card_text():
    provider, source_rows = _dense_centroid_provider()
    provider.build(source_rows, policy_id="saea-a2t-dense-centroid-v1")
    ranking = provider.candidates((0.9, 0.1), k=2)
    fused = provider.fuse((ranking,), k=2, policy_id=DENSE_CENTROID_FUSE_POLICY_ID)

    packet = provider.materialize(fused, query_state=None)

    selected_names = tuple(entry.entry_id for entry in fused.entries)
    expected_packet = _selected_tool_decision_ground().build(selected_names)
    assert packet.prompt_block == expected_packet.text


def test_dense_centroid_provider_receipt_carries_hashes_and_index_sha256():
    provider, source_rows = _dense_centroid_provider()
    index = provider.build(source_rows, policy_id="saea-a2t-dense-centroid-v1")
    receipt = provider.receipt()
    assert receipt["provider_id"] == "dense-centroid-v1"
    assert receipt["snapshot_sha256"] == index.index_sha256
    assert receipt["index_sha256"] == index.index_sha256
    assert receipt["build_policy_id"] == "saea-a2t-dense-centroid-v1"


def test_dense_centroid_provider_decontaminate_refuses_identity_overlap():
    provider, source_rows = _dense_centroid_provider()
    provider.build(source_rows, policy_id="saea-a2t-dense-centroid-v1")
    with pytest.raises(RailsError):
        provider.decontaminate(["tier1_direct:000001"])
    clean = provider.decontaminate(["tier1_direct:999999"])
    assert clean["identity_overlap_count"] == 0


def test_dense_centroid_provider_fuse_refuses_unknown_ranking():
    provider, source_rows = _dense_centroid_provider()
    provider.build(source_rows, policy_id="saea-a2t-dense-centroid-v1")
    other_provider, other_rows = _dense_centroid_provider()
    other_provider.build(other_rows, policy_id="saea-a2t-dense-centroid-v1")
    foreign_ranking = other_provider.candidates((0.9, 0.1), k=2)
    with pytest.raises(RailsError):
        provider.fuse((foreign_ranking,), k=2, policy_id=DENSE_CENTROID_FUSE_POLICY_ID)


# ---------------------------------------------------------------------------
# ConecContextProvider
# ---------------------------------------------------------------------------


def _evidence_item(sample_id: str, content: str) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=f"conec/{sample_id}",
        source_uri=f"conec://contexts/{sample_id}.txt",
        content=content,
        provenance={
            "lock_key": "conec",
            "relpath": f"contexts/{sample_id}.txt",
            "sha256": "0" * 64,
        },
    )


def _conec_provider() -> tuple[ConecContextProvider, dict[str, tuple[EvidenceItem, ...]]]:
    source_rows = {
        "earnings21:s1": (_evidence_item("earnings21:s1", "Q1 revenue context for s1."),),
        "earnings21:s2": (_evidence_item("earnings21:s2", "Q1 revenue context for s2."),),
        "earnings21:s3": (_evidence_item("earnings21:s3", "Q1 revenue context for s3."),),
    }
    provider = ConecContextProvider(evidence_source_id="conec-contexts")
    return provider, source_rows


def test_conec_context_provider_build_candidates_fuse_materialize_round_trip():
    provider, source_rows = _conec_provider()
    built = provider.build(source_rows, policy_id="conec-contexts")
    assert set(built) == set(source_rows)

    ranking = provider.candidates("earnings21:s1", k=5)
    assert isinstance(ranking, Ranking)
    assert ranking.entries[0].entry_id == "conec/earnings21:s1"

    fused = provider.fuse((ranking,), k=5, policy_id=CONEC_FUSE_POLICY_ID)
    assert isinstance(fused, Ranking)

    packet = provider.materialize(fused, query_state=None)
    assert "[evidence conec/earnings21:s1] Q1 revenue context for s1." in packet.prompt_block


def test_conec_context_provider_negative_control_yields_a_different_samples_context():
    provider, source_rows = _conec_provider()
    provider.build(source_rows, policy_id="conec-contexts")

    plain = provider.candidates("earnings21:s1", k=5, negative_control=False)
    with_negative = provider.candidates("earnings21:s1", k=5, negative_control=True)

    plain_ids = {entry.entry_id for entry in plain.entries}
    negative_ids = {entry.entry_id for entry in with_negative.entries}
    added = negative_ids - plain_ids
    assert added, "negative_control=True must add at least one extra entry"
    assert all(entry_id.startswith("negctrl:") for entry_id in added)

    packet = provider.materialize(with_negative, query_state=None)
    # The genuine sample's own context is present...
    assert "Q1 revenue context for s1." in packet.prompt_block
    # ...and so is a DIFFERENT sample's context (the rotated negative control),
    # never the queried sample's own content repeated under a different id.
    assert "Q1 revenue context for s2." in packet.prompt_block


def test_conec_context_provider_receipt_and_decontaminate():
    provider, source_rows = _conec_provider()
    built = provider.build(source_rows, policy_id="conec-contexts")
    receipt = provider.receipt()
    assert receipt["provider_id"] == "conec-context-v1"
    assert receipt["evidence_source_id"] == "conec-contexts"
    assert len(receipt["snapshot_sha256"]) == 64
    assert set(receipt["source_ids"]) == set(built)

    with pytest.raises(RailsError):
        provider.decontaminate(["earnings21:s1"])
    clean = provider.decontaminate(["earnings21:not-built"])
    assert clean["identity_overlap_count"] == 0


def test_conec_context_provider_rejects_unregistered_evidence_source():
    with pytest.raises(RailsError):
        ConecContextProvider(evidence_source_id="not-a-registered-source")


def test_conec_context_provider_build_rejects_mismatched_policy_id():
    provider, source_rows = _conec_provider()
    with pytest.raises(RailsError):
        provider.build(source_rows, policy_id="conec-names")


# ---------------------------------------------------------------------------
# KNOWLEDGE_PROVIDERS registry / resolve_provider
# ---------------------------------------------------------------------------


def test_knowledge_providers_registry_resolves_every_registered_provider():
    assert set(KNOWLEDGE_PROVIDERS.names()) == {
        "kb-facet-v1",
        "dense-centroid-v1",
        "conec-context-v1",
        # KU-S4N, 2026-09-09: the SLURP intent-narrowing view, whose per-row
        # decision is a sha256-pinned candidate bank rather than a cosine.
        "slurp-intent-candidates-v1",
        # Candidate-conditioned explanatory values stay behind the same
        # registered provider seam and released named-store custody.
        "slurp-candidate-semantic-v1",
        "audio2tool-candidate-semantic-v1",
        "source-scoped-context-v1",
        # Stage-3 S3-6 (2026-09-22): the stage3-deltas store's candidate-bound,
        # prior_score-capped selector. Registered so a baseline fragment's
        # "provider": "stage3-delta-candidate-bound-v1" resolves honestly; NOT
        # YET reachable from a live flight (rails/stage3_delta_supply.py module
        # docstring: build_knowledge_store_supply does not recognize this
        # provider id in its context_supply/candidate_supply dispatch yet).
        "stage3-delta-candidate-bound-v1",
        # Stage-3 S3-4s (owner decision 106, 2026-09-23): the same store's
        # UNCONDITIONAL, node-filtered selector -- the Perception route, whose
        # node produces the candidate list and so has nothing to bind against.
        "stage3-delta-unconditional-v1",
    }


def test_resolve_provider_constructs_conec_context_provider():
    provider = resolve_provider("conec-context-v1", evidence_source_id="conec-names")
    assert isinstance(provider, ConecContextProvider)
    assert provider.provider_id == "conec-context-v1"


def test_resolve_provider_unknown_id_refuses():
    with pytest.raises(Exception):
        resolve_provider("no-such-provider-id")
