"""Rails contract dataclasses (B0): round-trip/hash-stability + the legality
gate reusing core.legality's own either-field rule.
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path
import threading
import time

import pytest

from speech_aware_evidence_acquisition.core.legality import LegalityError
from speech_aware_evidence_acquisition.core.model import (
    FrozenCoreError,
    inspect_legacy_cached_speech_feature_cache,
    legacy_audio_feature_cache_key,
    materialize_legacy_cached_speech_feature_packet,
    materialize_legacy_cached_speech_feature_packets,
)
from speech_aware_evidence_acquisition.rails import (
    AgentStateArtifact,
    AgentStepTransition,
    AudioRef,
    ConsumptionOutcome,
    ConsumptionRecord,
    ConsumptionTrace,
    EvidenceItem,
    EvidenceSet,
    FusionDecision,
    KeyFacet,
    KnowledgeSnapshot,
    ObsPacket,
    RailsError,
    RetrievalKeyKind,
    RetrievalParams,
    QueryState,
    RankedFacet,
    RankResult,
    SpanRef,
    SupplyDose,
    SupplyForm,
    SupplyItem,
    SupplyPacket,
    ValueBundle,
    assert_agent_step_binding,
    assert_knowledge_use_binding,
    build_consumption_trace,
    classify_outcome,
    default_obs_packet,
)
from speech_aware_evidence_acquisition.rails.knowledge import (
    EXTERNAL_GOVERNED_PARTITION_ROLE,
)

_SHA_A = "a" * 64
_SHA_B = "b" * 64
_SHA_C = "c" * 64


def _write_legacy_cache_chunk(
    cache_dir, audio_bytes, ordinal, *, n_tokens=2, n_embd=4, trailing=b""
):
    key = legacy_audio_feature_cache_key(audio_bytes)
    feature_bytes = struct.pack(f"<{n_tokens * n_embd}f", *[1.0] * (n_tokens * n_embd))
    path = cache_dir / f"{key}_o{ordinal}.feat"
    path.write_bytes(struct.pack("<QQ", n_tokens, n_embd) + feature_bytes + trailing)
    return path


def test_legacy_cache_inspection_reports_exact_identity_and_ordered_chunks(tmp_path):
    audio = tmp_path / "audio.flac"
    audio_bytes = b"governed-audio"
    audio.write_bytes(audio_bytes)
    legacy = tmp_path / "legacy-cache"
    legacy.mkdir()
    paths = [
        _write_legacy_cache_chunk(legacy, audio_bytes, 0, n_tokens=2),
        _write_legacy_cache_chunk(legacy, audio_bytes, 1, n_tokens=3),
    ]

    inspection = inspect_legacy_cached_speech_feature_cache(
        audio_path=audio,
        legacy_cache_dir=legacy,
        expected_n_embd=4,
    )

    assert inspection.audio_sha256 == hashlib.sha256(audio_bytes).hexdigest()
    assert inspection.cache_key == legacy_audio_feature_cache_key(audio_bytes)
    assert [chunk.ordinal for chunk in inspection.chunks] == [0, 1]
    assert [chunk.relative_filename for chunk in inspection.chunks] == [
        path.name for path in paths
    ]
    assert [chunk.file_sha256 for chunk in inspection.chunks] == [
        hashlib.sha256(path.read_bytes()).hexdigest() for path in paths
    ]
    assert [chunk.file_size for chunk in inspection.chunks] == [
        path.stat().st_size for path in paths
    ]
    assert [(chunk.n_tokens, chunk.n_embd) for chunk in inspection.chunks] == [
        (2, 4),
        (3, 4),
    ]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda path: path.unlink(), "has no ordinal zero"),
        (
            lambda path: path.write_bytes(struct.pack("<QQ", 2, 3) + b"\x00" * 24),
            "decoder dimension",
        ),
        (
            lambda path: path.write_bytes(struct.pack("<QQ", 2, 4) + b"\x00" * 33),
            "byte length",
        ),
    ],
)
def test_legacy_cache_inspection_refuses_invalid_chunks(tmp_path, mutate, message):
    audio = tmp_path / "audio.flac"
    audio_bytes = b"governed-audio"
    audio.write_bytes(audio_bytes)
    legacy = tmp_path / "legacy-cache"
    legacy.mkdir()
    path = _write_legacy_cache_chunk(legacy, audio_bytes, 0)

    mutate(path)
    with pytest.raises(FrozenCoreError, match=message):
        inspect_legacy_cached_speech_feature_cache(
            audio_path=audio,
            legacy_cache_dir=legacy,
            expected_n_embd=4,
        )


def test_legacy_cache_inspection_refuses_noncanonical_ordinal_but_promotion_keeps_legacy(
    tmp_path,
):
    audio = tmp_path / "audio.flac"
    audio_bytes = b"governed-audio"
    audio.write_bytes(audio_bytes)
    legacy = tmp_path / "legacy-cache"
    legacy.mkdir()
    canonical = _write_legacy_cache_chunk(legacy, audio_bytes, 0)
    alias = legacy / canonical.name.replace("_o0.", "_o00.")
    canonical.rename(alias)

    with pytest.raises(FrozenCoreError, match="not canonical"):
        inspect_legacy_cached_speech_feature_cache(
            audio_path=audio,
            legacy_cache_dir=legacy,
            expected_n_embd=4,
        )

    packet = materialize_legacy_cached_speech_feature_packet(
        feature_root=tmp_path / "packets",
        packet_id="slurp/dev/example",
        audio_path=audio,
        legacy_cache_dir=legacy,
        encoder_receipt_sha256="1" * 64,
        decoder_gguf_sha256="2" * 64,
        mmproj_sha256="3" * 64,
        expected_n_embd=4,
        causal_attention=True,
    )
    assert packet.chunks[0].ordinal == 0


def test_legacy_cache_inspection_refuses_chunk_symlink_outside_cache(tmp_path):
    audio = tmp_path / "audio.flac"
    audio_bytes = b"governed-audio"
    audio.write_bytes(audio_bytes)
    legacy = tmp_path / "legacy-cache"
    legacy.mkdir()
    external = tmp_path / "external.feat"
    external.write_bytes(
        struct.pack("<QQ", 2, 4) + b"\x00" * 32
    )
    key = legacy_audio_feature_cache_key(audio_bytes)
    (legacy / f"{key}_o0.feat").symlink_to(external)

    with pytest.raises(FrozenCoreError, match="outside the cache directory"):
        inspect_legacy_cached_speech_feature_cache(
            audio_path=audio,
            legacy_cache_dir=legacy,
            expected_n_embd=4,
        )


def test_legacy_cache_inspection_refuses_gapped_ordinals(tmp_path):
    audio = tmp_path / "audio.flac"
    audio_bytes = b"governed-audio"
    audio.write_bytes(audio_bytes)
    legacy = tmp_path / "legacy-cache"
    legacy.mkdir()
    _write_legacy_cache_chunk(legacy, audio_bytes, 0)
    _write_legacy_cache_chunk(legacy, audio_bytes, 2)

    with pytest.raises(FrozenCoreError, match="not contiguous"):
        inspect_legacy_cached_speech_feature_cache(
            audio_path=audio,
            legacy_cache_dir=legacy,
            expected_n_embd=4,
        )


def test_legacy_cache_inspection_refuses_duplicate_ordinals(tmp_path, monkeypatch):
    audio = tmp_path / "audio.flac"
    audio_bytes = b"governed-audio"
    audio.write_bytes(audio_bytes)
    legacy = tmp_path / "legacy-cache"
    legacy.mkdir()
    path = _write_legacy_cache_chunk(legacy, audio_bytes, 0)
    original_glob = Path.glob

    def duplicate_glob(directory, pattern):
        paths = list(original_glob(directory, pattern))
        if directory == legacy:
            return iter(paths + [path])
        return original_glob(directory, pattern)

    monkeypatch.setattr(Path, "glob", duplicate_glob)
    with pytest.raises(FrozenCoreError, match="duplicate legacy"):
        inspect_legacy_cached_speech_feature_cache(
            audio_path=audio,
            legacy_cache_dir=legacy,
            expected_n_embd=4,
        )


def test_legacy_featcache_batch_promotion_is_parallel_and_ordered(
    tmp_path, monkeypatch
):
    from speech_aware_evidence_acquisition.core.model import speech_features

    legacy = tmp_path / "legacy-cache"
    legacy.mkdir()
    bindings = []
    for index in range(6):
        audio = tmp_path / f"audio-{index}.flac"
        audio.write_bytes(f"governed-audio-{index}".encode())
        key = legacy_audio_feature_cache_key(audio.read_bytes())
        features = struct.pack("<8f", *[float(index)] * 8)
        (legacy / f"{key}_o0.feat").write_bytes(struct.pack("<QQ", 2, 4) + features)
        bindings.append({"packet_id": f"slurp/train/s{index}", "audio_path": audio})

    original = speech_features._prepare_legacy_cached_speech_feature_packet
    lock = threading.Lock()
    active = 0
    peak = 0

    def tracked_preflight(**kwargs):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.02)
        try:
            return original(**kwargs)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(
        speech_features,
        "_prepare_legacy_cached_speech_feature_packet",
        tracked_preflight,
    )
    packets = materialize_legacy_cached_speech_feature_packets(
        feature_root=tmp_path / "packets",
        bindings=tuple(reversed(bindings)),
        legacy_cache_dir=legacy,
        encoder_receipt_sha256="1" * 64,
        decoder_gguf_sha256="2" * 64,
        mmproj_sha256="3" * 64,
        expected_n_embd=4,
        causal_attention=True,
        workers=3,
    )

    assert [packet.packet_id for packet in packets] == [
        binding["packet_id"] for binding in reversed(bindings)
    ]
    assert 2 <= peak <= 3


def test_legacy_featcache_batch_promotion_refuses_duplicates_before_work(tmp_path):
    audio = tmp_path / "audio.flac"
    audio.write_bytes(b"governed-audio")
    with pytest.raises(FrozenCoreError, match="duplicate speech packet"):
        materialize_legacy_cached_speech_feature_packets(
            feature_root=tmp_path / "packets",
            bindings=(
                {"packet_id": "slurp/train/s1", "audio_path": audio},
                {"packet_id": "slurp/train/s1", "audio_path": audio},
            ),
            legacy_cache_dir=tmp_path / "legacy-cache",
            encoder_receipt_sha256="1" * 64,
            decoder_gguf_sha256="2" * 64,
            mmproj_sha256="3" * 64,
            expected_n_embd=4,
            causal_attention=True,
        )


def test_legacy_featcache_batch_promotion_preflights_all_caches_before_writing(
    tmp_path,
):
    legacy = tmp_path / "legacy-cache"
    legacy.mkdir()
    valid_audio = tmp_path / "valid.flac"
    valid_audio.write_bytes(b"governed-valid-audio")
    missing_audio = tmp_path / "missing.flac"
    missing_audio.write_bytes(b"governed-missing-audio")
    key = legacy_audio_feature_cache_key(valid_audio.read_bytes())
    features = struct.pack("<8f", *[1.0] * 8)
    (legacy / f"{key}_o0.feat").write_bytes(struct.pack("<QQ", 2, 4) + features)
    feature_root = tmp_path / "packets"

    with pytest.raises(FrozenCoreError, match="has no ordinal zero"):
        materialize_legacy_cached_speech_feature_packets(
            feature_root=feature_root,
            bindings=(
                {"packet_id": "slurp/train/valid", "audio_path": valid_audio},
                {"packet_id": "slurp/train/missing", "audio_path": missing_audio},
            ),
            legacy_cache_dir=legacy,
            encoder_receipt_sha256="1" * 64,
            decoder_gguf_sha256="2" * 64,
            mmproj_sha256="3" * 64,
            expected_n_embd=4,
            causal_attention=True,
            workers=2,
        )

    assert not feature_root.exists()


# ---------------------------------------------------------------------------
# ObsPacket
# ---------------------------------------------------------------------------


def _obs_packet() -> ObsPacket:
    return ObsPacket(
        audio_ref=AudioRef(path="datasets/x/media/1.wav", sha256=_SHA_A),
        spans=(SpanRef(span_id="full", start_seconds=0.0, end_seconds=4.5),),
        first_pass=None,
    )


def test_obs_packet_round_trips_and_hash_is_stable():
    packet = _obs_packet().validate()
    rebuilt = ObsPacket.from_json(packet.as_json())
    assert rebuilt == packet
    assert rebuilt.content_hash() == packet.content_hash()
    # independently-constructed-but-equal packets hash identically
    assert _obs_packet().content_hash() == packet.content_hash()


def test_obs_packet_hash_changes_when_a_field_changes():
    base = _obs_packet()
    changed = ObsPacket(
        audio_ref=base.audio_ref,
        spans=base.spans,
        first_pass="a different first-pass hypothesis",
    )
    assert changed.content_hash() != base.content_hash()


def test_obs_packet_has_no_views_field():
    """Owner scope ruling (2026-08-17): multi-view speech embeddings are out
    of this study's scope; ObsPacket must carry no views field at all."""

    assert "views" not in _obs_packet().as_json()
    assert not hasattr(_obs_packet(), "views")


