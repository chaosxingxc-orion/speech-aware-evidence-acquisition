"""Prospective continuation envelopes refuse oversized custody without truncation."""
import copy
import json
import pytest

from speech_aware_evidence_acquisition.rails.system_proposer_continuation import LIMITS, checked_output, checked_tool, require_limits
from speech_aware_evidence_acquisition.rails.system_proposer_responses import ResponsesHTTP, ResponsesProposer
from speech_aware_evidence_acquisition.rails.system_proposer_capacity import audit_scenario, request_bound
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError, canonical
from test_system_proposer_capacity import setup
from test_system_proposer_responses import completed, reply, server


@pytest.mark.parametrize("bad", [{}, {**LIMITS, "unknown": 1}, {**LIMITS, "provider_output_items_bytes": True},
    {**LIMITS, "tool_result_bytes": 4097}])
def test_invalid_envelopes_fail_closed(bad):
    with pytest.raises(PolicyError): require_limits(bad)


def test_exact_byte_bounds_and_legacy_are_distinct():
    output = [{"text": "x" * (4096 - len(canonical([{"text": ""}]).encode()))}]
    checked_output(output, LIMITS)
    output[0]["text"] += "x"
    with pytest.raises(PolicyError, match="provider continuation"):
        checked_output(output, LIMITS)
    checked_output(output, None)
    with pytest.raises(PolicyError, match="artifact continuation"):
        checked_tool({"text": "x" * 4096}, "call", LIMITS)


@pytest.mark.parametrize("oversized", ["provider", "tool"])
def test_charged_oversized_turn_is_preserved_and_next_contact_is_not_sent(tmp_path, oversized, monkeypatch):
    capsule, scenario = setup(tmp_path, cap=131072, subscription=True)
    output = scenario["turns"][0]["output"]
    if oversized == "provider": output[0]["encrypted_content"] = "x" * 4096
    else: monkeypatch.setattr(capsule, "read_artifact", lambda _: {"text": "y" * 4096})
    with server([reply(completed(output))]) as (endpoint, requests):
        transport = ResponsesProposer(capsule, ResponsesHTTP(endpoint, fixture_only=True),
            audit_dir=tmp_path / "audit", input_counter=request_bound,
            before_contact=lambda _: None, contact_cap=4, continuation_limits=LIMITS)
        with pytest.raises(PolicyError, match="continuation"):
            transport(capsule.request())
        assert len(requests) == 1
    outcome = json.loads((tmp_path / "audit/outcome.json").read_text())
    assert outcome["attempted_contacts"] == 1 and outcome["usage_complete"]
    assert outcome["observed_input_tokens"] == 100 and outcome["observed_output_tokens"] == 10
    assert not (tmp_path / "audit/contact-002").exists()
    assert (tmp_path / "audit/contact-001/response.sse").exists()


def test_two_pages_then_final_shares_exact_transport_and_offline_bounds(tmp_path):
    capsule, scenario = setup(tmp_path, cap=131072, subscription=True)
    second = copy.deepcopy(scenario["turns"][0]); second["output"][1]["call_id"] = "second"
    scenario["turns"].append(second)
    scenario["continuation_limits"] = LIMITS
    report = audit_scenario(capsule.as_json(), scenario)
    with server([reply(completed(t["output"])) for t in scenario["turns"]] + [reply(completed())]) as (endpoint, requests):
        transport = ResponsesProposer(capsule, ResponsesHTTP(endpoint, fixture_only=True),
            audit_dir=tmp_path / "audit", input_counter=request_bound,
            before_contact=lambda _: None, contact_cap=4, continuation_limits=LIMITS)
        result = transport(capsule.request())
    assert result["input_tokens"] == 300
    assert len(requests) == report["covered_requests"] == 3
    from speech_aware_evidence_acquisition.rails.hashing import content_hash
    assert [content_hash(r["body"]) for r in requests] == [r["request_sha256"] for r in report["requests"]]
    scenario["turns"][0]["output"][0]["encrypted_content"] = "z" * 4096
    with pytest.raises(PolicyError, match="provider continuation"):
        audit_scenario(capsule.as_json(), scenario)


def test_prospective_fourth_tool_call_exhausts_contact_cap_without_fifth_request(tmp_path):
    capsule, scenario = setup(tmp_path, cap=131072, subscription=True)
    outputs = []
    for i in range(4):
        output = copy.deepcopy(scenario["turns"][0]["output"]); output[1]["call_id"] = str(i)
        outputs.append(output)
    with server([reply(completed(o)) for o in outputs]) as (endpoint, requests):
        transport = ResponsesProposer(capsule, ResponsesHTTP(endpoint, fixture_only=True),
            audit_dir=tmp_path / "audit", input_counter=request_bound,
            before_contact=lambda _: None, contact_cap=4, continuation_limits=LIMITS)
        with pytest.raises(PolicyError, match="contact budget"):
            transport(capsule.request())
        assert len(requests) == 4


def test_envelope_rehearsal_charges_full_byte_bounds_for_three_maximum_turns(tmp_path):
    from speech_aware_evidence_acquisition.rails.system_proposer_continuation import audit_envelope
    capsule, _ = setup(tmp_path, cap=131072, subscription=True)
    report = audit_envelope(capsule.as_json())
    assert report["actual_contacts"] == 0 and report["status"] == "covered_envelope_fits"
    assert len(report["requests"]) == 4
    assert report["cumulative_request_bounds"] == sum(row["input_token_bound"] for row in report["requests"])
    assert report["continuation_item_sizes"] == [4096, 4096]
    assert report["final_output_reserve"] == 1096
    (tmp_path / "small").mkdir()
    small, _ = setup(tmp_path / "small", cap=32768, subscription=True)
    assert audit_envelope(small.as_json())["status"] == "input_budget_exceeded"
