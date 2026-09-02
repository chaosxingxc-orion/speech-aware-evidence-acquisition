"""Deterministic full-handbook construction for Audio2Tool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails import a2t_executable_ground as ground
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import A2tKbRow


def _registry_row(
    name: str,
    *,
    category: str = "lighting",
    signature: str | None = None,
    description: str | None = None,
    defaults: str = "deviceId='default-device'",
    constraints: str = "state: [On, Off]",
) -> dict[str, str]:
    return {
        "tool_id": "1",
        "domain": "smart_home",
        "category": category,
        "tool_name": name,
        "signature": signature or f"{name}(deviceId: str, state: str)",
        "description": description or f"Use {name} for its declared operation.",
        "argument_defaults": defaults,
        "argument_constraints": constraints,
    }


def _row(
    unit_id: str,
    tool: str,
    keys: tuple[str, ...],
    *,
    text: str = "PRIVATE INVOCATION TEXT",
) -> A2tKbRow:
    return A2tKbRow(
        unit_id=unit_id,
        tier="tier1_direct",
        query_idx=int(unit_id.rsplit(":", 1)[-1]),
        text=text,
        domain="smart_home",
        category="lighting",
        tool_id=1,
        tool_name=tool,
        arg_signature=keys,
        arg_pairs=tuple((key, f"PRIVATE-{key}-VALUE") for key in keys),
        call_render=f"{tool}(PRIVATE VALUES)",
        extra_call_names=(),
        call_count=1,
        sample_ids=(f"tier1_direct:{unit_id.rsplit(':', 1)[-1]}",),
        item_ids=(int(unit_id.rsplit(":", 1)[-1]),),
        media_relpath_by_sample_id={},
        speaker_ids=("speaker",),
    )


def test_handbook_keeps_every_tool_and_all_argument_patterns_without_values() -> None:
    registry = (
        _registry_row("setLight"),
        _registry_row(
            "getLight",
            signature="getLight(deviceId: str)",
            defaults="deviceId='lamp-1'",
        ),
        _registry_row(
            "unusedTool",
            signature="unusedTool()",
            defaults="",
            constraints="",
        ),
    )
    rows = (
        _row("tier1_direct:000001", "setLight", ("deviceId", "state")),
        _row("tier1_direct:000002", "setLight", ("deviceId",)),
        _row("tier1_direct:000003", "getLight", ("deviceId",)),
    )

    artifact = ground.build_executable_ground(registry, rows)

    assert artifact.report["registry_tool_count"] == 3
    assert artifact.report["construction_tool_count"] == 2
    assert artifact.report["argument_pattern_family_count"] == 3
    assert artifact.report["argument_key_count"] == 2
    assert artifact.text.count("TOOL setLight\n") == 1
    assert artifact.text.count("TOOL getLight\n") == 1
    assert artifact.text.count("TOOL unusedTool\n") == 1
    assert "Required arguments: deviceId" in artifact.text
    assert "Optional arguments: state" in artifact.text
    assert "Allowed argument-key sets: {deviceId}; {deviceId, state}" in artifact.text
    assert "argument_defaults" not in artifact.text
    assert "default-device" not in artifact.text
    assert "lamp-1" not in artifact.text
    assert "PRIVATE INVOCATION TEXT" not in artifact.text
    assert "PRIVATE-deviceId-VALUE" not in artifact.text


def test_handbook_contains_fixed_execution_and_contrast_rules() -> None:
    artifact = ground.build_executable_ground(
        (
            _registry_row("setLight"),
            _registry_row("getLight", signature="getLight(deviceId: str)"),
        ),
        (
            _row("tier1_direct:000001", "setLight", ("deviceId", "state")),
            _row("tier1_direct:000002", "getLight", ("deviceId",)),
        ),
    )

    assert "Never copy a value from this handbook" in artifact.text
    assert "Use the final corrected value" in artifact.text
    assert "Emit one call per requested action" in artifact.text
    assert "Candidate tools in this contrast group: getLight, setLight" in artifact.text
    assert artifact.report["ascii_only"] is True
    assert artifact.report["default_literal_match_count"] == 0


def test_handbook_refuses_unknown_or_duplicate_tools_and_oversize_output() -> None:
    registry = (_registry_row("setLight"),)
    with pytest.raises(ground.ExecutableGroundError, match="outside the registry"):
        ground.build_executable_ground(
            registry,
            (_row("tier1_direct:000001", "unknown", ()),),
        )
    with pytest.raises(ground.ExecutableGroundError, match="duplicate"):
        ground.build_executable_ground((registry[0], registry[0]), ())
    with pytest.raises(ground.ExecutableGroundError, match="byte budget"):
        ground.build_executable_ground(
            (
                _registry_row(
                    "setLight",
                    description="x" * 200,
                    defaults="",
                    constraints="",
                ),
            ),
            (_row("tier1_direct:000001", "setLight", ()),),
            max_utf8_bytes=100,
        )


def test_committed_build_receipt_preserves_the_static_ground_gates() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    receipt_path = (
        repository_root
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-09-02-a2t-executable-ground-build-v1"
        / "build-receipt.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    report = receipt["handbook"]["report"]

    assert receipt["execution_profile"] == "model-free-check"
    assert set(receipt["contacts"].values()) == {0}
    assert receipt["offline_guard"]["outbound_connection_attempts"] == 0
    assert receipt["partition"]["construction_forbidden_intersection_count"] == 0
    assert receipt["handbook"]["deterministic_rebuild_equal"] is True
    assert report["registry_tool_count"] == 152
    assert report["construction_tool_count"] == 151
    assert report["argument_pattern_family_count"] == 354
    assert report["argument_key_count"] == 85
    assert report["default_literal_match_count"] == 0
    assert report["invocation_texts_rendered"] == 0
    assert report["argument_values_rendered"] == 0
    assert report["utf8_bytes"] <= report["max_utf8_bytes"]
    assert receipt["engineering_scope"]["network_jitter_testing"] is False