def test_span_ref_rejects_a_backwards_or_zero_length_span():
    with pytest.raises(RailsError, match="end_seconds"):
        SpanRef(span_id="full", start_seconds=2.0, end_seconds=2.0).validate()
    with pytest.raises(RailsError, match="end_seconds"):
        SpanRef(span_id="full", start_seconds=3.0, end_seconds=1.0).validate()


def test_obs_packet_rejects_duplicate_span_ids():
    packet = ObsPacket(
        audio_ref=AudioRef(path="a.wav", sha256=_SHA_A),
        spans=(
            SpanRef(span_id="s1", start_seconds=0.0, end_seconds=1.0),
            SpanRef(span_id="s1", start_seconds=1.0, end_seconds=2.0),
        ),
        first_pass=None,
    )
    with pytest.raises(RailsError, match="duplicate span_id"):
        packet.validate()


def test_audio_ref_rejects_a_non_sha256_hash():
    with pytest.raises(RailsError, match="sha256"):
        AudioRef(path="a.wav", sha256="not-a-hash").validate()


def test_default_obs_packet_builds_one_whole_file_span():
    class _Sample:
        sample_id = "s1"
        audio_ref = AudioRef(path="a.wav", sha256=_SHA_A)
        audio_seconds = 3.25

    packet = default_obs_packet(_Sample())
    assert packet.spans == (
        SpanRef(span_id="full", start_seconds=0.0, end_seconds=3.25),
    )
    assert packet.first_pass is None


