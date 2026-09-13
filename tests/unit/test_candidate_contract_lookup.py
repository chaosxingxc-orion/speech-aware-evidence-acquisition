"""Synthetic tests for the bounded candidate-contract lookup foundation."""

from __future__ import annotations

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.rails import tools
from speech_aware_evidence_acquisition.rails.candidate_contract_lookup import (
    CandidateContractEvidence,
    CandidateContractLookupError,
    CandidateContractLookupResult,
    CandidateContractProvider,
    CandidateContractRequest,
    TOOL_ID,
    canonical_sha256,
)
from speech_aware_evidence_acquisition.rails.tool_wrappers.candidate_contract_lookup import (
    lookup_candidate_contracts,
)


SOURCE_SHA256 = canonical_sha256({"source": "synthetic-task-contract"})


class SyntheticProvider:
    source_sha256 = SOURCE_SHA256

    def __init__(self, result_factory, *, source_sha256=SOURCE_SHA256):
        self.result_factory = result_factory
        self.source_sha256 = source_sha256
        self.requests = []

    def lookup(self, candidate_ids):
        self.requests.append(candidate_ids)
        return self.result_factory(candidate_ids)


def _candidate(candidate_id: str, operation: str) -> CandidateContractEvidence:
    return CandidateContractEvidence(
        candidate_id=candidate_id,
        operation=operation,
        schema=(("slot", "entity"),),
        contrast=f"Use only for {operation}; avoid nearby operations.",
        required_keys=("slot",),
    )


def _result(request, candidates=None, source_sha256=None):
    if not isinstance(request, CandidateContractRequest):
        request = CandidateContractRequest(tuple(request))
    return CandidateContractLookupResult(
        request=request,
        source_sha256=source_sha256 or SOURCE_SHA256,
        candidates=tuple(
            candidates
            or (_candidate(item, item) for item in request.candidate_ids)
        ),
    )


def test_real_wrapper_path_preserves_order_and_hashes_without_mocking_catalog():
    provider = SyntheticProvider(_result)
    request_ids = ("intent_alpha", "intent_beta")
    wrapped = lookup_candidate_contracts(provider, request_ids)

    assert wrapped.tool_id == TOOL_ID
    assert isinstance(wrapped.result, CandidateContractLookupResult)
    assert provider.requests == [request_ids]
    assert tuple(item.candidate_id for item in wrapped.result.candidates) == request_ids
    assert wrapped.result.request.content_hash() == canonical_sha256(
        wrapped.result.request.as_json()
    )
    assert wrapped.result.content_hash() == hashlib.sha256(
        json.dumps(
            wrapped.result.as_json(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def test_request_duplicates_are_refused_before_provider_call():
    provider = SyntheticProvider(_result)
    with pytest.raises(CandidateContractLookupError, match="candidate_ids"):
        lookup_candidate_contracts(provider, ("intent_alpha", "intent_alpha"))
    assert provider.requests == []


@pytest.mark.parametrize(
    "returned_ids, message",
    [
        (("intent_beta", "intent_alpha"), "requested order"),
        (("intent_alpha", "foreign"), "requested order"),
        (("intent_alpha", "intent_alpha"), "duplicate"),
    ],
)
def test_unknown_reordered_or_duplicate_provider_ids_are_refused(returned_ids, message):
    provider = SyntheticProvider(
        lambda request: _result(
            CandidateContractRequest(request),
            candidates=tuple(_candidate(item, item) for item in returned_ids),
        )
    )
    with pytest.raises(CandidateContractLookupError, match=message):
        lookup_candidate_contracts(provider, ("intent_alpha", "intent_beta"))


def test_no_argument_contract_schema_is_legal():
    no_argument = CandidateContractEvidence(
        candidate_id="intent_no_slots",
        operation="No-slot intent",
        schema=(),
        contrast="Use only when no slot is required.",
    )
    provider = SyntheticProvider(
        lambda request: _result(
            request,
            candidates=(no_argument,),
        )
    )
    result = lookup_candidate_contracts(provider, ("intent_no_slots",)).result
    assert result.candidates[0].schema == ()


def test_result_must_match_bound_provider_source():
    foreign_source = canonical_sha256({"source": "foreign-task-contract"})
    provider = SyntheticProvider(
        lambda request: _result(request, source_sha256=foreign_source)
    )
    with pytest.raises(CandidateContractLookupError, match="provider source"):
        lookup_candidate_contracts(provider, ("intent_alpha",))


def test_wrong_source_hash_and_evidence_status_are_refused():
    provider = SyntheticProvider(
        lambda request: _result(
            CandidateContractRequest(request),
            source_sha256="not-a-hash",
        )
    )
    with pytest.raises(CandidateContractLookupError, match="source_sha256"):
        lookup_candidate_contracts(provider, ("intent_alpha",))
    provider = SyntheticProvider(
        lambda request: CandidateContractLookupResult(
            request=CandidateContractRequest(request),
            source_sha256=SOURCE_SHA256,
            candidates=(_candidate("intent_alpha", "intent_alpha"),),
            evidence_status="heard-query",
        )
    )
    with pytest.raises(CandidateContractLookupError, match="evidence_status"):
        lookup_candidate_contracts(provider, ("intent_alpha",))


def test_unknown_membership_is_a_canonical_provider_boundary():
    def lookup(candidate_ids):
        if "foreign" in candidate_ids:
            raise CandidateContractLookupError("canonical source rejected unknown candidate ID")
        return _result(candidate_ids)

    provider = SyntheticProvider(lookup)
    with pytest.raises(CandidateContractLookupError, match="unknown candidate ID"):
        lookup_candidate_contracts(provider, ("foreign",))


def test_registered_manifest_is_pinned_and_system_invoked():
    entry = tools.resolve_tool(TOOL_ID)
    assert entry.manifest.system_invoked is True
    assert entry.manifest.axis == "ORG"
    tools.assert_pinned_hash(entry.manifest)


def test_provider_protocol_accepts_only_lookup_objects():
    assert isinstance(SyntheticProvider(_result), CandidateContractProvider)
    assert not isinstance(object(), CandidateContractProvider)
