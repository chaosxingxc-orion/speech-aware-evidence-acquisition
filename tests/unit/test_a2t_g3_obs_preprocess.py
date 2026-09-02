from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_g3_obs_preprocess import (
    G3ObsPreprocessError,
    build_execution_plan,
    build_merged_outputs,
    build_preprocess_plan,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
TIERS = (
    "tier1_direct",
    "tier2_parametric",
    "tier3_multi_intent",
    "tier4_implicit",
    "tier5_needle",
    "tier6_correction",
    "tier7_multiturn",
    "tier8_intent_blending",
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _fixtures():
    roster_items = []
    media_items = []
    promotions = {"g1": [], "cpv2": [], "ground": []}
    for tier_index, tier in enumerate(TIERS):
        for offset in range(5):
            item_id = tier_index * 100 + offset + 1
            sample_id = f"{tier}:{item_id:06d}"
            packet_id = sample_id.replace(":", "/")
            audio_sha = _sha(f"original:{sample_id}")
            roster_items.append(
                {
                    "audio_seconds": 1.0,
                    "audio_sha256": audio_sha,
                    "id": item_id,
                    "key": f"audio2tool:{sample_id}",
                    "media_relpath": f"datasets/audio2tool/{packet_id}.wav",
                    "packet_id": packet_id,
                    "query_block": f"{tier}:query-{item_id:05d}",
                    "sample_id": sample_id,
                    "selection_rank_sha256": _sha(f"rank:{sample_id}"),
                    "tier": tier,
                }
            )
            media = {
                "audio_seconds": 1.0,
                "audio_sha256": audio_sha,
                "media_relpath": f"datasets/audio2tool/{packet_id}.wav",
                "sample_id": sample_id,
                "tier": tier,
            }
            if tier == "tier7_multiturn":
                media.update(
                    {
                        "audio_seconds": 10.0 + offset,
                        "audio_sha256": _sha(f"dialogue:{sample_id}"),
                        "media_relpath": f"derived/g3/{packet_id}.wav",
                        "source_final_turn_media_relpath": roster_items[-1]["media_relpath"],
                    }
                )
            media_items.append(media)
            promotions[("g1", "cpv2", "ground")[offset % 3]].append(
                {
                    "audio_sha256": audio_sha,
                    "decoder_gguf_sha256": "d" * 64,
                    "mmproj_sha256": "e" * 64,
                    "packet_id": packet_id,
                    "packet_sha256": _sha(f"packet:{sample_id}"),
                }
            )
    roster = {
        "count": 40,
        "items": roster_items,
        "run_identity_hash": _sha("run-identity"),
        "split_identity_hash": _sha("split-identity"),
        "split_name": "A2T-G3-PILOT-40",
    }
    media_manifest = {
        "count": 40,
        "items": media_items,
        "schema": "saea-a2t-g3-runtime-media-manifest-v1",
        "tier7_complete_dialogue_count": 5,
    }
    source_promotions = {
        name: {
            "count": len(packets),
            "feature_root": "/feature-root",
            "packets": packets,
            "receipt_sha256": _sha(f"receipt:{name}"),
        }
        for name, packets in promotions.items()
    }
    return roster, media_manifest, source_promotions


def _derived_packets(plan):
    return [
        {
            "audio_sha256": item.audio_sha256,
            "decoder_gguf_sha256": "d" * 64,
            "mmproj_sha256": "e" * 64,
            "packet_id": item.packet_id,
            "packet_sha256": _sha(f"derived-packet:{item.sample_id}"),
        }
        for item in plan.derived
    ]


def test_plan_verifies_all_originals_then_partitions_35_reused_and_5_derived() -> None:
    roster, media, promotions = _fixtures()

    plan = build_preprocess_plan(roster, media, promotions)

    assert len(plan.original_verified) == 40
    assert len(plan.reused) == 35
    assert len(plan.derived) == 5
    assert plan.planned_contacts == 5
    assert plan.derived_audio_seconds == 60.0
    assert plan.execution_plan_audio_seconds == 60
    assert all(item.tier == "tier7_multiturn" for item in plan.derived)
    assert all(item.packet_id.startswith("g3_complete_dialogue/") for item in plan.derived)
    assert {item.packet_id for item in plan.derived}.isdisjoint(
        {item.packet_id for item in plan.original_verified}
    )


def test_plan_and_merge_are_deterministic_under_input_reordering() -> None:
    roster, media, promotions = _fixtures()
    first = build_preprocess_plan(roster, media, promotions)
    reversed_plan = build_preprocess_plan(
        {**roster, "items": list(reversed(roster["items"]))},
        {**media, "items": list(reversed(media["items"]))},
        dict(reversed(tuple(promotions.items()))),
    )

    first_receipt, first_bindings = build_merged_outputs(
        first, _derived_packets(first), feature_root="/feature-root"
    )
    second_receipt, second_bindings = build_merged_outputs(
        reversed_plan,
        list(reversed(_derived_packets(reversed_plan))),
        feature_root="/feature-root",
    )

    assert first == reversed_plan
    assert first_receipt == second_receipt
    assert first_bindings == second_bindings
    assert first_receipt["count"] == 40
    assert first_receipt["reused_original_count"] == 35
    assert first_receipt["derived_complete_dialogue_count"] == 5
    assert first_receipt["encode_contacts"] == 5
    assert len(first_bindings["bindings"]) == 40


def test_merge_binds_audio_and_packet_id_and_contains_no_task_information() -> None:
    roster, media, promotions = _fixtures()
    plan = build_preprocess_plan(roster, media, promotions)
    receipt, bindings = build_merged_outputs(
        plan, _derived_packets(plan), feature_root="/feature-root"
    )

    encoded = json.dumps({"receipt": receipt, "bindings": bindings}, sort_keys=True)
    for forbidden in (
        "expected_tool_call",
        "extracted_params",
        "additional_tool_calls",
        '"content"',
        '"query"',
        '"score"',
    ):
        assert forbidden not in encoded
    assert all(set(value) == {"packet_id", "sha256"} for value in bindings["bindings"].values())


def test_plan_and_merge_refuse_audio_or_packet_identity_drift() -> None:
    roster, media, promotions = _fixtures()
    promotions["g1"]["packets"][0]["audio_sha256"] = "0" * 64
    with pytest.raises(G3ObsPreprocessError, match="original audio SHA-256"):
        build_preprocess_plan(roster, media, promotions)

    roster, media, promotions = _fixtures()
    plan = build_preprocess_plan(roster, media, promotions)
    derived = _derived_packets(plan)
    derived[0]["audio_sha256"] = "0" * 64
    with pytest.raises(G3ObsPreprocessError, match="derived audio SHA-256"):
        build_merged_outputs(plan, derived, feature_root="/feature-root")


def test_execution_plan_accounts_only_for_five_derived_contacts() -> None:
    roster, media, promotions = _fixtures()
    plan = build_preprocess_plan(roster, media, promotions)

    execution = build_execution_plan(
        plan,
        run_id="SAEA-SN-A2T-G3-OBS-PREPROCESS",
        protocol_hash="a" * 64,
        attempt_id="attempt-g3",
    )

    assert execution.planned_model_calls == 5
    assert execution.planned_speech_audio_seconds == 60
    assert execution.split_identity_hash == roster["run_identity_hash"]
    assert execution.execution_profile == "bounded-discovery-probe"


def test_launcher_exposes_only_preflight_and_one_shot_run_modes() -> None:
    source = (REPO_ROOT / "scripts" / "a2t_g3_obs_preprocess.py").read_text(
        encoding="utf-8"
    )

    assert '"--preflight-only"' in source
    assert '"--run"' in source
    assert "ExecutionPlan" in source
    assert "materialize_legacy_cached_speech_feature_packets" in source
    assert "retry" not in source.lower()
    assert "response =" not in source