# ---------------------------------------------------------------------------
# EvidenceItem / EvidenceSet + legality gate reuse
# ---------------------------------------------------------------------------


def test_evidence_item_round_trips_and_hash_is_stable():
    item = EvidenceItem(
        evidence_id="e1",
        content="Acme Corp",
        source_ref="conec:4000001",
        legality_tier="legal",
    )
    rebuilt = EvidenceItem.from_json(item.as_json())
    assert rebuilt == item


def test_evidence_set_round_trips_and_hash_is_stable():
    items = (
        EvidenceItem(evidence_id="e1", content="Acme Corp", source_ref="conec:4000001"),
        EvidenceItem(evidence_id="e2", content="Beta Inc", source_ref="conec:4000001"),
    )
    params = RetrievalParams(tau=0.5, k=2, key_kind=RetrievalKeyKind.TASK_CONTEXT.value)
    evidence_set = EvidenceSet(
        items=items, query_ref="query:4000001", retrieval_params=params
    )
    rebuilt = EvidenceSet.from_json(evidence_set.as_json())
    assert rebuilt == evidence_set
    assert rebuilt.content_hash() == evidence_set.content_hash()


def test_evidence_set_has_no_views_field():
    params = RetrievalParams(tau=0.5, k=2, key_kind="task-context")
    assert "views" not in params.as_json()
    evidence_set = EvidenceSet(items=(), query_ref="q", retrieval_params=params)
    assert "views" not in evidence_set.as_json()["retrieval_params"]


def test_evidence_set_rejects_duplicate_evidence_ids():
    items = (
        EvidenceItem(evidence_id="e1", content="a", source_ref="r"),
        EvidenceItem(evidence_id="e1", content="b", source_ref="r"),
    )
    evidence_set = EvidenceSet(
        items=items,
        query_ref="q",
        retrieval_params=RetrievalParams(tau=0.1, k=1, key_kind="task-context"),
    )
    with pytest.raises(RailsError, match="duplicate evidence_id"):
        evidence_set.validate()


def test_retrieval_params_rejects_out_of_range_tau_and_negative_k():
    with pytest.raises(RailsError, match="tau"):
        RetrievalParams(tau=1.5, k=1, key_kind="task-context").validate()
    with pytest.raises(RailsError, match="k"):
        RetrievalParams(tau=0.5, k=-1, key_kind="task-context").validate()
    with pytest.raises(RailsError, match="key_kind"):
        RetrievalParams(tau=0.5, k=1, key_kind="").validate()


def test_legality_gate_rejects_a_gold_span_source_declared_legal_tier(tmp_path):
    """The B0 mission's own required test: the legality gate rejects a
    gold-derived EvidenceItem in a deployment-tier ("legal") arm, reusing
    core.legality's E1' either-field rule directly -- never a re-derived
    rails-local rule."""

    item = EvidenceItem(
        evidence_id="e1",
        content="Acme Corp",
        source_ref="p1-oracle-v2:4000001",
        span_source="gold-aligned",
        legality_tier="legal",
    )
    with pytest.raises(LegalityError, match="either-field rule"):
        item.resolve_legality(tmp_path)


def test_legality_gate_rejects_a_gold_reference_source_declared_legal_tier(tmp_path):
    item = EvidenceItem(
        evidence_id="e1",
        content="Acme Corp",
        source_ref="p1-oracle-v2:4000001",
        reference_source="oracle-lineage",
        legality_tier="legal",
    )
    with pytest.raises(LegalityError, match="either-field rule"):
        item.resolve_legality(tmp_path)


def test_legality_gate_accepts_a_gold_span_source_declared_ceiling_tier(tmp_path):
    item = EvidenceItem(
        evidence_id="e1",
        content="Acme Corp",
        source_ref="p1-oracle-v2:4000001",
        span_source="gold-aligned",
        reference_source="own-draft",
        legality_tier="ceiling",
    )
    declaration = item.resolve_legality(tmp_path)
    assert declaration.legality_tier == "ceiling"
    assert declaration.declaration_warning is None


def test_legality_gate_accepts_a_legal_tier_item_with_no_gold_fields(tmp_path):
    item = EvidenceItem(
        evidence_id="e1",
        content="Acme Corp",
        source_ref="conec:4000001",
        span_source="roster-band-flag",
        reference_source="conec-call-keyed",
        legality_tier="legal",
    )
    declaration = item.resolve_legality(tmp_path)
    assert declaration.legality_tier == "legal"
    assert declaration.declaration_warning is None


def test_legality_gate_warns_on_an_undeclared_evidence_item(tmp_path):
    """Grandfathering (core.legality's own doctrine): an item declaring
    NONE of the three fields only warns, it is never refused."""

    item = EvidenceItem(
        evidence_id="e1", content="Acme Corp", source_ref="conec:4000001"
    )
    declaration = item.resolve_legality(tmp_path)
    assert declaration.declaration_warning is not None
    assert "GRANDFATHERED" in declaration.declaration_warning


