"""Level-2 note view (2026-10-10 live defect): the render-only Perception state that carries a
non-A branch's OWN note must still satisfy its own source-response binding.

The first live exercise of the level-2 render fix (NX R6-P1 smoke) stopped with
``hypothesis content does not match its source response SHA-256``: the view replaced the sealed
state's ``content`` with the branch's note but left ``source_response_sha256`` at A's response, so
``parse_slurp_intent_hypothesis_state`` (reached through ``KnowledgeProvider._candidate_state`` from
``perception_branch_solver_supply``) refused it. Both runner sites (``settle`` and
``_perception_note_view``) now build the view through ``perception_note_view_state``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.rails import runner
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import (
    HYPOTHESIS_SEMANTICS,
    HYPOTHESIS_STATE_SCHEMA,
    SlurpIntentHypothesisError,
    parse_slurp_intent_hypothesis_state,
)

LEGAL = frozenset({"weather_query", "transport_taxi", "calendar_set"})
SAMPLE_ID = "slurp:devel:0001"


def _note(intent_id: str) -> str:
    return json.dumps(
        {
            "schema": HYPOTHESIS_STATE_SCHEMA,
            "semantics": HYPOTHESIS_SEMANTICS,
            "sample_id": SAMPLE_ID,
            "candidates": [{
                "intent_id": intent_id,
                "distinction": "A distinction.",
                "evidence_refs": ["speech:full-utterance"],
                "unresolved_fields": [],
            }],
        },
        sort_keys=True,
    )


def _sealed(content: str) -> AgentStateArtifact:
    # Exactly the shape ``seal_phase_response_state`` produces for A.
    return AgentStateArtifact(
        state_id=f"c:hypotheses:{SAMPLE_ID}",
        state_kind="phase:hypotheses",
        content=content,
        source_query_state_sha256="1" * 64,
        source_response_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        producer_policy_id="phase-joint-intent-v1",
        cited_value_ids=(),
    ).validate()


def _parse(artifact):
    return parse_slurp_intent_hypothesis_state(
        artifact, expected_sample_id=SAMPLE_ID, legal_intent_ids=LEGAL, max_candidates=3,
    )


def test_content_only_swap_is_the_defect_and_the_helper_view_parses():
    a_state = _sealed(_note("weather_query"))
    b_note = _note("transport_taxi")
    # Master's construction: only ``content`` swapped -> refused by the real parser.
    with pytest.raises(SlurpIntentHypothesisError, match="source response SHA-256"):
        _parse(replace(a_state, content=b_note))
    # The fix: bound to the branch's own note bytes, exactly as A is bound to A's.
    view = runner.perception_note_view_state(a_state, note_text=b_note)
    assert [c.intent_id for c in _parse(view).candidates] == ["transport_taxi"]
    assert view.source_response_sha256 == hashlib.sha256(b_note.encode("utf-8")).hexdigest()
    # Custody fields are untouched, and A's own artifact is unchanged.
    for field in ("state_id", "state_kind", "source_query_state_sha256",
                  "producer_policy_id", "cited_value_ids"):
        assert getattr(view, field) == getattr(a_state, field)
    assert [c.intent_id for c in _parse(a_state).candidates] == ["weather_query"]
