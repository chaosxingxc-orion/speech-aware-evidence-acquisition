"""Source-bound SLURP candidate-contract state for hypothesis consumers.

This view is an opt-in, model-free composition seam. It validates a typed
hypothesis artifact, asks the already prepared TRAIN candidate-contract
provider for the same ordered IDs, and renders only candidate IDs, schemas,
and observed-profile contrasts. Source hashes and response bookkeeping remain
in the surrounding provenance; no filler values, references, transcripts, or
final-authority instruction enter the state text.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping

from .candidate_contract_lookup import (
    CandidateContractLookupError,
    CandidateContractLookupResult,
    CandidateContractRequest,
)
from .knowledge import AgentStateArtifact
from .slurp_candidate_contracts import (
    SlurpCandidateContractProvider,
    build_slurp_candidate_contract_provider,
)
from .slurp_intent_hypotheses import (
    SlurpIntentHypothesisError,
    parse_slurp_intent_hypothesis_state,
)

VIEW_SCHEMA = "saea-slurp-hypothesis-candidate-contract-view-v1"
DEFAULT_MAX_HYPOTHESIS_CANDIDATES = 3
# Compatibility alias for callers that imported the historical default.
MAX_HYPOTHESIS_CANDIDATES = DEFAULT_MAX_HYPOTHESIS_CANDIDATES


class SlurpHypothesisCandidateContractViewError(ValueError):
    """A pinned source or source-bound hypothesis view is invalid."""


def _source_sha256(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.strip()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise SlurpHypothesisCandidateContractViewError(
            "candidate_source_sha256 must be 64 lowercase hexadecimal characters"
        )
    return value


def _max_candidates(value: object, *, legal_count: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
        or (
            value > DEFAULT_MAX_HYPOTHESIS_CANDIDATES
            and value > legal_count
        )
    ):
        raise SlurpHypothesisCandidateContractViewError(
            "max_candidates must be between 1 and the legal intent count "
            f"({legal_count})"
        )
    if legal_count < 1:
        raise SlurpHypothesisCandidateContractViewError(
            "candidate contract provider must expose at least one legal intent"
        )
    return value


def render_compact_candidate_contract_result(
    result: CandidateContractLookupResult,
) -> str:
    """Render one deterministic state payload from the native result model.

    The projection intentionally retains only the ordered candidate ID, its
    value-free schema, and the provider's observed-profile contrast. The
    result's source/request hashes and evidence classification remain in the
    runtime result/provenance object.
    """

    try:
        result.validate()
    except CandidateContractLookupError as error:
        raise SlurpHypothesisCandidateContractViewError(
            f"invalid candidate-contract result: {error}"
        ) from error
    document = {
        "candidates": [
            {
                "candidate_id": candidate.candidate_id,
                "schema": [
                    {"name": name, "type": type_name}
                    for name, type_name in candidate.schema
                ],
                "contrast": candidate.contrast,
            }
            for candidate in result.candidates
        ]
    }
    return json.dumps(
        document, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )


@dataclass(frozen=True)
class SlurpHypothesisCandidateContractStateView:
    """Render one source-bound hypothesis state for multiple phase branches."""

    provider: SlurpCandidateContractProvider
    candidate_source_sha256: str
    max_candidates: int = DEFAULT_MAX_HYPOTHESIS_CANDIDATES

    def __post_init__(self) -> None:
        pinned = _source_sha256(self.candidate_source_sha256)
        if self.provider.source_sha256 != pinned:
            raise SlurpHypothesisCandidateContractViewError(
                "candidate contract provider source does not match the pinned source"
            )
        _max_candidates(
            self.max_candidates, legal_count=len(self.provider.candidate_ids)
        )

    def with_max_candidates(
        self, max_candidates: int
    ) -> "SlurpHypothesisCandidateContractStateView":
        """Return the same immutable provider with a narrower configured bound."""

        return replace(self, max_candidates=max_candidates)

    def __call__(self, state_content: str) -> str:
        raise SlurpHypothesisCandidateContractViewError(
            "source-bound candidate-contract views require the full AgentStateArtifact"
        )

    def render_state(
        self, artifact: AgentStateArtifact, *, sample_id: str
    ) -> str:
        """Validate a sample's hypotheses and render ordered contracts.

        Both hard-first and joint consumers call this method on the same
        artifact and view, so the candidate ordering and bytes are shared.
        """

        try:
            state = parse_slurp_intent_hypothesis_state(
                artifact,
                expected_sample_id=sample_id,
                legal_intent_ids=self.provider.candidate_ids,
                max_candidates=min(self.max_candidates, len(self.provider.candidate_ids)),
            )
            request = CandidateContractRequest.from_ids(
                tuple(candidate.intent_id for candidate in state.candidates)
            )
            result = self.provider.lookup(request.candidate_ids)
            result.validate_for(request)
            if result.source_sha256 != self.candidate_source_sha256:
                raise SlurpHypothesisCandidateContractViewError(
                    "candidate contract result source does not match the pinned source"
                )
            return render_compact_candidate_contract_result(result)
        except SlurpHypothesisCandidateContractViewError:
            raise
        except (SlurpIntentHypothesisError, CandidateContractLookupError) as error:
            raise SlurpHypothesisCandidateContractViewError(str(error)) from error


def build_slurp_hypothesis_candidate_contract_view(
    lock: Mapping[str, object],
    root: Path,
    *,
    candidate_source_sha256: str,
    max_candidates: int = DEFAULT_MAX_HYPOTHESIS_CANDIDATES,
) -> SlurpHypothesisCandidateContractStateView:
    """Build the canonical TRAIN provider once and verify its source pin."""

    provider = build_slurp_candidate_contract_provider(lock, root)
    return SlurpHypothesisCandidateContractStateView(
        provider=provider,
        candidate_source_sha256=candidate_source_sha256,
        max_candidates=max_candidates,
    )


__all__ = [
    "DEFAULT_MAX_HYPOTHESIS_CANDIDATES",
    "MAX_HYPOTHESIS_CANDIDATES",
    "VIEW_SCHEMA",
    "SlurpHypothesisCandidateContractStateView",
    "SlurpHypothesisCandidateContractViewError",
    "build_slurp_hypothesis_candidate_contract_view",
    "render_compact_candidate_contract_result",
]
