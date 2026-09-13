"""Thin SYSTEM-invoked wrapper for canonical candidate-contract lookup."""

from __future__ import annotations

from ..candidate_contract_lookup import (
    CandidateContractLookupError,
    CandidateContractProvider,
    CandidateContractRequest,
    CandidateContractLookupResult,
    TOOL_ID,
)


def lookup_candidate_contracts(
    provider: CandidateContractProvider, candidate_ids
):
    """Resolve model-selected IDs through a bound canonical task-contract provider."""

    from ..tools import ToolResult

    if not isinstance(provider, CandidateContractProvider):
        raise CandidateContractLookupError(
            "candidate-contract lookup requires a canonical provider"
        )
    request = CandidateContractRequest.from_ids(candidate_ids)
    result = provider.lookup(request.candidate_ids)
    if not isinstance(result, CandidateContractLookupResult):
        raise CandidateContractLookupError(
            "canonical provider returned the wrong result type"
        )
    result.validate_for(request)
    if result.source_sha256 != provider.source_sha256:
        raise CandidateContractLookupError(
            "provider source does not match result source"
        )
    return ToolResult(tool_id=TOOL_ID, result=result)


__all__ = ["lookup_candidate_contracts"]
