"""Model-free tests for the G6 corpus and fixed16 runtime integration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.probes.a2t_g6_corpus_integration import (
    COMMITTED_CORPUS_SHA256,
    G6_FIXED16_SPLIT_ID,
    G6CorpusAdapter,
    G6CorpusIntegrationError,
    build_prompt_fit_report,
    load_g6_runtime_surface,
    measure_contact_prompt_fit,
)


REPO = Path(__file__).resolve().parents[2]
CORPUS = (
    REPO
    / "knowledge"
    / "audio2tool"
    / "g5-exhaustive-family-contracts-v1"
    / "corpus.json"
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="ascii")


def _runtime_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    g1_rows: list[dict[str, object]] = []
    selected: list[dict[str, str]] = []
    packet_rows: list[dict[str, str]] = []
    packet_root = tmp_path / "packets"
    tiers = [f"tier{number}_fixture" for number in range(1, 9)]
    for tier_number, tier in enumerate(tiers, start=1):
        for item_number in range(2):
            sample_id = f"{tier}:{item_number:06d}"
            key = f"audio2tool:{sample_id}"
            packet_id = sample_id.replace(":", "/")
            audio_sha256 = hashlib.sha256(sample_id.encode("ascii")).hexdigest()
            packet_sha256 = hashlib.sha256(packet_id.encode("ascii")).hexdigest()
            media_relpath = f"datasets/audio2tool/{tier}/{item_number}.wav"
            g1_rows.append(
                {
                    "sample_id": sample_id,
                    "key": key,
                    "tier": tier,
                    "packet_id": packet_id,
                    "audio_sha256": audio_sha256,
                    "audio_seconds": float(tier_number + item_number),
                    "media_relpath": media_relpath,
                }
            )
            selected.append({"sample_id": sample_id, "key": key, "tier": tier})
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
    split_hash = hashlib.sha256(
        "\n".join(sorted(f"audio2tool/{row['sample_id']}" for row in selected)).encode("ascii")
    ).hexdigest()
    g1_path = tmp_path / "g1.json"
    roster_path = tmp_path / "g6.json"
    promotion_path = packet_root / "promotion.json"
    _write_json(
        g1_path,
        {"schema": "saea-a2t-subset-receipt-v1", "count": 16, "items": g1_rows},
    )
    _write_json(
        roster_path,
        {
            "schema": "saea-a2t-g6-family-sweep-fixed16-identity-receipt-v1",
            "split_name": G6_FIXED16_SPLIT_ID,
            "split_role": "discovery",
            "tier_order": tiers,
            "selection": {
                "items_per_tier": 2,
                "uses_task_text": False,
                "uses_audio": False,
                "uses_gold": False,
                "uses_outputs": False,
                "uses_scores": False,
                "uses_rewards": False,
                "uses_test": False,
                "uses_future_turns": False,
                "uses_model_or_tool": False,
                "uses_network_or_tokenizer_or_scorer": False,
            },
            "selected": selected,
            "selected_tier_counts": {tier: 2 for tier in tiers},
            "manifest_split_identity_hash": split_hash,
            "split_identity_hash": split_hash,
            "source_hashes": {"g1": hashlib.sha256(g1_path.read_bytes()).hexdigest()},
        },
    )
    _write_json(
        promotion_path,
        {
            "schema": "saea-speech-feature-promotion-v1",
            "count": 16,
            "subset_receipt_sha256": hashlib.sha256(g1_path.read_bytes()).hexdigest(),
            "packets": packet_rows,
        },
    )
    return g1_path, roster_path, promotion_path


def test_adapter_maps_all_contracts_once_and_preserves_exact_skeletons() -> None:
    adapter = G6CorpusAdapter.from_path(CORPUS)

    assert adapter.corpus_sha256 == COMMITTED_CORPUS_SHA256
    assert len(adapter.family_bundles) == 28
    assert sum(len(bundle.contracts) for bundle in adapter.family_bundles) == 152
    assert len(adapter.family_reference_sha256s) == 28
    assert adapter.build_sweep().family_tags == tuple(
        bundle.family_tag for bundle in adapter.family_bundles
    )
    media = next(
        bundle
        for bundle in adapter.family_bundles
        if bundle.family_tag == "smart-car-media-cabin"
    )
    playback = next(
        contract for contract in media.contracts if contract.tool_name == "controlPlayback"
    )
    assert playback.legal_key_skeletons == (
        (),
        ("action",),
        ("action", "deviceId"),
    )
    rendered = media.render()
    assert rendered.count("REFERENCE-ONLY FAMILY MATERIAL") == 1
    assert all(rendered.count(f"Tool: {contract.tool_name}") == 1 for contract in media.contracts)


def test_exact_skeletons_reject_a_union_approximation() -> None:
    adapter = G6CorpusAdapter.from_path(CORPUS)
    sweep = adapter.build_sweep()
    abstain = (
        '{"applicable":false,"candidates":[],"correction_evidence":[],'
        '"turn_evidence":[],"role_evidence":[],"ordering_evidence":[]}'
    )
    responses = {tag: abstain for tag in sweep.family_tags}
    responses["smart-car-media-cabin"] = json.dumps(
        {
            "applicable": True,
            "candidates": [
                {
                    "tool_name": "controlPlayback",
                    "speech_spans": ["Kitchen"],
                    "argument_bindings": [
                        {"key": "deviceId", "value": "Kitchen", "speech_span": "Kitchen"}
                    ],
                    "unresolved_required_arguments": [],
                }
            ],
            "correction_evidence": [],
            "turn_evidence": [],
            "role_evidence": [],
            "ordering_evidence": [],
        },
        separators=(",", ":"),
    )
    reports = sweep.parse_scan_responses(responses)

    assert sweep.parse_resolve_response(
        '[{"name":"controlPlayback","arguments":{"deviceId":"Kitchen"}}]',
        reports=reports,
    ).valid is False


def test_runtime_surface_loads_only_roster_g1_and_sealed_packet_metadata(
    tmp_path: Path,
) -> None:
    g1, roster, promotion = _runtime_fixture(tmp_path)

    surface = load_g6_runtime_surface(
        g1_receipt_path=g1,
        g6_roster_path=roster,
        promotion_receipt_path=promotion,
    )

    assert surface.split_id == G6_FIXED16_SPLIT_ID
    assert len(surface.samples) == 16
    assert max(surface.speech_feature_tokens_by_sample.values()) == 81
    assert set(surface.packet_bindings) == {sample.sample_id for sample in surface.samples}
    assert surface.source_field_names == (
        "audio_seconds",
        "audio_sha256",
        "key",
        "media_relpath",
        "packet_id",
        "sample_id",
        "tier",
    )


def test_runtime_surface_refuses_roster_or_packet_drift(tmp_path: Path) -> None:
    g1, roster, promotion = _runtime_fixture(tmp_path)
    document = json.loads(roster.read_text(encoding="ascii"))
    document["selected"][0]["key"] = "audio2tool:wrong"
    _write_json(roster, document)

    with pytest.raises(G6CorpusIntegrationError, match="roster|G1"):
        load_g6_runtime_surface(
            g1_receipt_path=g1,
            g6_roster_path=roster,
            promotion_receipt_path=promotion,
        )


def test_scan_prompt_fit_and_dynamic_resolve_fit_are_pure_and_exact(tmp_path: Path) -> None:
    g1, roster, promotion = _runtime_fixture(tmp_path)
    runtime = load_g6_runtime_surface(
        g1_receipt_path=g1,
        g6_roster_path=roster,
        promotion_receipt_path=promotion,
    )
    adapter = G6CorpusAdapter.from_path(CORPUS)

    def token_counter(text: str) -> int:
        return (len(text.encode("ascii")) + 3) // 4

    report = build_prompt_fit_report(
        adapter=adapter,
        runtime=runtime,
        task_contract="Return only registered calls grounded in the original speech.",
        token_counter=token_counter,
    )

    assert report["status"] == "PASS"
    assert report["scan"]["exact_context_count"] == 16 * 28
    assert len(report["scan"]["family_maxima"]) == 28
    assert report["resolve"]["precomputed"] is False
    assert report["contacts"] == {
        "frozen_core": 0,
        "network": 0,
        "retriever": 0,
        "scorer": 0,
    }

    sample = runtime.samples[0]
    binding = runtime.packet_bindings[sample.sample_id]
    reports = adapter.build_sweep().parse_scan_responses(
        {
            tag: '{"applicable":false,"candidates":[],"correction_evidence":[],'
            '"turn_evidence":[],"role_evidence":[],"ordering_evidence":[]}'
            for tag in adapter.renderer.family_tags
        }
    )
    context = adapter.build_sweep().build_resolve_context(
        speech_packet_id=binding["packet_id"],
        speech_packet_sha256=binding["sha256"],
        task_contract="Return only registered calls grounded in the original speech.",
        reports=reports,
    )
    exact = context.render_control_text()
    dynamic = measure_contact_prompt_fit(
        context=context,
        rendered_request=exact,
        runtime=runtime,
        sample_id=sample.sample_id,
        token_counter=token_counter,
    )
    assert dynamic["status"] == "PASS"
    assert dynamic["rendered_request_ascii_bytes"] == len(exact.encode("ascii"))
    assert dynamic["nominated_contract_count"] == 0
    assert dynamic["remaining_tokens"] >= 8_192
