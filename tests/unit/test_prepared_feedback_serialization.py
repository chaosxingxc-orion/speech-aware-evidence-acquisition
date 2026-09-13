"""Prepared feedback remains truthful ORG history through the speech renderer."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.model import FrozenCoreError
from speech_aware_evidence_acquisition.core.model.native_history import project_native_history
from speech_aware_evidence_acquisition.core.model.transport import _speech_history_texts
from speech_aware_evidence_acquisition.rails.core_client import (
    FrozenCoreClientError,
    _agent_history,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.prepared_feedback import (
    PREPARED_FEEDBACK_STATE_KIND,
    PreparedFeedbackStateArtifact,
    _state_id,
)


def _prepared_state() -> PreparedFeedbackStateArtifact:
    model_context = {
        "task_family": "slurp",
        "candidates": [{"label": "option-1", "quality": {"intent": 1.0}}],
    }
    context_sha256 = content_hash(model_context)
    values = {
        "prepared_artifact_sha256": "a" * 64,
        "source_feedback_sha256": "b" * 64,
        "construction_roster_sha256": "c" * 64,
        "model_context_sha256": context_sha256,
    }
    return PreparedFeedbackStateArtifact(
        state_id=_state_id(**values),
        state_kind=PREPARED_FEEDBACK_STATE_KIND,
        content=json.dumps(model_context, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
        cited_value_ids=(),
        **values,
    ).validate()


def test_prepared_feedback_history_is_truthful_and_renders_canonical_content():
    state = _prepared_state()
    history = _agent_history(
        agent_state=[state.as_json()],
        agent_contact_id="proposal",
        contact_instruction="Propose one provisional training feedback artifact.",
    )
    assert history[0] == {
        "turn": 1,
        "role": "agent_state",
        "state_id": state.state_id,
        "state_kind": PREPARED_FEEDBACK_STATE_KIND,
        "content": state.content,
        "content_sha256": hashlib.sha256(state.content.encode()).hexdigest(),
        "cited_value_ids": [],
        "prepared_feedback_state_version": state.prepared_feedback_state_version,
        "prepared_artifact_sha256": state.prepared_artifact_sha256,
        "source_feedback_sha256": state.source_feedback_sha256,
        "construction_roster_sha256": state.construction_roster_sha256,
        "model_context_sha256": state.model_context_sha256,
    }
    assert "source_query_state_sha256" not in history[0]
    assert "source_response_sha256" not in history[0]
    assert "producer_policy_id" not in history[0]
    rendered = _speech_history_texts(history)
    assert rendered == [
        f"[agent state {state.state_id} kind={state.state_kind}] {state.content}",
        "[agent control proposal] Propose one provisional training feedback artifact.",
    ]
    assert state.prepared_artifact_sha256 not in rendered[0]
    messages = [{"role": "system", "content": "System."}, {"role": "user", "content": []}]
    assert project_native_history(
        payload={"history": history}, messages=messages, state_texts=rendered
    ) == (messages, [])


def test_legacy_agent_state_history_and_renderer_remain_byte_stable():
    state = AgentStateArtifact(
        state_id="state:legacy",
        state_kind="phase:legacy",
        content="Legacy organized state.",
        source_query_state_sha256="1" * 64,
        source_response_sha256="2" * 64,
        producer_policy_id="legacy-organizer-v1",
        cited_value_ids=(),
    )
    history = _agent_history(
        agent_state=[state.as_json()], agent_contact_id="legacy", contact_instruction="Continue."
    )
    assert history[0] == {
        "turn": 1,
        "role": "agent_state",
        "state_id": "state:legacy",
        "state_kind": "phase:legacy",
        "content": "Legacy organized state.",
        "content_sha256": hashlib.sha256(b"Legacy organized state.").hexdigest(),
        "source_query_state_sha256": "1" * 64,
        "source_response_sha256": "2" * 64,
        "producer_policy_id": "legacy-organizer-v1",
        "cited_value_ids": [],
    }
    assert _speech_history_texts(history)[0] == "[agent state state:legacy kind=phase:legacy] Legacy organized state."


@pytest.mark.parametrize("change", ["version", "hash", "state_id"])
def test_prepared_feedback_state_malformed_provenance_is_refused(change):
    document = _prepared_state().as_json()
    if change == "version":
        document["prepared_feedback_state_version"] = "wrong"
    elif change == "hash":
        document["source_feedback_sha256"] = "z" * 64
    else:
        document["state_id"] = "prepared-feedback:" + "0" * 64
    with pytest.raises(FrozenCoreClientError, match="malformed Agent state"):
        _agent_history(
            agent_state=[document], agent_contact_id="proposal", contact_instruction="Propose."
        )


def test_prepared_feedback_duplicate_ids_and_transport_mutation_are_refused():
    state = _prepared_state()
    with pytest.raises(FrozenCoreClientError, match="duplicate state ids"):
        _agent_history(
            agent_state=[state.as_json(), state.as_json()],
            agent_contact_id="proposal", contact_instruction="Propose.",
        )
    history = _agent_history(
        agent_state=[state.as_json()], agent_contact_id="proposal", contact_instruction="Propose."
    )
    malformed = copy.deepcopy(history)
    malformed[0]["prepared_feedback_state_version"] = "wrong"
    with pytest.raises(FrozenCoreError, match="prepared feedback state"):
        _speech_history_texts(malformed)
    malformed = copy.deepcopy(history)
    malformed[0]["model_context_sha256"] = "0" * 64
    with pytest.raises(FrozenCoreError, match="prepared feedback state"):
        _speech_history_texts(malformed)
