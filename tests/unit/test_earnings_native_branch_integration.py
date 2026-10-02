"""Exercise ASR runtime adapters, window branches and sealed terminal custody.

Speech, prepared knowledge, dataset loading and model replies are synthetic.
The real adapter contract, FlightRuntime dispatch, OpenJiuwen graph, acquisition
policy, delivery normaliser and output/trace verification remain in the path.
This is an offline engineering proof, not a carrier flight or quality estimate.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core import preparation_fit
from speech_aware_evidence_acquisition.core.bundle.outputs import (
    _minimum_model_calls_from_trace, _verify_outputs_trace_binding,
)
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails.adapters.earnings import Earnings21Adapter, EarningsSample
from speech_aware_evidence_acquisition.rails.adapters.earnings_runtime import Earnings21RuntimeAdapter
from speech_aware_evidence_acquisition.rails.adapters.earnings22_runtime import Earnings22RuntimeAdapter
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.execution_units import execution_unit_scope
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial

from test_e35_earnings_native_episode_wire import NORMALISERS, PROGRAM_ID, _run, _values
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness, _plan, _wire_response
from test_raw_execution_unit_runner import _feature_windows, _runtime

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = "A margin is a ratio; preserve the spoken percentage without inventing a value."


def _adapter(harness, tmp_path, carrier, values, monkeypatch):
    split = "discovery" if carrier == "earnings21-original" else "dev"
    samples = tuple(EarningsSample(
        sample_id=s.sample_id, audio_ref=s.audio_ref, audio_seconds=s.audio_seconds,
        media_relpath=s.audio_ref.path, carrier_lock_key=carrier,
    ) for s in harness.samples)

    def load_synthetic_split(self, split_id):
        assert self.CARRIER_LOCK_KEY == carrier
        assert split_id == split
        return samples

    def forbidden(*args, **kwargs):
        raise AssertionError("Runtime must not read targets or invoke scoring.")

    monkeypatch.setattr(Earnings21Adapter, "load_split", load_synthetic_split)
    monkeypatch.setattr(Earnings21Adapter, "gold", forbidden)
    monkeypatch.setattr(Earnings21RuntimeAdapter, "score_response", forbidden)
    repo = tmp_path / "adapter-repo"
    path = repo / "configs/dataset/synthetic.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"carrier_lock_key": carrier, "split_name": split}))
    config = {
        **values, "split_name": split, "policy": PROGRAM_ID,
        "arm": "speech-feature-query-native-tools",
        "prepared_execution_units": {"synthetic": True},
        "prepared_window_feature_packets": {"synthetic": True},
        "serving_geometry": {"slots": 2, "slot_tokens": 8192, "max_tokens": 64},
        "decoding_params": {"max_tokens": 64},
        "task_instruction": "Transcribe the current speech window verbatim.",
    }
    cls = Earnings21RuntimeAdapter if split == "discovery" else Earnings22RuntimeAdapter
    adapter = cls(config, {}, harness.world.data_root, repo, dataset_fragment="synthetic")
    adapter.bind_runtime(None, config)
    assert adapter.load_split(split) == samples
    return adapter, split, samples


@pytest.mark.parametrize("carrier", NORMALISERS)
@pytest.mark.parametrize("route", [
    "accept", "revise", "lookup", "empty-lookup", "exhaust", "abstain",
    "blank-revision", "whitespace", "empty-length",
])
def test_native_window_branches_keep_solver_authority_and_complete_custody(
    tmp_path, monkeypatch, carrier, route,
):
    plan = _plan(
        carrier_lock_key=carrier,
        split_identity_hash=split_identity_hash(prefixed(carrier, ["s1"])),
        planned_model_calls=22,
    )
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=1, max_contacts=11,
        planner_actions=("ACCEPT",), arm="speech-feature-query-native-tools",
        execution_plan=plan, execution_units_factory=_feature_windows,
    )
    roster = harness.execution_units
    scope_to_unit = {execution_unit_scope(u.request_key): u.request_key for u in roster.units}
    values = _values(armed=True, carrier=carrier)
    values["native_episode"].update({
        "finite_completion_policy": "deliver-latest-or-abstain",
        "react_exhaustion_policy": "continue-without-answer",
        "exhaustion_policy": "deliver-latest-solver",
    })
    values["native_contact_fit"] = {
        "run_id": "SAEA-SYNTHETIC-ASR-BRANCH-FIT", "attempt_id": "attempt-asr-branch-fit",
        "contact_cap": 22,
    }
    harness.adapter, split, harness.samples = _adapter(harness, tmp_path, carrier, values, monkeypatch)
    program = default_phase_program(PROGRAM_ID)

    def material(phase, context, sealed):
        return PhaseMaterial(
            instruction=f"Complete {phase} for {context.execution_unit_id}.",
            response_format=None, contact_id="material-" + phase, purpose=phase,
        )

    runtime = _runtime(harness, roster, material, values)
    runtime._split_id = split
    runtime._repo_root = REPO_ROOT
    requests, visits, query_scopes = {}, {}, []
    lock = threading.Lock()
    first = threading.Barrier(2)

    def fit(request):
        payload = request.as_payload()
        contact = payload["history"][-1]["contact_id"]
        scope, legacy = contact.split("/", 1)
        unit, phase = scope_to_unit[scope], legacy.split(":")[-3]
        body = harness.transport.render_request(request.payload_bytes)
        with lock:
            visit = visits.get((unit, phase), 0) + 1
            visits[unit, phase] = visit
            requests[json.dumps(body, sort_keys=True)] = (unit, phase, visit, contact, body)

    def post(url, raw):
        unit, phase, visit, _, _ = requests[json.dumps(json.loads(raw), sort_keys=True)]
        if phase == "perception":
            first.wait(timeout=5)
        first_window = unit.endswith("w0001")
        if phase == "planner":
            text = "ACCEPT"
            if first_window and route in {"revise", "exhaust", "lookup", "empty-lookup", "blank-revision"}:
                if visit == 1 or route == "exhaust":
                    text = "ACQUIRE" if "lookup" in route else "REVISE"
        elif phase == "solver":
            empty = first_window and (
                route in {"abstain", "whitespace", "empty-length"}
                or (route == "blank-revision" and visit == 2)
            )
            text = ("   \n" if route == "whitespace" else "") if empty else (
                f"Transcript: {'revised' if visit == 2 else 'initial'}   transcript for {unit}"
            )
        elif phase == "reviewer":
            text = "Check the margin terminology; this review is not the delivered transcript."
        else:
            text = f"Observation for {unit}"
        response = _wire_response(text)
        if first_window and phase == "solver" and route == "empty-length":
            response = json.loads(response)
            response["choices"][0]["finish_reason"] = "length"
            return json.dumps(response).encode()
        return response

    # A synthetic prepared store stands in for carrier-specific admission.
    # The callback returned to the graph is the production binding, including
    # its state restrictions, empty-result handling and acquisition receipts.
    original_binding = runtime._acquisition_requery_binding

    def bind_acquisition(config, supply, snapshot):
        def prepared_supply(phase, context):
            query_scopes.append((phase, context.execution_unit_id))
            return SimpleNamespace(fusion_decision=SimpleNamespace(
                selected_value_ids=("synthetic:margin",) if route == "lookup" else (),
            ))
        return original_binding(config, prepared_supply, SimpleNamespace(values=(SimpleNamespace(
            value_id="synthetic:margin", content=EVIDENCE, associated_facet_ids=("margin",),
        ),)))

    runtime._acquisition_requery_binding = bind_acquisition
    harness.transport._post = post
    fit.receipts = []
    monkeypatch.setattr(preparation_fit, "build_native_contact_fit_gate", lambda *_args: fit)
    try:
        rows, contacts, *_ = runtime._dispatch_phase_program(harness.client, plan, program.program_id)
        runtime._output_rows = rows
        summary = runtime._phase_summaries[0]
        canonical = runtime._canonical_output_rows(harness.client)
        runtime._trace_execution_unit_deliveries(harness.client, canonical)
    finally:
        closed = harness.close()

    assert contacts == closed["request_count"] == len(requests)
    assert len(canonical) == 1
    assert len(summary.results) == 2
    for result in summary.results:
        unit = result.execution_unit_id
        episode = result.native_episode_receipt
        other = next(u.request_key for u in roster.units if u.request_key != unit)
        bodies = [(phase, visit, body) for u, phase, visit, _, body in requests.values() if u == unit]
        assert all(other not in json.dumps(body) for _, _, body in bodies)
        if not (unit.endswith("w0001") and route in {"abstain", "whitespace", "empty-length"}):
            visit = 2 if unit.endswith("w0001") and route in {"revise", "exhaust", "lookup", "empty-lookup"} else 1
            expected = f"{'revised' if visit == 2 else 'initial'} transcript for {unit}"
            assert result.final_response_text == expected
            normaliser = episode["deliver_normaliser"]
            assert normaliser["normaliser_id"] == NORMALISERS[carrier]
            assert normaliser["carrier_lock_key"] == carrier
            receipt_key = "terminal_solver_receipt" if unit.endswith("w0001") and route in {"exhaust", "blank-revision"} else "accepted_solver_receipt"
            assert ":solver:" in episode[receipt_key]["final_contact"]["agent_contact_id"]
        else:
            assert result.final_response_text == ""
        acquired = episode["acquisition"]["acquisitions"]
        if unit.endswith("w0001") and "lookup" in route:
            assert len(acquired) == 1
            second = next(body for phase, visit, body in bodies if phase == "solver" and visit == 2)
            assert (EVIDENCE in json.dumps(second)) == (route == "lookup")
        else:
            assert acquired == []
        assert episode["acquisition"]["contacts_used"] == 0
    assert query_scopes == ([("solver", "s1#w0001")] if "lookup" in route else [])
    assert "review is not" not in canonical[0]["text"]
    if route in {"abstain", "whitespace", "empty-length"}:
        assert canonical[0]["text"] == "initial transcript for s1#w0002"
    records = [json.loads(line) for line in (
        harness.world.run_dir / f"{plan.run_id}.trace.jsonl"
    ).read_text().splitlines()]
    payloads = {row["record_id"]: row["payload"] for row in records}
    assert len(payloads) == len(records)
    _verify_outputs_trace_binding(tuple(canonical), payloads)
    assert _minimum_model_calls_from_trace(payloads) == contacts


@pytest.mark.parametrize("carrier", NORMALISERS)
def test_strict_completion_policy_still_refuses_an_empty_solver(tmp_path, carrier):
    from speech_aware_evidence_acquisition.reproduction.ojw.native_episode import NativeEpisodeError

    harness = _run(tmp_path, sample_count=1, armed=True, carrier=carrier)
    original_output = harness._output
    harness._output = lambda key: "" if key[1] == "solver" else original_output(key)
    try:
        with pytest.raises(NativeEpisodeError, match="Solver completion contains no answer text"):
            harness.run()
    finally:
        closed = harness.close()
    assert closed["request_count"] == 2
