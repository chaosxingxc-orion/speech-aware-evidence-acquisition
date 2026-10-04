"""Prospective typed contract agrees with the existing immutable validator."""
import copy
import pytest
from test_system_proposer_capsule import fixture
from speech_aware_evidence_acquisition.rails.system_proposer_capsule import ProposerCapsule
from speech_aware_evidence_acquisition.rails.system_text_policy import TextPolicyUpdateProposal, PolicyError


def test_typed_contract_documents_hypothesis_elements_and_valid_examples(tmp_path):
    packet, roots = fixture(tmp_path)
    contract = TextPolicyUpdateProposal.response_contract(packet)
    assert set(contract["field_types"]) == set(contract["example"])
    assert contract["field_types"]["hypotheses"].startswith("array<EnglishText>")
    assert "32768" in contract["types"]["EnglishText"]
    assert contract["types"]["JSON"] == "object|array|string|number|boolean|null"
    hypothesis = copy.deepcopy(contract["example"])
    hypothesis["hypotheses"] = ["A clearer instruction may help; this remains untested."]
    for example in (contract["example"], hypothesis):
        TextPolicyUpdateProposal.from_json(example)
    for bad in ({"statement": "An English hypothesis."}, [], " ", 3, None):
        value = copy.deepcopy(hypothesis)
        value["hypotheses"] = [bad]
        with pytest.raises(PolicyError):
            TextPolicyUpdateProposal.from_json(value)


def test_contract_is_prospective_and_legacy_capsule_roundtrip_is_identical(tmp_path):
    packet, roots = fixture(tmp_path)
    old = ProposerCapsule.from_packet(packet, roots=roots, view_profile="coherent-feedback-v1")
    original = old.request()
    assert "field_types" not in old.initial_input()["response_contract"]
    typed = ProposerCapsule.from_packet(packet, roots=roots, view_profile="typed-coherent-feedback-v1")
    assert typed.as_json()["view_profile"] == "typed-coherent-feedback-v1"
    assert typed.initial_input()["response_contract"]["field_types"]["hypotheses"].startswith("array<EnglishText>")
    assert old.request() == original == ProposerCapsule.from_json(old.as_json()).request()
    assert typed.as_json()["artifacts"] == old.as_json()["artifacts"]
    assert typed.request() != old.request()


def test_field_contract_returns_fresh_values_and_respects_scope(tmp_path):
    packet, _ = fixture(tmp_path)
    packet["optimization_scope"] = {"purpose": "reused-optimization-panel",
        "editable": ["role_text"], "plan_sha256": "a" * 64}
    a = TextPolicyUpdateProposal.response_contract(packet)
    assert set(a["editable_changes"]) == {"role_text"}
    a["field_types"]["hypotheses"] = "array<object>"
    assert TextPolicyUpdateProposal.response_contract(packet)["field_types"]["hypotheses"].startswith("array<EnglishText>")


@pytest.mark.parametrize("branch", ["L", "B"])
def test_typed_contract_preserves_all_feedback_and_artifacts(tmp_path, branch):
    from test_system_proposer_coherent_feedback import chain_fixture
    packet, roots = chain_fixture(tmp_path) if branch == "L" else fixture(tmp_path, "B")
    legacy = ProposerCapsule.from_packet(packet, roots=roots, view_profile="coherent-feedback-v1")
    typed = ProposerCapsule.from_packet(packet, roots=roots, view_profile="typed-coherent-feedback-v1")
    before, after = legacy.initial_input(), typed.initial_input()
    before.pop("response_contract")
    after.pop("response_contract")
    assert before == after
    assert legacy.as_json()["artifacts"] == typed.as_json()["artifacts"]
    if branch == "B":
        assert not any(a["kind"].startswith("feedback-") for a in typed.as_json()["artifacts"])
        assert "feedback_chain" not in after and "feedback_summary" not in after
