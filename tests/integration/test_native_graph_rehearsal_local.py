"""Opt-in repository-data rehearsal; fail, never skip, once explicitly enabled."""
import json
import os
from pathlib import Path
from unittest.mock import patch
import pytest
from speech_aware_evidence_acquisition.analysis.native_graph_rehearsal import FourPathResponder, rehearse_native_graph
from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime

@pytest.mark.skipif(not os.environ.get("SAEA_NATIVE_REHEARSAL_OUTPUT"), reason="Requires released local DATA and a live render-only session")
def test_current_four_paths_use_the_real_native_graph_without_network():
    repo = Path(__file__).resolve().parents[2]
    data = Path(os.environ["SAEA_NATIVE_REHEARSAL_DATA"])
    output = Path(os.environ["SAEA_NATIVE_REHEARSAL_OUTPUT"])
    experiment = "slurp-native-stage3-system-text-smoke-4-recovery1-v1"
    cell = json.loads((repo / "configs/experiment" / (experiment + ".json")).read_text())["cells"][0]
    runtime = build_flight_runtime(repo, data, model=cell["model_fragment"], dataset=cell["dataset_fragment"],
        baseline=cell["baseline_fragment"], experiment=experiment, run_id=cell["run_id"],
        attempt_id=cell["attempt_id"], runtime_root=Path("/home/chao"),
        lock_path=Path(os.environ["SAEA_NATIVE_REHEARSAL_LOCK"]), campaign_active=False)
    roster = runtime.preparation_context()["sample_ids"]
    responder = FourPathResponder(roster, ["media_type", "device_type"])
    def no_network(*_args, **_kwargs):
        raise AssertionError("No network is allowed in this proof")
    with patch("socket.socket.connect", no_network), patch("socket.socket.connect_ex", no_network):
        receipt = rehearse_native_graph(runtime, session_path=Path(os.environ["SAEA_NATIVE_REHEARSAL_SESSION"]),
                                        respond=responder, output=output)
    assert receipt["terminal_rows"] == 4
    assert receipt["synthetic_completions"] == 22
    assert receipt["synthetic_tool_calls"] == 3
    assert receipt["generation_contacts"] == receipt["tokenizer_contacts"] == receipt["official_score_jobs"] == 0
    assert receipt["capacity_verified"] is False
    counts = {r["sample_id"]: r["contacts"] for r in receipt["dispatch"]["contacts_per_sample_observed"]}
    assert [counts[s] for s in roster] == [4, 5, 5, 8]
    paths = {r["sample_id"]: r for r in receipt["terminal_paths"]}
    for sample in roster:
        assert paths[sample]["accepted_solver_receipt"]
        assert paths[sample]["terminal_disposition"] is None
    assert paths[roster[-1]]["role_visits"] == ["perception", "solver", "reviewer", "planner", "solver", "reviewer", "planner"]
    assert [r["action"] for r in paths[roster[-1]]["planner_routes"]] == ["REVISE", "ACCEPT"]
    records = [json.loads(line) for line in (output / "requests.jsonl").read_text().splitlines()]
    responses = {}
    for row in records:
        for message in row["request"]["messages"]:
            if message.get("role") == "tool":
                responses.setdefault(row["sample_id"], []).append(json.loads(message["content"]))
    assert roster[0] not in responses
    assert responses[roster[1]][0]["result"]["supply_disposition"] == "no-mapping"
    assert responses[roster[1]][0]["evidence"] == []
    for sample in roster[2:]:
        assert responses[sample][0]["result"]["supply_disposition"] == "acquired"
        assert len(responses[sample][0]["evidence"]) == 2
    # Exact tool messages persist to the revised Solver and remaining graph.
    revised = next(r for r in records if r["sample_id"] == roster[-1]
                   and any(":solver:1:" in h.get("contact_id", "") for h in r["payload"]["history"]))
    assert any(m.get("role") == "tool" for m in revised["request"]["messages"])

@pytest.mark.skipif(not os.environ.get("SAEA_NATIVE_REHEARSAL_OUTPUT"), reason="Requires explicitly enabled local render-only proof")
@pytest.mark.parametrize("case", ["malformed-control", "rejected-tool"])
def test_current_negative_control_paths_terminate_without_external_actions(case):
    repo = Path(__file__).resolve().parents[2]
    data = Path(os.environ["SAEA_NATIVE_REHEARSAL_DATA"])
    output = Path(os.environ["SAEA_NATIVE_REHEARSAL_OUTPUT"] + "-" + case)
    experiment = "slurp-native-stage3-system-text-smoke-4-recovery1-v1"
    cell = json.loads((repo / "configs/experiment" / (experiment + ".json")).read_text())["cells"][0]
    runtime = build_flight_runtime(repo, data, model=cell["model_fragment"], dataset=cell["dataset_fragment"],
        baseline=cell["baseline_fragment"], experiment=experiment, run_id=cell["run_id"],
        attempt_id=cell["attempt_id"], runtime_root=Path("/home/chao"),
        lock_path=Path(os.environ["SAEA_NATIVE_REHEARSAL_LOCK"]), campaign_active=False)
    roster = runtime.preparation_context()["sample_ids"]
    normal = FourPathResponder(roster, ["media_type", "device_type"])
    seen = set()
    def respond(payload):
        control = [x for x in payload["history"] if x.get("role") == "control"][-1]
        if ":planner:" not in control["contact_id"]:
            return normal(payload)
        if case == "malformed-control":
            return {"role": "assistant", "content": 'UNREGISTERED_ACTION'}
        if payload["sample_id"] not in seen:
            seen.add(payload["sample_id"])
            return {"role": "assistant", "content": None, "tool_calls": [{
                "id": "synthetic-rejected-lookup", "type": "function",
                "function": {"name": "saea-tool-knowledge-target-lookup-v1",
                    "arguments": json.dumps({"store_id": "slot-contracts", "view": "text",
                        "candidate_ids": ["media_type", "device_type", "food_type"],
                        "distinction": "Deliberately over-limit synthetic request."})}}]}
        return {"role": "assistant", "content": "ACCEPT"}
    with patch("socket.socket.connect", side_effect=AssertionError("No network")), patch("socket.socket.connect_ex", side_effect=AssertionError("No network")):
        receipt = rehearse_native_graph(runtime, session_path=Path(os.environ["SAEA_NATIVE_REHEARSAL_SESSION"]),
                                        respond=respond, output=output)
    assert receipt["terminal_rows"] == 4
    assert receipt["synthetic_tool_calls"] == 0
    assert receipt["generation_contacts"] == receipt["tokenizer_contacts"] == 0
    if case == "malformed-control":
        assert all(r["planner_routes"][-1]["disposition"] == "planner_action_illegal"
                   and r["accepted_solver_receipt"] for r in receipt["terminal_paths"])
    else:
        assert receipt["dispatch"]["phase_tools"]["native_rejected_requests"]["count"] == 4