def test_evidence_set_assert_legal_for_deployment_propagates_the_refusal(tmp_path):
    items = (
        EvidenceItem(
            evidence_id="e1", content="a", source_ref="r", legality_tier="legal"
        ),
        EvidenceItem(
            evidence_id="e2",
            content="b",
            source_ref="r",
            span_source="gold-aligned",
            legality_tier="legal",
        ),
    )
    evidence_set = EvidenceSet(
        items=items,
        query_ref="q",
        retrieval_params=RetrievalParams(tau=0.5, k=2, key_kind="task-context"),
    )
    with pytest.raises(LegalityError):
        evidence_set.assert_legal_for_deployment(tmp_path)


# ---------------------------------------------------------------------------
# Knowledge BUILD -> frozen snapshot -> DEV USE/OPTIMIZE contracts
# ---------------------------------------------------------------------------


def _knowledge_snapshot() -> KnowledgeSnapshot:
    return KnowledgeSnapshot(
        snapshot_id="slurp-train-kb-v1",
        source_split_identity_hash=_SHA_A,
        source_sample_ids=("slurp/train/t1", "slurp/train/t2"),
        builder_policy_id="multifacet-train-build-v1",
        facets=(
            KeyFacet(
                facet_id="domain:iot",
                dimension="domain",
                representation_kind="text",
                representation="connected-device control",
                source_sample_ids=("slurp/train/t1", "slurp/train/t2"),
            ),
            KeyFacet(
                facet_id="operation:decrease",
                dimension="operation",
                representation_kind="text",
                representation="reduce the current level",
                source_sample_ids=("slurp/train/t1",),
                parent_facet_ids=("domain:iot",),
            ),
        ),
        values=(
            ValueBundle(
                value_id="value:dim-light",
                content="Choose the dim-light route when the requested operation reduces brightness.",
                associated_facet_ids=("domain:iot", "operation:decrease"),
                source_sample_ids=("slurp/train/t1",),
                provenance_refs=("slurp/train/t1",),
                task_target="hue_lightdim",
                prior_score=0.25,
            ),
        ),
    )


def _query_state(**overrides) -> QueryState:
    values = dict(
        query_id="query:dev:d1:step0",
        query_sample_id="slurp/dev/d1",
        speech_packet_id="slurp/devel/d1",
        speech_packet_sha256=_SHA_B,
        use_split_identity_hash=_SHA_C,
    )
    values.update(overrides)
    return QueryState(**values)


def _rank_and_fusion(snapshot: KnowledgeSnapshot, query: QueryState):
    rank = RankResult(
        snapshot_sha256=snapshot.content_hash(),
        query_state_sha256=query.content_hash(),
        ranking_policy_id="speech-facet-ranker-v1",
        candidates=(
            RankedFacet(facet_id="operation:decrease", score=0.9),
            RankedFacet(facet_id="domain:iot", score=0.8),
        ),
    )
    fusion = FusionDecision(
        snapshot_sha256=snapshot.content_hash(),
        query_state_sha256=query.content_hash(),
        rank_result_sha256=rank.content_hash(),
        fusion_policy_id="late-facet-fusion-v1",
        supporting_facet_ids=("operation:decrease", "domain:iot"),
        selected_value_ids=("value:dim-light",),
    )
    return rank, fusion


def test_knowledge_snapshot_freezes_and_round_trips_with_a_self_hash():
    snapshot = _knowledge_snapshot().validate()
    frozen = snapshot.frozen_json()
    assert frozen["source_partition_role"] == "train"
    assert frozen["snapshot_sha256"] == snapshot.content_hash()
    assert KnowledgeSnapshot.from_frozen_json(frozen) == snapshot


def test_knowledge_snapshot_refuses_dev_as_a_build_source():
    snapshot = _knowledge_snapshot()
    with pytest.raises(RailsError, match="must be 'train'"):
        KnowledgeSnapshot(
            snapshot_id=snapshot.snapshot_id,
            source_split_identity_hash=snapshot.source_split_identity_hash,
            source_sample_ids=snapshot.source_sample_ids,
            builder_policy_id=snapshot.builder_policy_id,
            facets=snapshot.facets,
            values=snapshot.values,
            source_partition_role="dev",
        ).validate()


def test_knowledge_snapshot_refuses_hash_tampering():
    frozen = _knowledge_snapshot().frozen_json()
    frozen["builder_policy_id"] = "tampered-policy"
    with pytest.raises(RailsError, match="hash mismatch"):
        KnowledgeSnapshot.from_frozen_json(frozen)


def test_knowledge_snapshot_has_no_task_label_roster_cap():
    source_ids = tuple(f"train/sample-{index:03d}" for index in range(101))
    root = KeyFacet(
        facet_id="domain:root",
        dimension="domain",
        representation_kind="text",
        representation="task-independent root",
        source_sample_ids=source_ids,
    )
    leaves = tuple(
        KeyFacet(
            facet_id=f"route:{index:03d}",
            dimension="route",
            representation_kind="text",
            representation=f"maintainable route {index:03d}",
            source_sample_ids=(source_id,),
            parent_facet_ids=(root.facet_id,),
        )
        for index, source_id in enumerate(source_ids)
    )
    values = tuple(
        ValueBundle(
            value_id=f"value:{index:03d}",
            content=f"Training-derived evidence for route {index:03d}.",
            associated_facet_ids=(leaf.facet_id,),
            source_sample_ids=(source_id,),
            provenance_refs=(source_id,),
            task_target=f"target-{index:03d}",
        )
        for index, (source_id, leaf) in enumerate(zip(source_ids, leaves, strict=True))
    )
    snapshot = KnowledgeSnapshot(
        snapshot_id="large-roster-kb-v1",
        source_split_identity_hash=_SHA_A,
        source_sample_ids=source_ids,
        builder_policy_id="hierarchical-multifacet-build-v1",
        facets=(root, *leaves),
        values=values,
    ).validate()
    assert len(snapshot.facets) == 102
    assert len(snapshot.values) == 101


def test_query_state_keeps_original_speech_when_agent_state_is_added():
    query = _query_state(
        loop_step=2,
        agent_state_ids=("state:domain:iot",),
        retrieved_value_ids=("value:dim-light",),
    ).validate()
    assert query.speech_packet_sha256 == _SHA_B
    assert query.speech_packet_id == "slurp/devel/d1"
    assert query.query_source == "speech_features"
    assert query.use_partition_role == "dev"
    assert QueryState.from_json(query.as_json()) == query


