"""Supply alternatives retain acquired evidence across a real revision graph."""

from dataclasses import replace

import pytest

import test_native_episode_runner as harness_module
from test_native_episode_runner import _ActualEpisodeHarness
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_rails_controllers import _phase_supply
from test_stage3_supply_variant_interleaving import ARM_VALUE, _live_group
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize("mode", ["incremental", "repeated-selection"])
@pytest.mark.parametrize("side_selected", [(), (ARM_VALUE,)])
def test_revision_retains_each_arms_previous_supply(
    tmp_path, monkeypatch, mode, side_selected
):
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=1, max_contacts=9,
        planner_actions=("REVISE", "ACCEPT"),
    )
    group = _live_group()
    harness.config = replace(
        harness.config,
        roles=tuple(
            replace(role, supply_variants=group) if role.role_kind == "solver"
            else role for role in harness.config.roles
        ),
    )
    harness.program = replace(
        harness.program,
        phases=tuple(
            replace(phase, knowledge="supplied") if phase.name == "solver"
            else phase for phase in harness.program.phases
        ),
    )

    def selected(context, values):
        if mode == "incremental":
            return tuple(v for v in values if v not in context.query_state.retrieved_value_ids)
        return values

    def supply(phase, context):
        ids = selected(context, (ARM_VALUE,)) if phase == "solver" else ()
        return _phase_supply(context, value_ids=ids, facet_ids=("operation:dim",)) if ids else None

    real_binding = harness_module.NativeEpisodeRunBinding
    monkeypatch.setattr(
        harness_module, "NativeEpisodeRunBinding",
        lambda **kwargs: real_binding(**kwargs, supply_for_phase=supply),
    )

    def resolve(*, arm_id, phase_id, context):
        assert phase_id == "solver"
        values = (ARM_VALUE,) if arm_id == "plan" else side_selected
        ids = selected(context, values)
        return _phase_supply(context, value_ids=ids, facet_ids=("operation:dim",)) if ids else None

    harness.supply_variant_for_phase = resolve
    try:
        summary = harness.run()
    finally:
        close = harness.close()
    assert close["request_count"] == 9
    result = summary.results[0]
    assert [visit["stage"] for visit in result.native_episode_receipt["role_visits"]] == [
        "perception", "solver", "review", "planner", "solver", "review", "planner",
    ]
    requests = [
        payload["payload"] for channel, _, payload in harness.trace.records
        if channel == "MODEL_REQUEST"
    ]
    # First visit arms are contacts 1/2; revised arms are contacts 5/6.
    for index in (1, 5):
        assert tuple(x["evidence_id"] for x in requests[index]["supplied_evidence"]) == side_selected
    for index in (2, 6):
        assert [x["evidence_id"] for x in requests[index]["supplied_evidence"]] == [ARM_VALUE]
    assert result.final_query_state.retrieved_value_ids == (ARM_VALUE,)


def test_selection_accumulates_increment_or_repeat_and_rejects_duplicate_decision():
    from speech_aware_evidence_acquisition.rails.supply_variants import (
        SupplyVariantError, accumulate_arm_selection,
    )
    assert accumulate_arm_selection(("a",), ()) == ("a",)
    assert accumulate_arm_selection(("a",), ("a", "b")) == ("a", "b")
    assert accumulate_arm_selection(("a",), ("b",)) == ("a", "b")
    with pytest.raises(SupplyVariantError, match="must be unique"):
        accumulate_arm_selection(("a",), ("b", "b"))
