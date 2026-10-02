"""Owner217 acceptance budgets, one-shot rejection and branch parity."""
import json
import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_proposer_capsule import ProposerCapsule, ProposalDispatch
from speech_aware_evidence_acquisition.rails.system_proposer_responses import ResponsesHTTP, ResponsesProposer
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from test_system_proposer_capsule import fixture
from test_system_proposer_responses import server, reply, completed, call, live_admission

PROFILE = "subscription-metered-reject-v1"


def setup(tmp_path, endpoint, branch="B"):
    packet, roots = fixture(tmp_path, branch)
    packet["budget_profile"] = PROFILE
    packet["input_sha256"] = content_hash({k: v for k, v in packet.items() if k != "input_sha256"})
    capsule = ProposerCapsule.from_packet(packet, roots=roots)
    transport = ResponsesProposer(capsule, ResponsesHTTP(endpoint, fixture_only=True),
        audit_dir=tmp_path / "transport", input_counter=lambda request: 100,
        before_contact=lambda receipt: None, contact_cap=2)
    return capsule, transport


@pytest.mark.parametrize("branch", ["L", "B"])
def test_subscription_preserves_isolation_and_omits_unsupported_limit(tmp_path, branch):
    with server([reply(completed())]) as (endpoint, requests):
        capsule, transport = setup(tmp_path, endpoint, branch)
        receipt = ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)
    assert receipt["output_tokens"] == 10
    wire = requests[0]["body"]
    assert "max_output_tokens" not in wire
    assert wire["tools"][0]["type"] == "namespace"
    assert wire["tools"][0]["name"] == "artifacts"
    assert len(wire["tools"][0]["tools"]) == 1
    assert "4096" in wire["instructions"]
    assert wire["stream"] and wire["store"] is False
    assert len(wire["input"]) == 1


@pytest.mark.parametrize("usage", [None, {"input_tokens": 100, "output_tokens": 4097}])
def test_subscription_rejected_output_consumes_slot_and_preserves_usage(tmp_path, usage):
    with server([reply(completed(usage=usage))]) as (endpoint, requests):
        capsule, transport = setup(tmp_path, endpoint)
        dispatch = ProposalDispatch(tmp_path / "dispatch", capsule)
        with pytest.raises(PolicyError):
            dispatch.run(transport)
        with pytest.raises(PolicyError, match="consumed"):
            dispatch.run(transport)
    assert len(requests) == 1
    outcome = json.loads((tmp_path / "transport/outcome.json").read_text())
    assert not outcome["retry_permitted"]
    if usage:
        assert outcome["observed_output_tokens"] == 4097 and outcome["usage_complete"]
    else:
        assert outcome["unmetered_contacts"] == 1


def test_subscription_tool_history_counts_toward_same_budget(tmp_path):
    capsule, transport = setup(tmp_path, "http://127.0.0.1:1/v1/responses")
    identity = capsule.initial_input()["artifacts"][0]["artifact_id"]
    tool = call(identity, namespace="artifacts")
    with server([reply(completed([tool])), reply(completed())]) as (endpoint, requests):
        transport.client = ResponsesHTTP(endpoint, fixture_only=True)
        receipt = ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)
    assert receipt["input_tokens"] == 200 and receipt["output_tokens"] == 20
    assert all("max_output_tokens" not in r["body"] for r in requests)
    assert "4086" in requests[1]["body"]["instructions"]


def test_profile_cannot_drift_between_branches(tmp_path):
    first = tmp_path / "first"; first.mkdir()
    second = tmp_path / "second"; second.mkdir()
    with server([reply(completed())]) as (endpoint, requests):
        capsule, transport = setup(first, endpoint)
        ProposalDispatch(tmp_path / "dispatch", capsule).run(transport)
        packet, roots = fixture(second, "L")
        packet["session_id"] = "new-isolated-session"
        packet["input_sha256"] = content_hash({k: v for k, v in packet.items() if k != "input_sha256"})
        other = ProposerCapsule.from_packet(packet, roots=roots)
        with pytest.raises(PolicyError, match="budget"):
            ProposalDispatch(tmp_path / "dispatch", other).run(lambda _: pytest.fail("must not contact"))
    assert len(requests) == 1


def test_subscription_admission_requires_owner217_and_exact_profile():
    value = live_admission()
    value.update(provider_profile="chatgpt-plan-preview", output_cap_enforcement="metered-reject-after-completion",
                 budget_profile=PROFILE, owner_decision=217)
    value["sha256"] = content_hash({k: v for k, v in value.items() if k != "sha256"})
    ResponsesHTTP(value["endpoint"], admission=value, bearer=lambda: "unused")
    value["owner_decision"] = 215
    value["sha256"] = content_hash({k: v for k, v in value.items() if k != "sha256"})
    with pytest.raises(PolicyError, match="incompatible"):
        ResponsesHTTP(value["endpoint"], admission=value, bearer=lambda: "unused")