def test_query_state_refuses_a_text_only_or_non_dev_query():
    with pytest.raises(RailsError, match="speech_packet_sha256"):
        _query_state(speech_packet_sha256="").validate()
    with pytest.raises(RailsError, match="must be 'dev'"):
        _query_state(use_partition_role="train").validate()
    with pytest.raises(RailsError, match="cannot replace the original speech query"):
        _query_state(query_source="generated_text").validate()


def test_knowledge_use_binding_accepts_disjoint_train_build_and_dev_use():
    snapshot = _knowledge_snapshot()
    query = _query_state()
    rank, fusion = _rank_and_fusion(snapshot, query)
    assert_knowledge_use_binding(
        snapshot=snapshot,
        query_state=query,
        rank_result=rank,
        fusion_decision=fusion,
    )


def test_knowledge_use_binding_refuses_self_retrieval():
    snapshot = _knowledge_snapshot()
    query = _query_state(query_sample_id="slurp/train/t1")
    rank, fusion = _rank_and_fusion(snapshot, query)
    with pytest.raises(RailsError, match="overlaps the TRAIN"):
        assert_knowledge_use_binding(
            snapshot=snapshot,
            query_state=query,
            rank_result=rank,
            fusion_decision=fusion,
        )


def test_knowledge_use_binding_refuses_unassociated_value_fusion():
    snapshot = _knowledge_snapshot()
    query = _query_state()
    rank = RankResult(
        snapshot_sha256=snapshot.content_hash(),
        query_state_sha256=query.content_hash(),
        ranking_policy_id="speech-facet-ranker-v1",
        candidates=(RankedFacet(facet_id="domain:iot", score=1.0),),
    )
    # Build a valid snapshot value that is associated only with operation,
    # then try to justify it with the independently ranked domain facet.
    operation_only_value = ValueBundle(
        value_id="value:dim-light",
        content=snapshot.values[0].content,
        associated_facet_ids=("operation:decrease",),
        source_sample_ids=("slurp/train/t1",),
        provenance_refs=("slurp/train/t1",),
        task_target="hue_lightdim",
    )
    snapshot = KnowledgeSnapshot(
        snapshot_id=snapshot.snapshot_id,
        source_split_identity_hash=snapshot.source_split_identity_hash,
        source_sample_ids=snapshot.source_sample_ids,
        builder_policy_id=snapshot.builder_policy_id,
        facets=snapshot.facets,
        values=(operation_only_value,),
    )
    rank = RankResult(
        snapshot_sha256=snapshot.content_hash(),
        query_state_sha256=query.content_hash(),
        ranking_policy_id="speech-facet-ranker-v1",
        candidates=(RankedFacet(facet_id="domain:iot", score=1.0),),
    )
    fusion = FusionDecision(
        snapshot_sha256=snapshot.content_hash(),
        query_state_sha256=query.content_hash(),
        rank_result_sha256=rank.content_hash(),
        fusion_policy_id="late-facet-fusion-v1",
        supporting_facet_ids=("domain:iot",),
        selected_value_ids=("value:dim-light",),
    )
    with pytest.raises(RailsError, match="has no association"):
        assert_knowledge_use_binding(
            snapshot=snapshot,
            query_state=query,
            rank_result=rank,
            fusion_decision=fusion,
        )


def _agent_step(
    snapshot: KnowledgeSnapshot,
    prior: QueryState,
    next_state: QueryState | None,
    **overrides,
) -> AgentStepTransition:
    values = dict(
        snapshot_sha256=snapshot.content_hash(),
        prior_query_state_sha256=prior.content_hash(),
        next_query_state_sha256=(
            next_state.content_hash() if next_state is not None else None
        ),
        action_kind="acquire",
        action_target_refs=("operation",),
        new_value_ids=("value:dim-light",),
        used_value_ids=(),
        dropped_value_ids=(),
        new_agent_state_ids=(),
        dropped_agent_state_ids=(),
    )
    values.update(overrides)
    return AgentStepTransition(**values)


def test_agent_acquire_step_proves_a_new_train_built_value_enters_same_speech_query():
    snapshot = _knowledge_snapshot()
    prior = _query_state()
    next_state = _query_state(
        query_id="query:dev:d1:step1",
        loop_step=1,
        retrieved_value_ids=("value:dim-light",),
    )
    transition = _agent_step(snapshot, prior, next_state)
    assert_agent_step_binding(
        snapshot=snapshot,
        prior_query_state=prior,
        next_query_state=next_state,
        transition=transition,
    )
    assert AgentStepTransition.from_json(transition.as_json()) == transition


def test_agent_supply_action_refuses_a_restatement_with_no_new_value():
    snapshot = _knowledge_snapshot()
    prior = _query_state()
    next_state = _query_state(query_id="query:dev:d1:step1", loop_step=1)
    transition = _agent_step(
        snapshot,
        prior,
        next_state,
        new_value_ids=(),
    )
    with pytest.raises(RailsError, match="must introduce at least one new value"):
        assert_agent_step_binding(
            snapshot=snapshot,
            prior_query_state=prior,
            next_query_state=next_state,
            transition=transition,
        )


def test_agent_supply_action_refuses_a_value_that_was_already_visible():
    snapshot = _knowledge_snapshot()
    prior = _query_state(retrieved_value_ids=("value:dim-light",))
    next_state = _query_state(
        query_id="query:dev:d1:step1",
        loop_step=1,
        retrieved_value_ids=("value:dim-light",),
    )
    transition = _agent_step(
        snapshot,
        prior,
        next_state,
        new_value_ids=("value:dim-light",),
    )

    with pytest.raises(RailsError, match="already visible"):
        assert_agent_step_binding(
            snapshot=snapshot,
            prior_query_state=prior,
            next_query_state=next_state,
            transition=transition,
        )


def test_agent_verify_step_reuses_visible_value_without_claiming_new_supply():
    snapshot = _knowledge_snapshot()
    prior = _query_state(
        query_id="query:dev:d1:step1",
        loop_step=1,
        retrieved_value_ids=("value:dim-light",),
    )
    next_state = _query_state(
        query_id="query:dev:d1:step2",
        loop_step=2,
        retrieved_value_ids=("value:dim-light",),
        agent_state_ids=("state:verified:dim-light",),
    )
    transition = _agent_step(
        snapshot,
        prior,
        next_state,
        action_kind="verify",
        action_target_refs=("value:dim-light",),
        new_value_ids=(),
        used_value_ids=("value:dim-light",),
        new_agent_state_ids=("state:verified:dim-light",),
    )
    assert_agent_step_binding(
        snapshot=snapshot,
        prior_query_state=prior,
        next_query_state=next_state,
        transition=transition,
    )


