"""Continuation scenarios share the production request/broker without contacts."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_proposer_capsule import ProposerCapsule
from speech_aware_evidence_acquisition.rails.system_proposer_capacity import audit_scenario, request_bound
from speech_aware_evidence_acquisition.rails.system_proposer_responses import ResponsesHTTP, ResponsesProposer
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from test_system_proposer_capsule import fixture, reseal
from test_system_proposer_responses import completed, reply, server
from test_system_proposer_views import learning_fixture


def setup(tmp_path, *, learning=False, cap=32768, profile="compact-feedback-v1", subscription=False):
    packet, roots = learning_fixture(tmp_path) if learning else fixture(tmp_path)
    packet["input_token_cap"] = cap
    if subscription:
        packet["budget_profile"] = "subscription-metered-reject-v1"
    reseal(packet)
    capsule = ProposerCapsule.from_packet(packet, roots=roots, view_profile=profile)
    artifact = next(a for a in capsule.as_json()["artifacts"] if a["kind"] == "knowledge-snapshot")
    output = [{"type": "reasoning", "id": "reasoning-fixture", "encrypted_content": "opaque-custody"},
              {"type": "function_call", "call_id": "call-fixture", "name": "read_artifact",
               "arguments": json.dumps({"artifact_id": artifact["artifact_id"], "offset": 0, "limit": 2048})}]
    scenario = {"schema": "saea-proposer-capacity-scenario-v1", "contact_cap": 4,
                "turns": [{"output": output, "assumed_input_tokens": 100, "assumed_output_tokens": 10}]}
    return capsule, scenario


@pytest.mark.parametrize("learning", [False, True])
@pytest.mark.parametrize("profile", ["compact-feedback-v1", "full-index-v1"])
def test_scenario_requests_equal_actual_transport_requests(tmp_path, learning, profile):
    capsule, scenario = setup(tmp_path, learning=learning, profile=profile)
    original = copy.deepcopy(capsule.as_json())
    report = audit_scenario(original, scenario)
    assert capsule.as_json() == original and capsule.access_log == []
    assert report["status"] == "covered_requests_fit"
    assert report["actual_contacts"] == 0 and report["dispatch_authority"] is False
    assert report["usage_kind"] == "assumed_not_measured"
    assert report["capsule_sha256"] == content_hash(original)
    assert report["scenario_sha256"] == content_hash(scenario)
    assert report["covered_requests"] == 2 and report["unassessed_turns"] == 0
    with server([reply(completed(scenario["turns"][0]["output"])), reply(completed())]) as (endpoint, requests):
        transport = ResponsesProposer(capsule, ResponsesHTTP(endpoint, fixture_only=True),
            audit_dir=tmp_path / "transport", input_counter=request_bound,
            before_contact=lambda _: None, contact_cap=4)
        transport(capsule.request())
    for actual, step in zip(requests, report["requests"], strict=True):
        assert content_hash(actual["body"]) == step["request_sha256"]
        assert request_bound(actual["body"]) == step["input_token_bound"]
    assert report["artifact_reads"][0]["characters"] > 0
    assert "Frozen English knowledge" not in json.dumps(report)


def test_initial_request_can_fit_while_continuation_cannot(tmp_path):
    capsule, scenario = setup(tmp_path, cap=19000)
    # Reasoning custody is repeated just like tool data; it is never discarded.
    scenario["turns"][0]["output"][0]["encrypted_content"] = "x" * 20000
    report = audit_scenario(capsule.as_json(), scenario)
    assert report["requests"][0]["fits"] is True
    assert report["status"] == "input_budget_exceeded"
    assert report["first_failed_contact"] == 2
    assert report["requests"][1]["input_token_bound"] > report["requests"][1]["remaining_input_tokens"]


def test_three_subscription_requests_preserve_reasoning_and_both_tool_turns(tmp_path):
    capsule, scenario = setup(tmp_path, subscription=True)
    second = copy.deepcopy(scenario["turns"][0])
    second["output"][1]["call_id"] = "second-call"
    second["output"][1]["namespace"] = "artifacts"
    second.update(assumed_input_tokens=222, assumed_output_tokens=33)
    scenario["turns"].append(second)
    report = audit_scenario(capsule.as_json(), scenario)
    with server([reply(completed(scenario["turns"][0]["output"])),
                 reply(completed(second["output"], usage={"input_tokens": 222, "output_tokens": 33})),
                 reply(completed())]) as (endpoint, requests):
        transport = ResponsesProposer(capsule, ResponsesHTTP(endpoint, fixture_only=True),
            audit_dir=tmp_path / "subscription", input_counter=request_bound,
            before_contact=lambda _: None, contact_cap=4)
        transport(capsule.request())
    assert [content_hash(r["body"]) for r in requests] == [r["request_sha256"] for r in report["requests"]]
    assert all("max_output_tokens" not in r["body"] for r in requests)
    assert report["assumed_usage"] == {"input_tokens": 322, "output_tokens": 43}
    assert report["requests"][2]["remaining_input_tokens"] == 32768 - 322


def test_initial_failure_does_not_read_artifact(tmp_path, monkeypatch):
    capsule, scenario = setup(tmp_path, cap=100)
    monkeypatch.setattr(ProposerCapsule, "read_artifact", lambda *_: pytest.fail("unexpected artifact read"))
    report = audit_scenario(capsule.as_json(), scenario)
    assert report["first_failed_contact"] == 1 and report["unassessed_turns"] == 1
    assert report["artifact_reads"] == []


def test_empty_scenario_only_checks_initial_request(tmp_path):
    capsule, scenario = setup(tmp_path)
    scenario["turns"] = []
    report = audit_scenario(capsule.as_json(), scenario)
    assert report["covered_requests"] == 1 and report["assumed_usage"] == {"input_tokens": 0, "output_tokens": 0}


@pytest.mark.parametrize("usage", [4096, 4097])
def test_exhausted_or_excessive_assumed_output_is_not_a_pass(tmp_path, usage):
    capsule, scenario = setup(tmp_path)
    scenario["turns"][0]["assumed_output_tokens"] = usage
    report = audit_scenario(capsule.as_json(), scenario)
    assert report["status"] == ("output_budget_exhausted" if usage == 4096 else "assumed_output_exceeds_allowance")


@pytest.mark.parametrize("mutation", ["extra", "wrong-schema", "bool-cap", "too-many-turns", "bad-turn",
                                      "negative", "bool-usage", "unknown-tool", "duplicate-call", "parallel",
                                      "foreign-artifact", "bad-page", "duplicate-json", "input-over-bound",
                                      "proposal-instead-of-read"])
def test_invalid_scenarios_fail_closed(tmp_path, mutation):
    capsule, scenario = setup(tmp_path)
    turn = scenario["turns"][0]
    call = turn["output"][1]
    if mutation == "extra":
        scenario["hidden_context"] = "not admitted"
    elif mutation == "wrong-schema":
        scenario["schema"] = "other"
    elif mutation == "bool-cap":
        scenario["contact_cap"] = True
    elif mutation == "too-many-turns":
        scenario["turns"] *= 4
    elif mutation == "bad-turn":
        turn["feedback"] = {}
    elif mutation == "negative":
        turn["assumed_input_tokens"] = -1
    elif mutation == "bool-usage":
        turn["assumed_output_tokens"] = True
    elif mutation == "unknown-tool":
        call["name"] = "read_any_file"
    elif mutation == "duplicate-call":
        scenario["turns"] *= 2
    elif mutation == "parallel":
        turn["output"].append({**call, "call_id": "another"})
    elif mutation == "foreign-artifact":
        args = json.loads(call["arguments"])
        args["artifact_id"] = "learning-branch-private-source"
        call["arguments"] = json.dumps(args)
    elif mutation == "bad-page":
        args = json.loads(call["arguments"])
        args["limit"] = 2049
        call["arguments"] = json.dumps(args)
    elif mutation == "duplicate-json":
        call["arguments"] = '{"artifact_id":"a","artifact_id":"b"}'
    elif mutation == "input-over-bound":
        turn["assumed_input_tokens"] = 32000
    else:
        turn["output"] = completed()["response"]["output"]
    with pytest.raises(PolicyError):
        audit_scenario(capsule.as_json(), scenario)


def load_script(name, relpath):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[2] / relpath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bound_is_identical_to_registered_round_launcher(tmp_path):
    capsule, _ = setup(tmp_path)
    launcher = load_script("capacity_round_fixture", "scripts/flights/system_text_proposer_round.py")
    assert request_bound(capsule.request()) == launcher.request_bound(capsule.request())


@pytest.mark.parametrize("cap", [32768, 100])
def test_pinned_cli_writes_new_report_and_refuses_changed_input_or_overwrite(tmp_path, cap):
    capsule, scenario = setup(tmp_path, cap=cap)
    script = load_script("capacity_check_fixture", "scripts/checks/system_text_proposer_capacity_check.py")
    args = []
    for name, value in (("capsule", capsule.as_json()), ("scenario", scenario)):
        path = tmp_path / (name + ".json")
        path.write_text(json.dumps(value))
        args.extend(["--" + name, str(path), "--" + name + "-sha256", hashlib.sha256(path.read_bytes()).hexdigest()])
    destination = tmp_path / "report.json"
    args.extend(["--report", str(destination)])
    wrong = list(args)
    wrong[3] = "0" * 64
    with pytest.raises(PolicyError, match="hash differs"):
        script.main(wrong)
    assert not destination.exists()
    assert script.main(args) == (0 if cap == 32768 else 2)
    saved = destination.read_bytes()
    report = json.loads(saved)
    assert report["input_files"]["scenario"]["sha256"] == args[7]
    with pytest.raises(PolicyError, match="already exists"):
        script.main(args)
    assert destination.read_bytes() == saved
    args[-1] = str(tmp_path / "subprocess-report.json")
    result = subprocess.run([sys.executable, "-B", script.__file__, *args], capture_output=True, text=True)
    assert result.returncode == (0 if cap == 32768 else 2), result.stderr
    assert json.loads(result.stdout)["actual_contacts"] == 0
