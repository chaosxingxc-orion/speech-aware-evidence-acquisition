from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
from speech_aware_evidence_acquisition.rails.phase_tools import PHASE_KNOWLEDGE_TOOL


@pytest.mark.parametrize("named_tool_access", [False, True])
def test_automatic_supply_does_not_grant_named_store_tool_authority(named_tool_access):
    runtime = FlightRuntime.__new__(FlightRuntime)
    tool_spec = {
        "mode": "native-tools",
        "allowed_tools": ["saea-tool-task-contract-v1"],
        "knowledge_views": ["text"],
    }
    if named_tool_access:
        tool_spec["knowledge_store_ids"] = ["slot-contracts"]
        tool_spec["allowed_tools"].append(PHASE_KNOWLEDGE_TOOL)
    runtime._phase_tool_specs = lambda _policy: {"reviewer": tool_spec}
    runtime._phase_knowledge_catalog = lambda _snapshot: None
    runtime._experience_memory = None
    runtime._candidate_experience_memory = None
    runtime._speech_observations = None
    runtime._live_speech_config = None
    runtime._composed = SimpleNamespace(values={})
    seen = {}

    def build(_config, _program, **kwargs):
        seen.update(kwargs)
        return SimpleNamespace(native_enabled=True)

    runtime._phase_tool_builder = build
    stores, router, automatic_supply = object(), object(), object()
    binding = {
        "knowledge_snapshot": object(),
        "knowledge_stores": stores,
        "supply_for_store": router,
        "supply_for_phase": automatic_supply,
    }
    runtime._build_phase_tool_dispatcher(
        "native", SimpleNamespace(stop_rule="native-role-episode"),
        binding=binding, sink=None, client=None,
    )
    assert seen["supply_for_phase"] is automatic_supply
    assert seen["knowledge_stores"] is (stores if named_tool_access else None)
    assert seen["supply_for_store"] is (router if named_tool_access else None)
    assert binding["knowledge_stores"] is stores
    assert binding["supply_for_store"] is router


@pytest.mark.parametrize("bad", [None, {}, "unsupported"])
def test_runtime_refuses_invalid_rendering_before_empty_tool_shortcut(bad):
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntimeError

    runtime = FlightRuntime.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values={"knowledge_value_rendering": bad})
    with pytest.raises(FlightRuntimeError, match="knowledge_value_rendering"):
        runtime._phase_tool_specs("phase-native-candidates-review-revise-v1")
