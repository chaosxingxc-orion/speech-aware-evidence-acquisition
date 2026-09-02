"""Contact-free tests for the G7 fixed16 launcher."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g7-exhaustive-example-ground-fixed16-v1/launcher/"
    "launch_a2t_g7_fixed16.py"
)
SPEC = importlib.util.spec_from_file_location("g7_launcher", LAUNCHER)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def _ground():
    bundles = []
    for family in range(28):
        tools = tuple(
            SimpleNamespace(
                tool_name=f"t_{family}_{index}",
                operation="Operate.",
                types=(),
                legal_key_skeletons=((),),
                patterns=(),
            )
            for index in range(6 if family < 12 else 5)
        )
        bundles.append(
            SimpleNamespace(
                family_tag=f"f-{family}",
                family_label=f"F {family}",
                tools=tools,
                tool_names=tuple(tool.tool_name for tool in tools),
                text=f"Family {family} examples.",
                sha256=f"{family:064x}",
                ascii_bytes=24,
            )
        )
    return SimpleNamespace(
        bundles=tuple(bundles),
        bundles_by_family={bundle.family_tag: bundle for bundle in bundles},
        tool_names=tuple(name for bundle in bundles for name in bundle.tool_names),
        sha256=module.GROUND_SHA256,
        receipt={"schema": "saea-a2t-construction-example-ground-receipt-v1"},
    )


def test_preflight_binds_identity_builder_and_exact_protocol() -> None:
    report = module.preflight_ground(_ground(), speech_feature_tokens_max=100)

    assert report["split_identity_hash"] == (
        "94a10c359dfe9e6a96cd63940c4dcb52fc7206e4c0e7d855733b21b69b987212"
    )
    assert report["contacts"] == 480
    assert report["family_count"] == 28
    assert report["tool_count"] == 152
    assert report["slots"] == report["max_concurrent_model_requests"] == 2
    assert report["queue_depth"] == 4
    assert report["audio_contacts_per_sample"] == 2
    assert report["builder_commit"] == "7046ce6e7fbbba67ddbae5f122748e2158761e23"


def test_byte_upper_bound_preflight_measures_all_static_prompts() -> None:
    report = module.preflight_ground(_ground(), speech_feature_tokens_max=100)

    assert report["token_counter"] == "utf8-byte-construction-upper-bound"
    assert report["obs_prompt"]["completion_tokens"] == 512
    assert len(report["evidence_prompts"]) == 28
    assert all(row["remaining_tokens"] >= 8192 for row in report["evidence_prompts"])
    assert report["resolve_empty_assessment_base_prompt"]["remaining_tokens"] >= 8192
    assert report["resolve_worst_normalized_assessment_prompt"]["remaining_tokens"] >= 8192
    assert report["resolve_measurement"] == "dynamic-after-152-assessments-seal"


def test_execution_plan_binds_exact_population_and_budget() -> None:
    plan = module.execution_plan("attempt-g7-unit")

    assert plan.split_identity_hash == module.SPLIT_IDENTITY_HASH
    assert plan.protocol_hash == module.PROTOCOL_SHA256
    assert plan.planned_model_calls == 480
    assert plan.planned_speech_audio_seconds == 185