def test_agent_organize_step_adds_auxiliary_state_without_replacing_speech_query():
    snapshot = _knowledge_snapshot()
    prior = _query_state()
    next_state = _query_state(
        query_id="query:dev:d1:step1",
        loop_step=1,
        agent_state_ids=("state:intent-factor:operation",),
    )
    transition = _agent_step(
        snapshot,
        prior,
        next_state,
        action_kind="organize",
        action_target_refs=("intent-factor-schema-v1",),
        new_value_ids=(),
        new_agent_state_ids=("state:intent-factor:operation",),
    )

    assert_agent_step_binding(
        snapshot=snapshot,
        prior_query_state=prior,
        next_query_state=next_state,
        transition=transition,
    )
    assert next_state.speech_packet_sha256 == prior.speech_packet_sha256
    assert next_state.retrieved_value_ids == ()


def test_agent_backtrack_can_drop_state_and_value_but_cannot_change_speech():
    snapshot = _knowledge_snapshot()
    prior = _query_state(
        query_id="query:dev:d1:step2",
        loop_step=2,
        retrieved_value_ids=("value:dim-light",),
        agent_state_ids=("state:unsupported",),
    )
    next_state = _query_state(
        query_id="query:dev:d1:step3",
        loop_step=3,
    )
    transition = _agent_step(
        snapshot,
        prior,
        next_state,
        action_kind="backtrack",
        action_target_refs=("state:unsupported",),
        new_value_ids=(),
        dropped_value_ids=("value:dim-light",),
        dropped_agent_state_ids=("state:unsupported",),
    )
    assert_agent_step_binding(
        snapshot=snapshot,
        prior_query_state=prior,
        next_query_state=next_state,
        transition=transition,
    )

    changed_speech = _query_state(
        query_id="query:dev:d1:step3",
        loop_step=3,
        speech_packet_sha256=_SHA_C,
    )
    changed_transition = _agent_step(
        snapshot,
        prior,
        changed_speech,
        action_kind="backtrack",
        action_target_refs=("state:unsupported",),
        new_value_ids=(),
        dropped_value_ids=("value:dim-light",),
        dropped_agent_state_ids=("state:unsupported",),
    )
    with pytest.raises(RailsError, match="same original speech packet"):
        assert_agent_step_binding(
            snapshot=snapshot,
            prior_query_state=prior,
            next_query_state=changed_speech,
            transition=changed_transition,
        )


def test_agent_stop_step_has_no_successor_or_information_delta():
    snapshot = _knowledge_snapshot()
    prior = _query_state()
    transition = _agent_step(
        snapshot,
        prior,
        None,
        action_kind="stop",
        action_target_refs=(),
        new_value_ids=(),
    )
    assert_agent_step_binding(
        snapshot=snapshot,
        prior_query_state=prior,
        next_query_state=None,
        transition=transition,
    )


def test_agent_backtrack_refuses_to_claim_a_drop_that_was_not_visible():
    snapshot = _knowledge_snapshot()
    prior = _query_state()
    next_state = _query_state(query_id="query:dev:d1:step1", loop_step=1)
    transition = _agent_step(
        snapshot,
        prior,
        next_state,
        action_kind="backtrack",
        action_target_refs=("value:dim-light",),
        new_value_ids=(),
        dropped_value_ids=("value:dim-light",),
    )

    with pytest.raises(RailsError, match="were not visible"):
        assert_agent_step_binding(
            snapshot=snapshot,
            prior_query_state=prior,
            next_query_state=next_state,
            transition=transition,
        )


def test_agent_state_artifact_round_trips_with_response_and_value_provenance():
    artifact = AgentStateArtifact(
        state_id="state:operation-needed",
        state_kind="intent-factor",
        content="The unresolved factor is the requested operation.",
        source_query_state_sha256=_SHA_A,
        source_response_sha256=_SHA_B,
        producer_policy_id="organize-v1",
        cited_value_ids=("value:dim-light",),
    ).validate()

    assert AgentStateArtifact.from_json(artifact.as_json()) == artifact
    assert len(artifact.content_hash()) == 64


def test_agent_state_artifact_refuses_duplicate_value_citations():
    with pytest.raises(RailsError, match="unique"):
        AgentStateArtifact(
            state_id="state:operation-needed",
            state_kind="intent-factor",
            content="The unresolved factor is the requested operation.",
            source_query_state_sha256=_SHA_A,
            source_response_sha256=_SHA_B,
            producer_policy_id="organize-v1",
            cited_value_ids=("value:dim-light", "value:dim-light"),
        ).validate()


# ---------------------------------------------------------------------------
# C4 scale fixes (docs/readiness/2026-08-23-knowledge-plane-baseline-
# rulings.md Sec 4, items 1-3): snapshot-hash passthrough, KnowledgeSnapshot
# .validate() idempotence, and the new external-governed source_partition_role.
# ---------------------------------------------------------------------------


def test_knowledge_use_binding_accepts_a_precomputed_snapshot_hash():
    snapshot = _knowledge_snapshot()
    query = _query_state()
    rank, fusion = _rank_and_fusion(snapshot, query)
    precomputed = snapshot.content_hash()
    # A caller-precomputed hash must behave identically to the default
    # recompute-every-call path: same acceptance, no observable difference.
    assert_knowledge_use_binding(
        snapshot=snapshot,
        query_state=query,
        rank_result=rank,
        fusion_decision=fusion,
        snapshot_sha256=precomputed,
    )
    assert_knowledge_use_binding(
        snapshot=snapshot,
        query_state=query,
        rank_result=rank,
        fusion_decision=fusion,
    )


def test_knowledge_use_binding_refuses_a_malformed_precomputed_hash():
    snapshot = _knowledge_snapshot()
    query = _query_state()
    rank, fusion = _rank_and_fusion(snapshot, query)
    with pytest.raises(RailsError, match="64-hex SHA-256"):
        assert_knowledge_use_binding(
            snapshot=snapshot,
            query_state=query,
            rank_result=rank,
            fusion_decision=fusion,
            snapshot_sha256="not-a-hash",
        )


