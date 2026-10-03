"""Opt-in node affinity through the actual flight and native request path."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.dispatch_slot_fill import (
    NativePrefixSlotsError, parse_native_prefix_slots,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401


BLOCK = {
    "schema": "saea-native-prefix-slots-v1",
    "role_slots": {"perception": 0, "solver": 1, "reviewer": 2, "planner": 3},
}


def _config(**overrides):
    return SimpleNamespace(
        roles=tuple(SimpleNamespace(phase_id=r, max_iterations=1) for r in BLOCK["role_slots"]),
        relisten_json=None, context_policy_json=None, **overrides,
    )


def _semantic_output(value):
    # Request identities and their hashes change when id_slot changes. Keep
    # response custody, role/decision history, answers and every other field.
    if isinstance(value, dict):
        return {key: _semantic_output(item) for key, item in value.items()
                if key not in {"request_id", "request_sha256", "slot_id", "slot_ids"}}
    if isinstance(value, list):
        return [_semantic_output(item) for item in value]
    return value


def test_absence_and_immutable_roundtrip():
    assert parse_native_prefix_slots({}) is None
    raw = {**BLOCK, "role_slots": dict(BLOCK["role_slots"])}
    parsed = parse_native_prefix_slots({"native_prefix_slots": raw})
    parsed.validate(_config(), slot_count=4)
    raw["role_slots"]["solver"] = 0
    assert parsed.as_json() == BLOCK
    changed = parsed.slot_bindings()
    changed["solver"] = 0
    assert parsed.slot_bindings() == BLOCK["role_slots"]


@pytest.mark.parametrize("raw", [
    None, True, {}, {**BLOCK, "schema": "wrong"}, {**BLOCK, "extra": 1},
    {**BLOCK, "role_slots": {}}, {**BLOCK, "role_slots": []},
    {**BLOCK, "role_slots": {"solver": True}},
    {**BLOCK, "role_slots": {"solver": -1}},
    {**BLOCK, "role_slots": {"solver": 0, "review": 0}},
    {**BLOCK, "role_slots": {"": 0}},
])
def test_invalid_declared_blocks_are_refused(raw):
    with pytest.raises(NativePrefixSlotsError):
        parse_native_prefix_slots({"native_prefix_slots": raw})


@pytest.mark.parametrize("slots", [True, 0, 3, "4"])
def test_geometry_is_validated_before_contacts(slots):
    parsed = parse_native_prefix_slots({"native_prefix_slots": BLOCK})
    with pytest.raises(NativePrefixSlotsError):
        parsed.validate(_config(), slot_count=slots)


def test_every_reachable_role_requires_a_distinct_slot():
    parsed = parse_native_prefix_slots({"native_prefix_slots": BLOCK})
    with pytest.raises(NativePrefixSlotsError, match="native"):
        parsed.validate(None, slot_count=4)
    config = _config()
    config.roles = config.roles[:-1]
    with pytest.raises(NativePrefixSlotsError, match="roles"):
        parsed.validate(config, slot_count=4)
    config = _config()
    config.relisten_json = "{}"
    with pytest.raises(NativePrefixSlotsError, match="roles"):
        parsed.validate(config, slot_count=4)
    extended = {**BLOCK, "role_slots": {**BLOCK["role_slots"], "relisten": 4}}
    parse_native_prefix_slots({"native_prefix_slots": extended}).validate(config, slot_count=5)


def test_unscheduled_context_cleaning_is_refused(monkeypatch):
    from speech_aware_evidence_acquisition.rails import node_context_binding
    monkeypatch.setattr(node_context_binding, "node_context_cleaning_boundaries", lambda _: ("solver",))
    config = _config()
    config.context_policy_json = "{}"
    with pytest.raises(NativePrefixSlotsError, match="cleaning"):
        parse_native_prefix_slots({"native_prefix_slots": BLOCK}).validate(config, slot_count=4)


def test_model_free_acquisition_needs_no_model_slot():
    config = _config()
    config.roles += (SimpleNamespace(phase_id="acquisition", max_iterations=0),)
    config.context_policy_json = "{}"
    parse_native_prefix_slots({"native_prefix_slots": BLOCK}).validate(config, slot_count=4)


@pytest.mark.parametrize("mode", ["absent", "fixed", "missing_role", "geometry"])
def test_flight_preparation_refuses_invalid_binding_without_contacts(mode):
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime, FlightRuntimeError
    runtime = object.__new__(FlightRuntime)
    values = {"native_prefix_slots": BLOCK, "policy": "fixed"}
    runtime._composed = SimpleNamespace(values=values)
    runtime._adapter = SimpleNamespace(serving_geometry=lambda: {"slots": 3 if mode == "geometry" else 4})
    if mode == "absent":
        values.pop("native_prefix_slots")
        assert runtime._native_prefix_slots() is None
        return
    config = _config()
    if mode == "missing_role":
        config.roles = config.roles[:-1]
    with pytest.raises(FlightRuntimeError):
        runtime._native_prefix_slots(None if mode == "fixed" else config)


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize("max_revisions", [0, 1])
def test_real_flight_routes_roles_and_preserves_model_content(tmp_path, monkeypatch, max_revisions):
    from test_flight_resume_recovery import _harness, _skeleton
    from test_dispatch_slot_fill import _rendered
    outputs = []
    for name, block in (("off", None), ("on", BLOCK)):
        harness = _harness(tmp_path, name, ("s1", "s2"), max_revisions=max_revisions)
        geometry = dict(harness.adapter.serving_geometry())
        monkeypatch.setattr(harness.adapter, "serving_geometry", lambda: {**geometry, "slots": 4})
        runtime = _skeleton(harness, monkeypatch)
        if block is not None:
            runtime._composed.values["native_prefix_slots"] = block
        try:
            rows, contacts, _, receipt, _ = runtime._dispatch_phase_program(
                harness.client, harness.plan, harness.program.program_id,
            )
        finally:
            harness.close()
        if block is not None:
            assert receipt["native_prefix_slots"] == BLOCK
            for (_, role, _, _), prepared in harness.prepared.items():
                assert prepared["slot_id"] == BLOCK["role_slots"][role]
        else:
            assert "native_prefix_slots" not in receipt
        assert contacts == 2 * (4 + 3 * max_revisions)
        runtime._output_rows = rows
        canonical = runtime._canonical_output_rows(harness.client)
        assert all(harness.events.index(("fit", key)) < harness.events.index(("dispatch", key))
                   for key in harness.prepared)
        outputs.append((_rendered(harness), _semantic_output(canonical)))
    assert outputs[0] == outputs[1]


def test_whole_policy_actions_cannot_change_slot_envelope():
    from speech_aware_evidence_acquisition.rails.system_episode_policy import (
        SystemEpisodePolicy, SystemEpisodePolicyError,
    )
    from speech_aware_evidence_acquisition.rails.native_episode_config import NativeEpisodeRunBinding
    config = SimpleNamespace(max_contacts=4, local_tool_workers=0)
    reference = NativeEpisodeRunBinding(
        config=config, program=SimpleNamespace(max_contacts=4),
        material_for_phase=None, render_request=None, request_gate=None,
    )
    selector = object.__new__(SystemEpisodePolicy)
    selector._reference = reference
    selector.assert_envelope(reference)
    with pytest.raises(SystemEpisodePolicyError, match="envelope"):
        selector.assert_envelope(replace(reference, prefix_slots=parse_native_prefix_slots({"native_prefix_slots": BLOCK})))
    config = _config()
    config.max_contacts = 4
    config.local_tool_workers = 0
    reference = replace(reference, config=config, prefix_slots=parse_native_prefix_slots({"native_prefix_slots": BLOCK}))
    selector._reference = reference
    selector.assert_envelope(reference)
    changed = _config()
    changed.max_contacts = 4
    changed.local_tool_workers = 0
    changed.roles = changed.roles[:-1]
    with pytest.raises(SystemEpisodePolicyError, match="roles"):
        selector.assert_envelope(replace(reference, config=changed))


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize("local_workers", [0, 1])
def test_native_tool_continuation_keeps_role_affinity(tmp_path, local_workers):
    from test_native_episode_runner import _ActualEpisodeHarness
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=2, max_revisions=0, max_contacts=5,
        planner_actions=("ACCEPT",), reviewer_task_tool=True,
    )
    harness.config = replace(harness.config, local_tool_workers=local_workers)
    harness.prefix_slots = parse_native_prefix_slots({"native_prefix_slots": BLOCK})
    harness.slot_count = 4
    try:
        summary = harness.run()
    finally:
        harness.close()
    assert len(summary.results) == 2
    assert len(harness.prepared) == 10
    assert len(harness.tool_contacts) == 2
    for (_, role, _, _), prepared in harness.prepared.items():
        assert prepared["slot_id"] == BLOCK["role_slots"][role]


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize("malformed", [True, False])
def test_runner_refuses_wrong_binding_before_any_request(tmp_path, malformed):
    from test_native_episode_runner import _ActualEpisodeHarness
    from speech_aware_evidence_acquisition.rails.runner import RailsRunnerError
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=4,
        planner_actions=("ACCEPT",),
    )
    harness.prefix_slots = object() if malformed else parse_native_prefix_slots({"native_prefix_slots": BLOCK})
    try:
        with pytest.raises(RailsRunnerError):
            harness.run()
        assert not harness.prepared and not harness.dispatched
    finally:
        harness.close()
