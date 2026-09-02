"""Model-free integration tests for the frozen G5 corpus and fixed16 surface."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (
    Audio2ToolSample,
)
from speech_aware_evidence_acquisition.rails.obs import AudioRef
from speech_aware_evidence_acquisition.rails.probes.a2t_g5_agentloop import (
    BUNDLE_ASCII_BYTE_CAP,
    G5AgentLoopError,
    G5AgentLoopAdapter,
    ParsedPlan,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_g5_corpus_integration import (
    COMMITTED_CORPUS_SHA256,
    FALLBACK_FAMILY_TAGS,
    G5_FIXED16_SPLIT_ID,
    CorpusFamilyCompiler,
    G5CorpusIntegrationError,
    build_prompt_fit_report,
    load_fixed16_runtime_surface,
)


REPO = Path(__file__).resolve().parents[2]
CORPUS = (
    REPO
    / "knowledge"
    / "audio2tool"
    / "g5-exhaustive-family-contracts-v1"
    / "corpus.json"
)
CHECK = (
    REPO
    / "docs"
    / "checks"
    / "speech-aware-evidence-acquisition"
    / "2026-09-02-a2t-g5-fixed16-integration-prompt-fit-v1"
    / "prompt-fit.json"
)


def _plan(*tags: str, valid: bool = True) -> ParsedPlan:
    return ParsedPlan(
        valid=valid,
        status="VALID" if valid else "INVALID_FALLBACK",
        operations=(),
        selected_family_tags=tuple(tags),
        canonical_json='{"operations":[]}',
    )


def test_corpus_compiler_maps_every_family_to_one_exact_aggregate() -> None:
    compiler = CorpusFamilyCompiler.from_path(CORPUS)

    assert compiler.corpus_sha256 == COMMITTED_CORPUS_SHA256
    assert len(compiler.taxonomy) == 28
    assert {taxon.operation_tags for taxon in compiler.taxonomy} == {("execute",)}
    assert len(compiler.registered_tool_names) == 152
    assert compiler.fallback_family_tags == FALLBACK_FAMILY_TAGS
    assert len(compiler.snapshot.facets) == 28
    assert len(compiler.snapshot.values) == 28
    adapter = G5AgentLoopAdapter(
        (
            # The adapter contract is identity-free; fixture media is never opened.
            Audio2ToolSample(
                sample_id="fixture:000001",
                audio_ref=AudioRef(path="audio.wav", sha256="a" * 64),
                audio_seconds=1.0,
                media_relpath="audio.wav",
            ),
        ),
        split_id="fixture",
        taxonomy=compiler.taxonomy,
    )
    plan_contract = adapter.build_task_contract(adapter.load_split("fixture")[0], None)
    assert "=[execute]" in plan_contract
    assert all(name not in plan_contract for name in compiler.registered_tool_names)

    for taxon in compiler.taxonomy:
        bundle = compiler.compile(_plan(taxon.family_tag))
        assert bundle.family_tags == (taxon.family_tag,)
        assert len(bundle.contracts) == 1
        contract = bundle.contracts[0]
        family = compiler.family_records[taxon.family_tag]
        assert contract.content.encode("ascii") == family.bundle_bytes
        assert hashlib.sha256(contract.content.encode("ascii")).hexdigest() == (
            family.bundle_sha256
        )
        bundle.validate(requested_family_tags=(taxon.family_tag,))


def test_compiler_preserves_requested_order_and_never_ranks_or_prunes() -> None:
    compiler = CorpusFamilyCompiler.from_path(CORPUS)
    bundle = compiler.compile(_plan(*FALLBACK_FAMILY_TAGS))

    assert bundle.family_tags == FALLBACK_FAMILY_TAGS
    assert tuple(row.family_tag for row in bundle.contracts) == FALLBACK_FAMILY_TAGS
    assert bundle.complete is True
    assert bundle.selection_mode == "full-unranked-compatible"
    assert len(bundle.render().encode("ascii")) <= BUNDLE_ASCII_BYTE_CAP
    assert sum(compiler.family_records[tag].tool_count for tag in FALLBACK_FAMILY_TAGS) == 19
    assert any(tag.startswith("smart-car-") for tag in FALLBACK_FAMILY_TAGS)
    assert any(tag.startswith("smart-home-") for tag in FALLBACK_FAMILY_TAGS)
    assert any(tag.startswith("wearables-") for tag in FALLBACK_FAMILY_TAGS)

    with pytest.raises(G5AgentLoopError, match="bundle byte cap"):
        compiler.compile(_plan(*(taxon.family_tag for taxon in compiler.taxonomy)))


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _runtime_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    rows = []
    tiers: dict[str, list[dict[str, str]]] = {}
    packet_rows = []
    packet_root = tmp_path / "packets"
    canonical = []
    for tier_number in range(1, 9):
        tier = f"tier{tier_number}_fixture"
        tiers[tier] = []
        for item_number in range(2):
            sample_id = f"{tier}:{item_number:06d}"
            packet_id = sample_id.replace(":", "/")
            audio_sha256 = hashlib.sha256(sample_id.encode()).hexdigest()
            packet_sha256 = hashlib.sha256(packet_id.encode()).hexdigest()
            media_relpath = f"datasets/audio2tool/{tier}/{item_number}.wav"
            rows.append(
                {
                    "sample_id": sample_id,
                    "key": f"audio2tool:{sample_id}",
                    "tier": tier,
                    "packet_id": packet_id,
                    "audio_sha256": audio_sha256,
                    "audio_seconds": 1.0 + item_number,
                    "media_relpath": media_relpath,
                }
            )
            tiers[tier].append({"sample_id": sample_id, "key": f"audio2tool:{sample_id}"})
            canonical.append(f"{tier}\t{sample_id}\n")
            packet_rows.append(
                {
                    "packet_id": packet_id,
                    "packet_sha256": packet_sha256,
                    "audio_sha256": audio_sha256,
                }
            )
            _write_json(
                packet_root / packet_id / "packet.json",
                {
                    "schema": "saea-speech-feature-packet-v1",
                    "packet_id": packet_id,
                    "packet_sha256": packet_sha256,
                    "audio_sha256": audio_sha256,
                    "chunks": [{"n_tokens": tier_number * 10 + item_number}],
                },
            )
    split_hash = hashlib.sha256("".join(canonical).encode()).hexdigest()
    g1 = tmp_path / "g1.json"
    fixed = tmp_path / "fixed.json"
    promotion = packet_root / "promotion.json"
    _write_json(
        g1,
        {
            "schema": "saea-a2t-subset-receipt-v1",
            "count": 16,
            "items": rows,
        },
    )
    _write_json(
        fixed,
        {
            "schema": "saea-a2t-g5-fixed16-identity-receipt-v1",
            "split_name": G5_FIXED16_SPLIT_ID,
            "split_identity_hash": split_hash,
            "selection": {"selected_count": 16, "uses_task_text": False},
            "tiers": tiers,
        },
    )
    _write_json(
        promotion,
        {
            "schema": "saea-speech-feature-promotion-v1",
            "count": 16,
            "subset_receipt_sha256": hashlib.sha256(g1.read_bytes()).hexdigest(),
            "packets": packet_rows,
        },
    )
    return g1, fixed, promotion


def test_fixed16_surface_uses_only_g1_identity_and_sealed_packet_metadata(
    tmp_path: Path,
) -> None:
    g1, fixed, promotion = _runtime_fixture(tmp_path)

    surface = load_fixed16_runtime_surface(
        g1_receipt_path=g1,
        fixed16_identity_path=fixed,
        promotion_receipt_path=promotion,
    )

    assert len(surface.samples) == 16
    assert surface.split_id == G5_FIXED16_SPLIT_ID
    assert set(surface.packet_bindings) == {sample.sample_id for sample in surface.samples}
    assert max(surface.speech_feature_tokens_by_sample.values()) == 81
    assert all(sample.media_relpath.endswith(".wav") for sample in surface.samples)
    assert surface.source_field_names == (
        "audio_seconds",
        "audio_sha256",
        "key",
        "media_relpath",
        "packet_id",
        "sample_id",
        "tier",
    )


def test_fixed16_surface_refuses_identity_or_packet_drift(tmp_path: Path) -> None:
    g1, fixed, promotion = _runtime_fixture(tmp_path)
    document = json.loads(fixed.read_text(encoding="utf-8"))
    document["tiers"]["tier1_fixture"][0]["sample_id"] = "tier1_fixture:999999"
    _write_json(fixed, document)

    with pytest.raises(G5CorpusIntegrationError, match="identity|G1"):
        load_fixed16_runtime_surface(
            g1_receipt_path=g1,
            fixed16_identity_path=fixed,
            promotion_receipt_path=promotion,
        )


def test_prompt_fit_is_exact_under_closed_conservative_accounting(tmp_path: Path) -> None:
    g1, fixed, promotion = _runtime_fixture(tmp_path)
    surface = load_fixed16_runtime_surface(
        g1_receipt_path=g1,
        fixed16_identity_path=fixed,
        promotion_receipt_path=promotion,
    )
    compiler = CorpusFamilyCompiler.from_path(CORPUS)

    report = build_prompt_fit_report(compiler=compiler, runtime=surface)

    assert report["status"] == "PASS"
    assert report["accounting"]["tokenizer_contacts"] == 0
    assert report["accounting"]["ascii_bytes_per_text_token_ceiling"] == 1
    assert report["execute"]["state_ascii_bytes"] == 4_096
    assert report["execute"]["bundle_ascii_bytes"] <= 18_432
    assert report["execute"]["maximum_envelope_tokens"] <= 32_768
    assert report["plan"]["maximum_envelope_tokens"] <= 32_768


def test_committed_source_free_prompt_fit_receipt_is_self_consistent() -> None:
    receipt = json.loads(CHECK.read_text(encoding="utf-8"))

    assert receipt["status"] == "PASS"
    assert receipt["sources"]["corpus_sha256"] == COMMITTED_CORPUS_SHA256
    assert receipt["runtime"]["sample_count"] == 16
    assert receipt["runtime"]["task_text_fields_read"] == 0
    assert receipt["runtime"]["gold_fields_read"] == 0
    assert receipt["runtime"]["outputs_read"] == 0
    assert receipt["contacts"] == {
        "frozen_core": 0,
        "network": 0,
        "retriever": 0,
        "scorer": 0,
        "tokenizer": 0,
    }
    assert receipt["execute"]["maximum_envelope_tokens"] <= 32_768