def test_knowledge_use_binding_refuses_a_precomputed_hash_that_does_not_match():
    snapshot = _knowledge_snapshot()
    query = _query_state()
    rank, fusion = _rank_and_fusion(snapshot, query)
    with pytest.raises(RailsError, match="bound to a different KnowledgeSnapshot"):
        assert_knowledge_use_binding(
            snapshot=snapshot,
            query_state=query,
            rank_result=rank,
            fusion_decision=fusion,
            snapshot_sha256="0" * 64,
        )


def test_agent_step_binding_accepts_a_precomputed_snapshot_hash():
    snapshot = _knowledge_snapshot()
    prior = _query_state()
    next_state = _query_state(
        query_id="query:dev:d1:step1",
        loop_step=1,
        retrieved_value_ids=("value:dim-light",),
    )
    transition = _agent_step(snapshot, prior, next_state)
    precomputed = snapshot.content_hash()
    assert_agent_step_binding(
        snapshot=snapshot,
        prior_query_state=prior,
        next_query_state=next_state,
        transition=transition,
        snapshot_sha256=precomputed,
    )
    assert_agent_step_binding(
        snapshot=snapshot,
        prior_query_state=prior,
        next_query_state=next_state,
        transition=transition,
    )


def test_agent_step_binding_refuses_a_malformed_precomputed_hash():
    snapshot = _knowledge_snapshot()
    prior = _query_state()
    next_state = _query_state(
        query_id="query:dev:d1:step1",
        loop_step=1,
        retrieved_value_ids=("value:dim-light",),
    )
    transition = _agent_step(snapshot, prior, next_state)
    with pytest.raises(RailsError, match="64-hex SHA-256"):
        assert_agent_step_binding(
            snapshot=snapshot,
            prior_query_state=prior,
            next_query_state=next_state,
            transition=transition,
            snapshot_sha256="short",
        )


def test_agent_step_binding_refuses_a_precomputed_hash_that_does_not_match():
    snapshot = _knowledge_snapshot()
    prior = _query_state()
    next_state = _query_state(
        query_id="query:dev:d1:step1",
        loop_step=1,
        retrieved_value_ids=("value:dim-light",),
    )
    transition = _agent_step(snapshot, prior, next_state)
    with pytest.raises(RailsError, match="bound to a different snapshot"):
        assert_agent_step_binding(
            snapshot=snapshot,
            prior_query_state=prior,
            next_query_state=next_state,
            transition=transition,
            snapshot_sha256="0" * 64,
        )


def test_knowledge_snapshot_validate_is_idempotent_and_preserves_the_hash():
    fresh = _knowledge_snapshot()
    baseline_hash = fresh.content_hash()

    revalidated = _knowledge_snapshot()
    for _ in range(3):
        assert revalidated.validate() is revalidated
    assert revalidated.content_hash() == baseline_hash
    assert revalidated.as_json() == fresh.as_json()
    assert revalidated == fresh


def test_knowledge_snapshot_validate_skips_full_revalidation_on_repeat_calls(
    monkeypatch,
):
    snapshot = _knowledge_snapshot()
    calls = []
    original = KnowledgeSnapshot._assert_acyclic_facets

    def counting_acyclic(self):
        calls.append(1)
        return original(self)

    monkeypatch.setattr(KnowledgeSnapshot, "_assert_acyclic_facets", counting_acyclic)
    snapshot.validate()
    snapshot.validate()
    snapshot.validate()
    assert len(calls) == 1


def test_knowledge_snapshot_historical_train_hash_is_unchanged_by_c4():
    # Pinned regression: this exact "train"-role snapshot's content hash was
    # confirmed identical between the pre-C4 module (git blob at the commit
    # preceding this change) and the post-C4 module -- the C4 scale fixes
    # (hash passthrough, validate idempotence, the new external-governed
    # role) change no field, no key order, and no hashed byte of an
    # existing-style frozen snapshot.
    snapshot = _knowledge_snapshot().validate()
    assert (
        snapshot.content_hash()
        == "959c1496a5eec17675bef623390b64bab89f8c1d32e18528e8f3315a14eb18a5"
    )
    assert snapshot.frozen_json()["snapshot_sha256"] == snapshot.content_hash()


def _external_governed_knowledge_snapshot() -> KnowledgeSnapshot:
    return KnowledgeSnapshot(
        snapshot_id="conec-context-kb-v1",
        source_split_identity_hash=_SHA_A,
        source_sample_ids=("conec/doc/entity-001", "conec/doc/entity-002"),
        builder_policy_id="external-governed-context-build-v1",
        facets=(
            KeyFacet(
                facet_id="entity:acme-corp",
                dimension="entity",
                representation_kind="text",
                representation="Acme Corp, a governed external context entity.",
                source_sample_ids=("conec/doc/entity-001",),
            ),
        ),
        values=(
            ValueBundle(
                value_id="value:acme-corp-context",
                content=(
                    "Acme Corp is referenced in the governed ConEC context "
                    "documents."
                ),
                associated_facet_ids=("entity:acme-corp",),
                source_sample_ids=("conec/doc/entity-001",),
                provenance_refs=("conec/doc/entity-001",),
            ),
            ValueBundle(
                value_id="value:entity-002-context",
                content="A second governed context entry sharing the entity facet.",
                associated_facet_ids=("entity:acme-corp",),
                source_sample_ids=("conec/doc/entity-002",),
                provenance_refs=("conec/doc/entity-002",),
            ),
        ),
        source_partition_role=EXTERNAL_GOVERNED_PARTITION_ROLE,
    )


def test_knowledge_snapshot_accepts_external_governed_source_role():
    snapshot = _external_governed_knowledge_snapshot().validate()
    frozen = snapshot.frozen_json()
    assert frozen["source_partition_role"] == "external-governed"
    assert frozen["snapshot_sha256"] == snapshot.content_hash()
    assert KnowledgeSnapshot.from_frozen_json(frozen) == snapshot


def test_knowledge_snapshot_refuses_an_unknown_role_and_names_both_allowed_values():
    snapshot = _knowledge_snapshot()
    with pytest.raises(RailsError, match="must be 'train' or 'external-governed'"):
        KnowledgeSnapshot(
            snapshot_id=snapshot.snapshot_id,
            source_split_identity_hash=snapshot.source_split_identity_hash,
            source_sample_ids=snapshot.source_sample_ids,
            builder_policy_id=snapshot.builder_policy_id,
            facets=snapshot.facets,
            values=snapshot.values,
            source_partition_role="test",
        ).validate()


