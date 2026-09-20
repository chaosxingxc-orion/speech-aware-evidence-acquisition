"""Item E23 (2026-09-20): a native-tools arm with no phase_tools is a tool-free episode.

Repair form 0-B (owner decision 55) withdraws the Reviewer's task-contract tool: the baseline keeps the
speech-feature-query-native-tools arm (its request contract, its audio path) and declares no
``phase_tools``. Before this item the runtime demanded a tool-schema resolver seam for that arm and
refused the four-row smoke of cell B1-notool before any contact; now the schema tuple is empty, the
same branch the raw-speech native arm already took."""

from speech_aware_evidence_acquisition.core.flight.runtime import (
    TOOL_FREE_NATIVE_ARMS,
    tool_free_native_arm,
)


def test_a_native_arm_without_phase_tools_is_tool_free():
    for arm in sorted(TOOL_FREE_NATIVE_ARMS):
        assert tool_free_native_arm(arm, {})
        assert tool_free_native_arm(arm, {"phase_tools": {}})
        assert tool_free_native_arm(arm, {"phase_tools": None})


def test_a_native_arm_with_a_reviewer_toolkit_is_not_tool_free():
    values = {"phase_tools": {"reviewer": {"mode": "native-tools", "allowed_tools": ["saea-tool-task-contract-v1"], "source_authority_role": "reviewer"}}}
    for arm in sorted(TOOL_FREE_NATIVE_ARMS):
        assert not tool_free_native_arm(arm, values)


def test_non_native_arms_never_take_the_branch():
    for arm in ("speech-feature-query", "bare-core", "fixed-legal-context", "", None):
        assert not tool_free_native_arm(arm, {})


def test_the_b1_notool_baselines_are_tool_free_on_their_own_arm():
    import io
    import json

    for name in ("slurp-native-anchor-exemplars-k20-notool-v1", "slurp-native-anchor-exemplars-k20-notool-smoke-4-v1"):
        d = json.load(io.open(f"configs/baseline/{name}.json", encoding="utf-8"))
        assert d["arm"] == "speech-feature-query-native-tools"
        assert "phase_tools" not in d
        assert tool_free_native_arm(d["arm"], d)


def test_the_core_client_accepts_the_explicit_empty_tuple_and_nothing_else():
    """Item E23b: the empty tuple is the tool-free contract; None and lists are not."""
    import pytest
    from speech_aware_evidence_acquisition.rails.core_client import (
        FrozenCoreClientError,
        _tool_schemas_sha256,
        _validate_tool_schemas,
        tool_free_native_schemas,
    )

    assert tool_free_native_schemas(())
    assert not tool_free_native_schemas(None)
    assert not tool_free_native_schemas([])
    assert not tool_free_native_schemas(({"type": "function", "function": {"name": "x"}},))
    with pytest.raises(FrozenCoreClientError, match="non-empty tool_schemas"):
        _validate_tool_schemas(())
    assert isinstance(_tool_schemas_sha256(()), str) and len(_tool_schemas_sha256(())) == 64
