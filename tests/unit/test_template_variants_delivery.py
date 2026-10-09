"""NX programme E1 (2026-10-09): the node-template arm kind through the
flight runtime's DELIVERY validator, not only the runner's composition check.

The 4-row smoke of the NX R1 cell sealed through ``FlightRuntime.seal`` ->
``_canonical_output_rows``, whose custody re-check read the declared arm list
from ``roles.solver.supply_variants`` only and so refused a cell declaring
``roles.solver.template_variants``. These proofs drive the SAME production
walk (graph, request renderer, state sealer, trace sink) the live-wiring proofs
use, then hand the rows to the runtime's own ``_canonical_output_rows`` -- the
function the smoke worker's seal calls -- with the RAW declared native block
the cell's fragment carries.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.bundle.outputs import _verify_outputs_trace_binding
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime, FlightRuntimeError
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

pytest.importorskip("openjiuwen", reason="OpenJiuwen unavailable")

import test_native_episode_runner as runner_tests  # noqa: E402
from test_llama_server_transport import _spawn_live_matching_process  # noqa: E402,F401
from test_stage3_supply_variant_interleaving import (  # noqa: E402
    ARM_VALUE,
    _arm_resolver,
    _live_config,
    _live_group,
)
from test_template_variants_live import (  # noqa: E402
    _arm_output,
    _block,
    _group,
    _template_harness,
)

pytestmark = pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")


def _raw_native(harness, *, solver_role):
    return {
        "finite_completion_policy": harness.config.finite_completion_policy,
        "exhaustion_policy": "raise", "max_revisions": 0,
        "actions": dict(zip(("accept", "revise", "acquire"), harness.config.actions)),
        "roles": {"solver": {"phase_id": "solver", **solver_role}},
    }


def _runtime(harness, summary, raw_native):
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values={"native_episode": raw_native})
    runtime._plan = harness.plan
    runtime._phase_summaries = [summary]
    runtime._output_rows = [
        {
            "sample_id": row.sample_id, "final_response_text": row.final_response_text,
            "native_episode_receipt": row.native_episode_receipt,
            **({"supply_variants": dict(row.supply_variants)}
               if row.supply_variants is not None else {}),
        }
        for row in summary.results
    ]
    runtime._result_kind = lambda: "answer"
    runtime._arm = lambda: harness.client.arm
    return runtime


def _four_row_template_world(tmp_path, monkeypatch):
    class FourRowWorld(runner_tests._World):
        SAMPLE_SPECS = (("s1", 2.0), ("s2", 3.5), ("s3", 2.5), ("s4", 3.0))

    monkeypatch.setattr(runner_tests, "_World", FourRowWorld)
    group = _group(twin=True)  # t1, t2, aa (twin), lock
    harness = _template_harness(tmp_path, group, rows=4)
    return group, harness


def test_four_template_rows_seal_through_the_runtime_delivery_validator(tmp_path, monkeypatch):
    group, harness = _four_row_template_world(tmp_path, monkeypatch)
    summary = harness.run()
    try:
        runtime = _runtime(
            harness, summary,
            _raw_native(harness, solver_role={"template_variants": _block(twin=True)}),
        )
        outputs = runtime._canonical_output_rows(harness.client)
    finally:
        harness.close()
    assert [row["sample_id"] for row in outputs] == ["s1", "s2", "s3", "s4"]
    for row, result in zip(outputs, summary.results):
        assert row["supply_variants"]["schema"] == "saea-supply-variant-arms-v4"
        assert [arm["arm_id"] for arm in row["supply_variants"]["arms"]] == list(group.arm_ids)
        assert len(row["supply_variants"]["arms"]) == group.arm_count
        assert row["text"] == result.final_response_text == _arm_output(
            (result.sample_id, "solver", 1, group.arm_count)
        )
    records = {rid: payload for _, rid, payload in harness.trace.records}
    _verify_outputs_trace_binding(tuple(outputs), records)


def test_the_validator_compares_declared_arms_with_the_sealed_arms(tmp_path, monkeypatch):
    """A template group whose declared arms differ from the sealed arms is
    refused by the receipt validator."""

    _group_, harness = _four_row_template_world(tmp_path, monkeypatch)
    summary = harness.run()
    try:
        declared = _block(twin=True)
        declared["arms"][0]["arm_id"] = "renamed"
        runtime = _runtime(
            harness, summary, _raw_native(harness, solver_role={"template_variants": declared}),
        )
        with pytest.raises(FlightRuntimeError, match="declared order"):
            runtime._canonical_output_rows(harness.client)
        shorter = _block(twin=False)
        runtime = _runtime(
            harness, summary, _raw_native(harness, solver_role={"template_variants": shorter}),
        )
        with pytest.raises(FlightRuntimeError, match="every declared arm"):
            runtime._canonical_output_rows(harness.client)
    finally:
        harness.close()


def test_a_template_receipt_is_never_validated_against_a_supply_declaration(tmp_path, monkeypatch):
    _group_, harness = _four_row_template_world(tmp_path, monkeypatch)
    summary = harness.run()
    try:
        raw = _raw_native(harness, solver_role={"supply_variants": _block(twin=True)})
        with pytest.raises(FlightRuntimeError, match="kind does not match"):
            _runtime(harness, summary, raw)._canonical_output_rows(harness.client)
        raw = _raw_native(harness, solver_role={})
        with pytest.raises(FlightRuntimeError, match="kind does not match"):
            _runtime(harness, summary, raw)._canonical_output_rows(harness.client)
        both = _raw_native(harness, solver_role={
            "template_variants": _block(twin=True), "supply_variants": _block(twin=True),
        })
        with pytest.raises(FlightRuntimeError, match="declares both"):
            _runtime(harness, summary, both)._canonical_output_rows(harness.client)
    finally:
        harness.close()


def test_a_supply_group_still_validates_as_before(tmp_path):
    group = _live_group()
    harness = runner_tests._ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=3, planner_actions=(),
    )
    harness.config = _live_config(group=group, max_contacts=3)
    harness.supply_variant_for_phase = _arm_resolver({"wide": (ARM_VALUE,), "plan": ()})
    harness._output = lambda key: (
        f"solver-arm-{key[3]}:{key[0]}" if key[1] == "solver"
        else f"{key[1]}-analysis:{key[0]}:visit:{key[2]}"
    )
    summary = harness.run()
    try:
        block = {
            "arms": [
                {"arm_id": "wide", "max_supplied_items": 4},
                {"arm_id": "plan", "deliver": True, "max_supplied_items": 4},
            ],
        }
        runtime = _runtime(
            harness, summary, _raw_native(harness, solver_role={"supply_variants": block}),
        )
        outputs = runtime._canonical_output_rows(harness.client)
        assert [a["arm_id"] for a in outputs[0]["supply_variants"]["arms"]] == ["wide", "plan"]
        # A supply receipt against a template declaration is refused by kind.
        runtime = _runtime(
            harness, summary,
            _raw_native(harness, solver_role={"template_variants": _block(twin=True)}),
        )
        with pytest.raises(FlightRuntimeError, match="kind does not match"):
            runtime._canonical_output_rows(harness.client)
    finally:
        harness.close()
