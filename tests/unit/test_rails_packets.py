"""Rails contract dataclasses (B0): round-trip/hash-stability + the legality
gate reusing core.legality's own either-field rule.
"""

from __future__ import annotations

import struct
import threading
import time

import pytest

from speech_aware_evidence_acquisition.core.legality import LegalityError
from speech_aware_evidence_acquisition.core.model import (
    FrozenCoreError,
    legacy_audio_feature_cache_key,
    materialize_legacy_cached_speech_feature_packets,
)
from speech_aware_evidence_acquisition.rails import (
    AudioRef,
    ConsumptionOutcome,
    ConsumptionRecord,
    ConsumptionTrace,
    EvidenceItem,
    EvidenceSet,
    ObsPacket,
    RailsError,
    RetrievalKeyKind,
    RetrievalParams,
    SpanRef,
    SupplyDose,
    SupplyForm,
    SupplyItem,
    SupplyPacket,
    build_consumption_trace,
    classify_outcome,
    default_obs_packet,
)

_SHA_A = "a" * 64
_SHA_B = "b" * 64


def test_legacy_featcache_batch_promotion_is_parallel_and_ordered(tmp_path, monkeypatch):
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


def test_legacy_featcache_batch_promotion_preflights_all_caches_before_writing(tmp_path):
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
    assert packet.spans == (SpanRef(span_id="full", start_seconds=0.0, end_seconds=3.25),)
    assert packet.first_pass is None


# ---------------------------------------------------------------------------
# EvidenceItem / EvidenceSet + legality gate reuse
# ---------------------------------------------------------------------------


def test_evidence_item_round_trips_and_hash_is_stable():
    item = EvidenceItem(
        evidence_id="e1", content="Acme Corp", source_ref="conec:4000001", legality_tier="legal"
    )
    rebuilt = EvidenceItem.from_json(item.as_json())
    assert rebuilt == item


def test_evidence_set_round_trips_and_hash_is_stable():
    items = (
        EvidenceItem(evidence_id="e1", content="Acme Corp", source_ref="conec:4000001"),
        EvidenceItem(evidence_id="e2", content="Beta Inc", source_ref="conec:4000001"),
    )
    params = RetrievalParams(tau=0.5, k=2, key_kind=RetrievalKeyKind.TASK_CONTEXT.value)
    evidence_set = EvidenceSet(items=items, query_ref="query:4000001", retrieval_params=params)
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
        items=items, query_ref="q", retrieval_params=RetrievalParams(tau=0.1, k=1, key_kind="task-context")
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

    item = EvidenceItem(evidence_id="e1", content="Acme Corp", source_ref="conec:4000001")
    declaration = item.resolve_legality(tmp_path)
    assert declaration.declaration_warning is not None
    assert "GRANDFATHERED" in declaration.declaration_warning


def test_evidence_set_assert_legal_for_deployment_propagates_the_refusal(tmp_path):
    items = (
        EvidenceItem(evidence_id="e1", content="a", source_ref="r", legality_tier="legal"),
        EvidenceItem(
            evidence_id="e2",
            content="b",
            source_ref="r",
            span_source="gold-aligned",
            legality_tier="legal",
        ),
    )
    evidence_set = EvidenceSet(
        items=items, query_ref="q", retrieval_params=RetrievalParams(tau=0.5, k=2, key_kind="task-context")
    )
    with pytest.raises(LegalityError):
        evidence_set.assert_legal_for_deployment(tmp_path)


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
    assert classify_outcome(response_tokens, ["acme", "corp"]) == ConsumptionOutcome.COPY
    assert classify_outcome(response_tokens, ["beta", "corp"]) == ConsumptionOutcome.USE
    assert classify_outcome(response_tokens, ["zulu", "foxtrot"]) == ConsumptionOutcome.IGNORE
    assert classify_outcome(response_tokens, []) == ConsumptionOutcome.IGNORE


def test_build_consumption_trace_with_no_supply_is_empty():
    trace = build_consumption_trace(span_id="full", supply=None, response_text="anything")
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
    response = "I will use the roster entry acme corp and mention beta but ignore other names"
    trace = build_consumption_trace(span_id="full", supply=supply, response_text=response)
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
                span_id="full", supplied_item_id="i1", outcome=ConsumptionOutcome.COPY, evidence="Acme Corp"
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