def test_knowledge_use_binding_refuses_self_retrieval_for_both_source_roles():
    for snapshot in (_knowledge_snapshot(), _external_governed_knowledge_snapshot()):
        overlapping_query = _query_state(query_sample_id=snapshot.source_sample_ids[0])
        rank = RankResult(
            snapshot_sha256=_SHA_A,
            query_state_sha256=_SHA_B,
            ranking_policy_id="dummy-ranker-v1",
            candidates=(),
        )
        fusion = FusionDecision(
            snapshot_sha256=_SHA_A,
            query_state_sha256=_SHA_B,
            rank_result_sha256=_SHA_C,
            fusion_policy_id="dummy-fusion-v1",
            supporting_facet_ids=(),
            selected_value_ids=(),
        )
        with pytest.raises(RailsError, match="overlaps the TRAIN"):
            assert_knowledge_use_binding(
                snapshot=snapshot,
                query_state=overlapping_query,
                rank_result=rank,
                fusion_decision=fusion,
            )


def test_agent_step_binding_refuses_self_retrieval_for_both_source_roles():
    for snapshot in (_knowledge_snapshot(), _external_governed_knowledge_snapshot()):
        prior = _query_state(query_sample_id=snapshot.source_sample_ids[0])
        transition = AgentStepTransition(
            snapshot_sha256=snapshot.content_hash(),
            prior_query_state_sha256=prior.content_hash(),
            next_query_state_sha256=None,
            action_kind="stop",
            action_target_refs=(),
            new_value_ids=(),
            used_value_ids=(),
            dropped_value_ids=(),
            new_agent_state_ids=(),
            dropped_agent_state_ids=(),
        )
        with pytest.raises(RailsError, match="query overlaps the TRAIN"):
            assert_agent_step_binding(
                snapshot=snapshot,
                prior_query_state=prior,
                next_query_state=None,
                transition=transition,
            )


# ---------------------------------------------------------------------------
# SupplyPacket
# ---------------------------------------------------------------------------


def _supply_packet() -> SupplyPacket:
    return SupplyPacket(
        form=SupplyForm.ROSTER,
        dose=SupplyDose(n_items=2, token_count=10),
        prompt_block="Known names: Acme Corp, Beta Inc.",
        assembly_template_id="roster-v1",
        items=(
            SupplyItem(item_id="i1", text="Acme Corp", evidence_id="e1"),
            SupplyItem(item_id="i2", text="Beta Inc", evidence_id="e2"),
        ),
    )


def test_supply_packet_round_trips_and_hash_is_stable():
    packet = _supply_packet().validate()
    rebuilt = SupplyPacket.from_json(packet.as_json())
    assert rebuilt == packet
    assert rebuilt.content_hash() == packet.content_hash()
    assert _supply_packet().content_hash() == packet.content_hash()


def test_supply_packet_rejects_a_dose_items_count_mismatch():
    packet = SupplyPacket(
        form=SupplyForm.TEXT,
        dose=SupplyDose(n_items=3, token_count=5),
        prompt_block="x",
        assembly_template_id="t1",
        items=(SupplyItem(item_id="i1", text="x"),),
    )
    with pytest.raises(RailsError, match="dose.n_items"):
        packet.validate()


def test_supply_packet_rejects_duplicate_item_ids():
    packet = SupplyPacket(
        form=SupplyForm.TEXT,
        dose=SupplyDose(n_items=2, token_count=5),
        prompt_block="x",
        assembly_template_id="t1",
        items=(SupplyItem(item_id="i1", text="x"), SupplyItem(item_id="i1", text="y")),
    )
    with pytest.raises(RailsError, match="duplicate item_id"):
        packet.validate()


# ---------------------------------------------------------------------------
# ConsumptionTrace
# ---------------------------------------------------------------------------


def test_classify_outcome_copy_use_ignore():
    response_tokens = "i will use the roster entry acme corp and mention beta but ignore other names".split()
    assert (
        classify_outcome(response_tokens, ["acme", "corp"]) == ConsumptionOutcome.COPY
    )
    assert classify_outcome(response_tokens, ["beta", "corp"]) == ConsumptionOutcome.USE
    assert (
        classify_outcome(response_tokens, ["zulu", "foxtrot"])
        == ConsumptionOutcome.IGNORE
    )
    assert classify_outcome(response_tokens, []) == ConsumptionOutcome.IGNORE


def test_build_consumption_trace_with_no_supply_is_empty():
    trace = build_consumption_trace(
        span_id="full", supply=None, response_text="anything"
    )
    assert trace == ConsumptionTrace(records=(), copy_rate=0.0, dose_realized=0)


def test_build_consumption_trace_computes_copy_rate_and_dose_realized():
    supply = SupplyPacket(
        form=SupplyForm.ROSTER,
        dose=SupplyDose(n_items=3, token_count=6),
        prompt_block="Acme Corp, Beta Corp, Zulu Foxtrot",
        assembly_template_id="roster-v1",
        items=(
            SupplyItem(item_id="i1", text="Acme Corp"),
            SupplyItem(item_id="i2", text="Beta Corp"),
            SupplyItem(item_id="i3", text="Zulu Foxtrot"),
        ),
    )
    response = (
        "I will use the roster entry acme corp and mention beta but ignore other names"
    )
    trace = build_consumption_trace(
        span_id="full", supply=supply, response_text=response
    )
    outcomes = {record.supplied_item_id: record.outcome for record in trace.records}
    assert outcomes == {
        "i1": ConsumptionOutcome.COPY,
        "i2": ConsumptionOutcome.USE,
        "i3": ConsumptionOutcome.IGNORE,
    }
    assert trace.copy_rate == pytest.approx(1 / 3)
    assert trace.dose_realized == 2
    assert all(record.span_id == "full" for record in trace.records)


def test_consumption_trace_round_trips_and_hash_is_stable():
    trace = ConsumptionTrace(
        records=(
            ConsumptionRecord(
                span_id="full",
                supplied_item_id="i1",
                outcome=ConsumptionOutcome.COPY,
                evidence="Acme Corp",
            ),
        ),
        copy_rate=1.0,
        dose_realized=1,
    ).validate()
    rebuilt = ConsumptionTrace.from_json(trace.as_json())
    assert rebuilt == trace
    assert rebuilt.content_hash() == trace.content_hash()


def test_consumption_trace_rejects_dose_realized_exceeding_records():
    with pytest.raises(RailsError, match="dose_realized"):
        ConsumptionTrace(records=(), copy_rate=0.0, dose_realized=1).validate()
