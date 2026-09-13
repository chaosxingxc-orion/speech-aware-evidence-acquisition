"""Actual FlightRuntime phase dispatch reaches the shared native graph."""

import copy
import hashlib
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight import runtime as flight_module
from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
)
from speech_aware_evidence_acquisition.core import preparation_fit
from speech_aware_evidence_acquisition.core.base import JudgeVerdict
from speech_aware_evidence_acquisition.core import judges as core_judges
from speech_aware_evidence_acquisition.rails.phase_review import (
    PhaseReviewSpec,
    build_review_for_phase,
)
from speech_aware_evidence_acquisition.rails.phase_runner import run_continuous_program

from test_native_episode_runner import _ActualEpisodeHarness
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_rails_runner import _knowledge_snapshot


@pytest.mark.parametrize("max_revisions", (0, 1))
def test_flight_config_dispatches_actual_roles_and_preserves_solver_custody(
    tmp_path,
    monkeypatch,
    max_revisions,
):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=2,
        max_revisions=max_revisions,
        max_contacts=4 + 3 * max_revisions,
        planner_actions=(("ACCEPT",) if max_revisions == 0 else ("REVISE", "ACCEPT")),
        arm="speech-feature-query",
    )
    values = {
        "native_episode": {
            "schema": "saea-native-episode-config-v1",
            "episode_id": harness.config.episode_id,
            "max_revisions": max_revisions,
            "actions": dict(
                zip(("accept", "revise", "acquire"), harness.config.actions)
            ),
            "roles": {
                role.role_kind: {
                    "phase_id": role.phase_id,
                    "max_iterations": role.max_iterations,
                }
                for role in harness.config.roles
            },
        },
        "native_contact_fit": {
            "run_id": "SAEA-NATIVE-DISPATCH-FIT",
            "attempt_id": "attempt-native-dispatch-fit",
            "contact_cap": 8 * harness.config.max_contacts,
        },
    }
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values=values)
    runtime._model = runtime._dataset = runtime._baseline = {}
    runtime._adapter = harness.adapter
    runtime._data_root = harness.world.data_root
    runtime._split_id = "all"
    runtime._transport = harness.transport
    runtime._arm = lambda: harness.client.arm
    runtime._plan = harness.plan
    judge_id = core_judges.EARNINGS_NUMERIC_FORMAT_JUDGE_V1
    review = build_review_for_phase(
        {
            role.phase_id: PhaseReviewSpec(phase=role.phase_id, judges=(judge_id,))
            for role in harness.config.roles
        },
        judges={
            judge_id: lambda draft, material, state: JudgeVerdict(
                judge_id, "v1", score=0.5
            ),
        },
    )
    runtime._phase_program_material = {
        "knowledge_snapshot": _knowledge_snapshot(),
        "speech_packet_bindings": harness.speech_bindings,
        "material_for_phase": harness.material_for_phase,
        "trace_sink": harness.trace,
        "review_for_phase": review,
    }
    runtime._continuous_phase_runner = run_continuous_program
    runtime._phase_planner_specs = lambda _policy: {}
    runtime._phase_decoding_params = lambda: {"temperature": 0, "max_tokens": 64}
    runtime._fit_base_plan = lambda plan: plan
    runtime._build_phase_tool_dispatcher = lambda *args, **kwargs: None

    def capacity_identity_only(request):
        harness.request_gate(request)
        capacity_identity_only.receipts.append({"capacity_verified": False})

    capacity_identity_only.receipts = []
    factories = []

    def fit_factory(actual_runtime, actual_program, actual_plan):
        factories.append((actual_runtime, actual_program, actual_plan))
        return capacity_identity_only

    monkeypatch.setattr(
        flight_module, "default_phase_program", lambda _policy: harness.program
    )
    monkeypatch.setattr(preparation_fit, "build_native_contact_fit_gate", fit_factory)
    try:
        rows, contacts, kind, dispatch, _phases = runtime._dispatch_phase_program(
            harness.client,
            harness.plan,
            harness.program.program_id,
        )
    finally:
        closed = harness.close()

    assert factories == [(runtime, harness.program, harness.plan)]
    assert contacts == closed["request_count"] == 2 * harness.config.max_contacts
    assert kind == "phase-program"
    assert dispatch["dispatch"] == "phase-program-continuous"
    assert dispatch["contacts_per_sample_ceiling"] == harness.config.max_contacts
    assert dispatch["native_episode"]["episode_id"] == harness.config.episode_id
    assert len(dispatch["native_contact_fit_receipts"]) == contacts
    assert [row["final_response_text"] for row in rows] == [
        f"solver-answer:s1:visit:{max_revisions + 1}",
        f"solver-answer:s2:visit:{max_revisions + 1}",
    ]
    for row in rows:
        receipt = row["native_episode_receipt"]
        accepted = receipt["accepted_solver_receipt"]["final_contact"]
        assert ":solver:" in accepted["agent_contact_id"]
        assert receipt["planner_routes"][-1]["action"] == "ACCEPT"

    assert harness.trace.records == []  # FlightRuntime flushed its one-shot buffer.
    trace_rows = [
        json.loads(line)
        for line in (harness.world.run_dir / f"{harness.plan.run_id}.trace.jsonl")
        .read_text()
        .splitlines()
    ]
    judgments = [
        row["payload"]
        for row in trace_rows
        if row["channel"] == "USE" and "use_phase_judgments" in row["payload"]
    ]
    assert len(judgments) == contacts
    assert len({row["use_source_request_id"] for row in judgments}) == contacts

    runtime._output_rows = rows
    canonical = runtime._canonical_output_rows(harness.client)
    for row in canonical:
        assert row["text"].startswith("solver-answer:")
        assert (
            hashlib.sha256(row["text"].encode()).hexdigest()
            == row["response_text_sha256"]
        )
        accepted = row["native_episode_receipt"]["accepted_solver_receipt"][
            "final_contact"
        ]
        assert row["request_id"] == accepted["request_id"]
        latest = [t for t in harness.client.timings if t.sample_id == row["sample_id"]][
            -1
        ]
        assert (
            row["request_id"] != latest.request_id
        )  # Planner cannot become the source.

    altered = copy.deepcopy(rows)
    altered[0]["native_episode_receipt"]["accepted_solver_receipt"]["final_contact"][
        "response_sha256"
    ] = "0" * 64
    runtime._output_rows = altered
    with pytest.raises(FlightRuntimeError, match="accepted runtime result"):
        runtime._canonical_output_rows(harness.client)
