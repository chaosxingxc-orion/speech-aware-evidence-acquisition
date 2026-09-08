"""The relaxed observation invariant: a REGISTERED derivation may move the
speech packet, nothing else may.

Change 3 of the 2026-09-08 openJiuwen assessment's ordered list. Until this
change ``rails.knowledge.assert_agent_step_binding`` froze
``speech_packet_id``/``speech_packet_sha256`` for a whole trajectory, which
also made a selective re-listen -- listening again, more closely, to a span of
the SAME call -- unexpressible. The relaxation admits exactly one new shape:
a successor packet that a :class:`SpeechPacketDerivation` chains to the packet
the trajectory STARTED from, with the derivation kind drawn from a closed
list.

Four claims are pinned here, in the order the change list states them:

1. today's steps are unchanged BYTE for byte -- a transition with no
   derivation serializes to the historical key set and hashes to the
   historical digest (``test_a_step_without_a_derivation_keeps_its_exact_json``
   builds that document independently of the dataclass);
2. a registered re-cut is admitted;
3. an unregistered packet swap is refused, with the historical sentence;
4. a derivation whose parent is not the original is refused -- including the
   subtle case where it chains to the PREVIOUS re-listen's own cut.
"""

import pytest

from speech_aware_evidence_acquisition.rails import (
    KeyFacet,
    KnowledgeSnapshot,
    QueryState,
    RailsError,
    ValueBundle,
    assert_agent_step_binding,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.knowledge import (
    SPEECH_PACKET_DERIVATION_KINDS,
    AgentStepTransition,
    SpeechPacketDerivation,
)

_SHA_SNAPSHOT_SOURCE = "a" * 64
_SHA_ORIGIN = "b" * 64
_SHA_SPLIT = "c" * 64
_SHA_FIRST_CUT = "d" * 64
_SHA_SECOND_CUT = "e" * 64
_SHA_FOREIGN = "f" * 64
_SHA_PARAMS = "1" * 64

_ORIGIN_PACKET = ("earnings21/dev/4341191", _SHA_ORIGIN)


def _snapshot() -> KnowledgeSnapshot:
    return KnowledgeSnapshot(
        snapshot_id="snapshot:relisten",
        source_split_identity_hash=_SHA_SNAPSHOT_SOURCE,
        source_sample_ids=("train/1",),
        builder_policy_id="builder-v1",
        facets=(
            KeyFacet(
                facet_id="facet:operation",
                dimension="operation",
                representation_kind="text",
                representation="reduce the current level",
                source_sample_ids=("train/1",),
            ),
        ),
        values=(
            ValueBundle(
                value_id="value:dim-light",
                content="Choose the dim-light route when brightness must fall.",
                associated_facet_ids=("facet:operation",),
                source_sample_ids=("train/1",),
                provenance_refs=("train/1",),
            ),
        ),
    )


def _query_state(**overrides) -> QueryState:
    values = dict(
        query_id="query:dev:4341191:step0",
        query_sample_id="earnings21/dev/4341191",
        speech_packet_id=_ORIGIN_PACKET[0],
        speech_packet_sha256=_ORIGIN_PACKET[1],
        use_split_identity_hash=_SHA_SPLIT,
    )
    values.update(overrides)
    return QueryState(**values)


def _derivation(**overrides) -> SpeechPacketDerivation:
    values = dict(
        parent_packet_id=_ORIGIN_PACKET[0],
        parent_packet_sha256=_ORIGIN_PACKET[1],
        derived_packet_id="earnings21/dev/4341191/relisten0",
        derived_packet_sha256=_SHA_FIRST_CUT,
        derivation_kind="recut-span",
        derivation_params_hash=_SHA_PARAMS,
    )
    values.update(overrides)
    return SpeechPacketDerivation(**values)


def _transition(
    snapshot: KnowledgeSnapshot,
    prior: QueryState,
    next_state: QueryState | None,
    **overrides,
) -> AgentStepTransition:
    values = dict(
        snapshot_sha256=snapshot.content_hash(),
        prior_query_state_sha256=prior.content_hash(),
        next_query_state_sha256=(
            None if next_state is None else next_state.content_hash()
        ),
        action_kind="relisten",
        action_target_refs=("earnings21/dev/4341191/relisten0",),
        new_value_ids=(),
        used_value_ids=(),
        dropped_value_ids=(),
        new_agent_state_ids=(),
        dropped_agent_state_ids=(),
        speech_packet_derivation=_derivation(),
    )
    values.update(overrides)
    return AgentStepTransition(**values)


# --------------------------------------------------------------------------
# 1. Today's steps, unchanged byte for byte
# --------------------------------------------------------------------------


def test_a_step_without_a_derivation_keeps_its_exact_json_and_hash():
    """The historical key set and digest, rebuilt here independently of the
    dataclass: adding an optional field must not move a single sealed byte."""

    snapshot = _snapshot()
    prior = _query_state()
    next_state = _query_state(
        query_id="query:dev:4341191:step1",
        loop_step=1,
        retrieved_value_ids=("value:dim-light",),
    )
    transition = _transition(
        snapshot,
        prior,
        next_state,
        action_kind="acquire",
        action_target_refs=("operation",),
        new_value_ids=("value:dim-light",),
        speech_packet_derivation=None,
    )
    expected = {
        "transition_version": "knowledge-agent-step-transition-v1",
        "snapshot_sha256": snapshot.content_hash(),
        "prior_query_state_sha256": prior.content_hash(),
        "next_query_state_sha256": next_state.content_hash(),
        "action_kind": "acquire",
        "action_target_refs": ["operation"],
        "new_value_ids": ["value:dim-light"],
        "used_value_ids": [],
        "dropped_value_ids": [],
        "new_agent_state_ids": [],
        "dropped_agent_state_ids": [],
        "new_facet_ids": [],
        "used_facet_ids": [],
        "dropped_facet_ids": [],
    }
    assert transition.as_json() == expected
    assert "speech_packet_derivation" not in transition.as_json()
    assert transition.content_hash() == content_hash(expected)
    assert AgentStepTransition.from_json(transition.as_json()) == transition


def test_a_caller_that_names_no_origin_still_freezes_the_packet():
    """No ``origin_speech_packet`` argument, no derivation: every caller
    written before 2026-09-08 keeps the old rule and the old sentence."""

    snapshot = _snapshot()
    prior = _query_state()
    unchanged = _query_state(
        query_id="query:dev:4341191:step1",
        loop_step=1,
        agent_state_ids=("state:brief",),
    )
    organize = dict(
        action_kind="organize",
        action_target_refs=("brief-schema-v1",),
        new_agent_state_ids=("state:brief",),
        speech_packet_derivation=None,
    )
    assert_agent_step_binding(
        snapshot=snapshot,
        prior_query_state=prior,
        next_query_state=unchanged,
        transition=_transition(snapshot, prior, unchanged, **organize),
    )

    swapped = _query_state(
        query_id="query:dev:4341191:step1",
        loop_step=1,
        agent_state_ids=("state:brief",),
        speech_packet_sha256=_SHA_FOREIGN,
    )
    with pytest.raises(RailsError, match="same original speech packet"):
        assert_agent_step_binding(
            snapshot=snapshot,
            prior_query_state=prior,
            next_query_state=swapped,
            transition=_transition(snapshot, prior, swapped, **organize),
        )


# --------------------------------------------------------------------------
# 2. A registered re-cut is admitted
# --------------------------------------------------------------------------


def test_a_registered_recut_span_admits_a_moved_speech_packet():
    snapshot = _snapshot()
    prior = _query_state()
    next_state = _query_state(
        query_id="query:dev:4341191:step1",
        loop_step=1,
        speech_packet_id="earnings21/dev/4341191/relisten0",
        speech_packet_sha256=_SHA_FIRST_CUT,
    )
    transition = _transition(snapshot, prior, next_state)
    assert_agent_step_binding(
        snapshot=snapshot,
        prior_query_state=prior,
        next_query_state=next_state,
        transition=transition,
        origin_speech_packet=_ORIGIN_PACKET,
    )
    assert transition.action_kind == "relisten"
    assert AgentStepTransition.from_json(transition.as_json()) == transition
    assert transition.as_json()["speech_packet_derivation"] == {
        "derivation_version": "knowledge-speech-packet-derivation-v1",
        "parent_packet_id": _ORIGIN_PACKET[0],
        "parent_packet_sha256": _ORIGIN_PACKET[1],
        "derived_packet_id": "earnings21/dev/4341191/relisten0",
        "derived_packet_sha256": _SHA_FIRST_CUT,
        "derivation_kind": "recut-span",
        "derivation_params_hash": _SHA_PARAMS,
    }


@pytest.mark.parametrize("kind", sorted(SPEECH_PACKET_DERIVATION_KINDS))
def test_every_closed_list_kind_is_admitted(kind):
    snapshot = _snapshot()
    prior = _query_state()
    next_state = _query_state(
        query_id="query:dev:4341191:step1",
        loop_step=1,
        speech_packet_id="earnings21/dev/4341191/relisten0",
        speech_packet_sha256=_SHA_FIRST_CUT,
    )
    assert_agent_step_binding(
        snapshot=snapshot,
        prior_query_state=prior,
        next_query_state=next_state,
        transition=_transition(
            snapshot,
            prior,
            next_state,
            speech_packet_derivation=_derivation(derivation_kind=kind),
        ),
        origin_speech_packet=_ORIGIN_PACKET,
    )


def test_a_second_relisten_chains_to_the_original_not_to_the_first_cut():
    """The reason the ORIGIN travels with the caller rather than with the
    prior step: two re-listens in a row must both cut the same parent media."""

    snapshot = _snapshot()
    prior = _query_state(
        query_id="query:dev:4341191:step1",
        loop_step=1,
        speech_packet_id="earnings21/dev/4341191/relisten0",
        speech_packet_sha256=_SHA_FIRST_CUT,
    )
    next_state = _query_state(
        query_id="query:dev:4341191:step2",
        loop_step=2,
        speech_packet_id="earnings21/dev/4341191/relisten1",
        speech_packet_sha256=_SHA_SECOND_CUT,
    )
    assert_agent_step_binding(
        snapshot=snapshot,
        prior_query_state=prior,
        next_query_state=next_state,
        transition=_transition(
            snapshot,
            prior,
            next_state,
            action_target_refs=("earnings21/dev/4341191/relisten1",),
            speech_packet_derivation=_derivation(
                derived_packet_id="earnings21/dev/4341191/relisten1",
                derived_packet_sha256=_SHA_SECOND_CUT,
            ),
        ),
        origin_speech_packet=_ORIGIN_PACKET,
    )


# --------------------------------------------------------------------------
# 3. An unregistered packet swap is refused, with the historical sentence
# --------------------------------------------------------------------------


def test_an_unregistered_packet_swap_is_refused_with_the_historical_message():
    snapshot = _snapshot()
    prior = _query_state()
    next_state = _query_state(
        query_id="query:dev:4341191:step1",
        loop_step=1,
        speech_packet_sha256=_SHA_FOREIGN,
    )
    with pytest.raises(RailsError, match="same original speech packet"):
        assert_agent_step_binding(
            snapshot=snapshot,
            prior_query_state=prior,
            next_query_state=next_state,
            transition=_transition(
                snapshot,
                prior,
                next_state,
                action_kind="organize",
                action_target_refs=("brief-schema-v1",),
                new_agent_state_ids=("state:brief",),
                speech_packet_derivation=None,
            ),
            origin_speech_packet=_ORIGIN_PACKET,
        )


def test_a_derivation_record_cannot_ride_a_non_relisten_action():
    snapshot = _snapshot()
    prior = _query_state()
    next_state = _query_state(
        query_id="query:dev:4341191:step1",
        loop_step=1,
        speech_packet_id="earnings21/dev/4341191/relisten0",
        speech_packet_sha256=_SHA_FIRST_CUT,
    )
    with pytest.raises(RailsError, match="only a 'relisten'"):
        _transition(
            snapshot,
            prior,
            next_state,
            action_kind="verify",
            used_value_ids=("value:dim-light",),
        ).validate()


def test_a_relisten_without_its_derivation_record_is_refused():
    snapshot = _snapshot()
    prior = _query_state()
    next_state = _query_state(
        query_id="query:dev:4341191:step1",
        loop_step=1,
        speech_packet_id="earnings21/dev/4341191/relisten0",
        speech_packet_sha256=_SHA_FIRST_CUT,
    )
    with pytest.raises(RailsError, match="requires its speech-packet derivation"):
        _transition(
            snapshot, prior, next_state, speech_packet_derivation=None
        ).validate()


def test_a_relisten_cannot_claim_knowledge_use_or_new_agent_state():
    snapshot = _snapshot()
    prior = _query_state(retrieved_value_ids=("value:dim-light",))
    next_state = _query_state(
        query_id="query:dev:4341191:step1",
        loop_step=1,
        retrieved_value_ids=("value:dim-light",),
        speech_packet_id="earnings21/dev/4341191/relisten0",
        speech_packet_sha256=_SHA_FIRST_CUT,
    )
    with pytest.raises(RailsError, match="changes only the observation"):
        _transition(
            snapshot,
            prior,
            next_state,
            used_value_ids=("value:dim-light",),
        ).validate()


def test_a_derivation_that_derives_nothing_is_refused():
    snapshot = _snapshot()
    prior = _query_state()
    next_state = _query_state(query_id="query:dev:4341191:step1", loop_step=1)
    with pytest.raises(RailsError, match="derives nothing"):
        assert_agent_step_binding(
            snapshot=snapshot,
            prior_query_state=prior,
            next_query_state=next_state,
            transition=_transition(snapshot, prior, next_state),
            origin_speech_packet=_ORIGIN_PACKET,
        )


# --------------------------------------------------------------------------
# 4. A derivation whose parent is not the original is refused
# --------------------------------------------------------------------------


def test_a_derivation_whose_parent_is_not_the_original_is_refused():
    snapshot = _snapshot()
    prior = _query_state()
    next_state = _query_state(
        query_id="query:dev:4341191:step1",
        loop_step=1,
        speech_packet_id="earnings21/dev/4341191/relisten0",
        speech_packet_sha256=_SHA_FIRST_CUT,
    )
    with pytest.raises(RailsError, match="must chain to this trajectory's ORIGINAL"):
        assert_agent_step_binding(
            snapshot=snapshot,
            prior_query_state=prior,
            next_query_state=next_state,
            transition=_transition(
                snapshot,
                prior,
                next_state,
                speech_packet_derivation=_derivation(
                    parent_packet_id="earnings21/dev/9999999",
                    parent_packet_sha256=_SHA_FOREIGN,
                ),
            ),
            origin_speech_packet=_ORIGIN_PACKET,
        )


def test_a_second_relisten_that_chains_to_the_first_cut_is_refused():
    """Derivation-of-a-derivation: each cut would be one step further from the
    media, and no single record would still name the original."""

    snapshot = _snapshot()
    prior = _query_state(
        query_id="query:dev:4341191:step1",
        loop_step=1,
        speech_packet_id="earnings21/dev/4341191/relisten0",
        speech_packet_sha256=_SHA_FIRST_CUT,
    )
    next_state = _query_state(
        query_id="query:dev:4341191:step2",
        loop_step=2,
        speech_packet_id="earnings21/dev/4341191/relisten1",
        speech_packet_sha256=_SHA_SECOND_CUT,
    )
    with pytest.raises(RailsError, match="must chain to this trajectory's ORIGINAL"):
        assert_agent_step_binding(
            snapshot=snapshot,
            prior_query_state=prior,
            next_query_state=next_state,
            transition=_transition(
                snapshot,
                prior,
                next_state,
                action_target_refs=("earnings21/dev/4341191/relisten1",),
                speech_packet_derivation=_derivation(
                    parent_packet_id="earnings21/dev/4341191/relisten0",
                    parent_packet_sha256=_SHA_FIRST_CUT,
                    derived_packet_id="earnings21/dev/4341191/relisten1",
                    derived_packet_sha256=_SHA_SECOND_CUT,
                ),
            ),
            origin_speech_packet=_ORIGIN_PACKET,
        )


def test_a_derivation_that_does_not_produce_the_successor_packet_is_refused():
    snapshot = _snapshot()
    prior = _query_state()
    next_state = _query_state(
        query_id="query:dev:4341191:step1",
        loop_step=1,
        speech_packet_id="earnings21/dev/4341191/relisten0",
        speech_packet_sha256=_SHA_SECOND_CUT,
    )
    with pytest.raises(RailsError, match="does not produce the successor"):
        assert_agent_step_binding(
            snapshot=snapshot,
            prior_query_state=prior,
            next_query_state=next_state,
            transition=_transition(snapshot, prior, next_state),
            origin_speech_packet=_ORIGIN_PACKET,
        )


# --------------------------------------------------------------------------
# The record's own closed-list and self-consistency rules
# --------------------------------------------------------------------------


def test_a_derivation_kind_outside_the_closed_list_is_refused():
    with pytest.raises(RailsError, match="derivation_kind must be one of"):
        _derivation(derivation_kind="synthesized-audio").validate()


def test_a_derivation_reusing_its_parent_identity_is_refused():
    with pytest.raises(RailsError, match="must produce a NEW packet id"):
        _derivation(derived_packet_id=_ORIGIN_PACKET[0]).validate()
    with pytest.raises(RailsError, match="derived nothing"):
        _derivation(derived_packet_sha256=_ORIGIN_PACKET[1]).validate()


def test_a_derivation_round_trips_through_json():
    derivation = _derivation()
    assert SpeechPacketDerivation.from_json(derivation.as_json()) == derivation
    assert derivation.content_hash() == content_hash(derivation.as_json())


def test_an_unversioned_derivation_can_never_be_used():
    with pytest.raises(RailsError, match="derivation_version must be"):
        _derivation(derivation_version="v0").validate()
