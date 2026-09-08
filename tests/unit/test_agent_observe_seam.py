"""The Observer seam: the previous wave's REVIEW flags become the next wave's
observation, and its absence changes nothing.

Change 4 of the 2026-09-08 openJiuwen assessment's ordered list. The seam sits
in the agent loop's wave preparation (``rails.runner``, shared by BOTH
executors so the ``reference-trajectory-v1`` equivalence oracle keeps covering
it) and consumes change 3's registered derivation.

Three things are pinned here:

1. **The default is inert.** ``observe_step=None`` and an ObserveStep whose
   Reviewer flagged nothing produce identical result JSON and an identical
   trace record sequence -- no OBS record, no ``relisten`` transition, no
   moved packet, no extra contact.
2. **A flagged span really is re-listened to.** The next wave's request
   carries the DERIVED packet, a ``relisten`` transition sits between the two
   controller steps carrying its derivation, and the two executors still agree
   on the whole result JSON.
3. **Every named failure is closed.** A span outside its media, a cutter that
   produced no derivation, a margin that is not a finite non-negative number,
   and more flagged spans than the configured re-listen budget all refuse --
   none of them is a silently skipped step.

``SliceReCutter`` is exercised against real bytes (a synthetic WAV through
``core.span_surgery.cut_span`` and a real ``SliceRegistry``), because "through
the replay loop's existing re-cut mechanism" is a claim about the byte chain,
not about a shape.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.model import FrozenCoreError, SliceRegistry
from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
from speech_aware_evidence_acquisition.rails import (
    AgentLoopAdvance,
    AgentStateArtifact,
    AgentStepTransition,
    QueryState,
    run_speech_native_agent_loop,
)
from speech_aware_evidence_acquisition.rails.observe import (
    FlaggedSpan,
    ObserveConfig,
    ObserveError,
    ObserveStep,
    ReListenResult,
    ReviewFlags,
    SliceReCutter,
    fixture_flag_source,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_rails_runner import (  # noqa: E402
    _SHA_C,
    _agent_trace,
    _contact,
    _controller_registry,
    _knowledge_snapshot,
    _one_sample_adapter,
    _plan,
    _RecordingAgentClient,
)

_MEDIA_SECONDS = 10.0
_MEDIA_FACTS = {"s1": ("a.wav", _MEDIA_SECONDS)}
_FLAG_DOCUMENT = [
    {
        "sample_id": "s1",
        "wave_index": 0,
        "spans": [{"start": 4.0, "end": 5.0, "reason": "low-confidence-decode"}],
    }
]


# --------------------------------------------------------------------------
# Fixtures: a controller whose loop_step is relative, and a cutter with no
# model in it
# --------------------------------------------------------------------------


def _successor(prior: QueryState, **overrides) -> QueryState:
    values = dict(
        query_id=prior.query_id,
        query_sample_id=prior.query_sample_id,
        speech_packet_id=prior.speech_packet_id,
        speech_packet_sha256=prior.speech_packet_sha256,
        use_split_identity_hash=prior.use_split_identity_hash,
        loop_step=prior.loop_step + 1,
        visible_facet_ids=prior.visible_facet_ids,
        agent_state_ids=prior.agent_state_ids,
        retrieved_value_ids=prior.retrieved_value_ids,
    )
    values.update(overrides)
    return QueryState(**values).validate()


class _OrganizeThenStopController:
    """Two waves, one gap between them -- exactly one place an Observer step
    can land. ``loop_step`` is derived from the context, never hardcoded, so
    an inserted Observer step keeps the successor's increment legal."""

    def __init__(self) -> None:
        self.seen_packets: list[str] = []

    def initial_contact(self, context):
        return _contact(context.query_state, 0, "primary")

    def advance(self, context, contact, response_text):
        prior = context.query_state
        self.seen_packets.append(prior.speech_packet_id)
        if len(self.seen_packets) == 1:
            state = AgentStateArtifact(
                state_id="state:span-unclear",
                state_kind="intent-factor",
                content="The flagged span is not resolved yet.",
                source_query_state_sha256=prior.content_hash(),
                source_response_sha256=hashlib.sha256(
                    response_text.encode("utf-8")
                ).hexdigest(),
                producer_policy_id="observe-seam-test-v1",
                cited_value_ids=(),
            )
            next_state = _successor(prior, agent_state_ids=(state.state_id,))
            return AgentLoopAdvance(
                transition=AgentStepTransition(
                    snapshot_sha256=context.knowledge_snapshot_sha256,
                    prior_query_state_sha256=prior.content_hash(),
                    next_query_state_sha256=next_state.content_hash(),
                    action_kind="organize",
                    action_target_refs=("intent-factor-schema-v1",),
                    new_value_ids=(),
                    used_value_ids=(),
                    dropped_value_ids=(),
                    new_agent_state_ids=(state.state_id,),
                    dropped_agent_state_ids=(),
                ),
                next_query_state=next_state,
                new_agent_states=(state,),
                next_contact=_contact(next_state, 1, "revise"),
            )
        return AgentLoopAdvance(
            transition=AgentStepTransition(
                snapshot_sha256=context.knowledge_snapshot_sha256,
                prior_query_state_sha256=prior.content_hash(),
                next_query_state_sha256=None,
                action_kind="stop",
                action_target_refs=(),
                new_value_ids=(),
                used_value_ids=(),
                dropped_value_ids=(),
                new_agent_state_ids=(),
                dropped_agent_state_ids=(),
            ),
            next_query_state=None,
            new_agent_states=(),
            next_contact=None,
        )


class _FakeCutter:
    """A cutter with no encoder in it: the byte chain is exercised separately
    by ``TestSliceReCutter`` against real WAV bytes."""

    def __init__(self) -> None:
        self.requests: list[object] = []

    def __call__(self, request):
        self.requests.append(request)
        digest = hashlib.sha256(
            f"{request.sample_id}|{request.start_seconds}|{request.end_seconds}".encode(
                "utf-8"
            )
        ).hexdigest()
        return ReListenResult(
            packet_id=f"fake/dev/{request.sample_id}/relisten{request.relisten_index}",
            packet_sha256=digest,
            provenance={"media_relpath": f"derived/obs-slices/{request.sample_id}.wav"},
        )


def _observe_step(
    *,
    flags=None,
    cutter=None,
    config: ObserveConfig | None = None,
    media_facts=None,
) -> ObserveStep:
    return ObserveStep(
        config=config
        or ObserveConfig(context_margin_seconds=1.5, max_relistens_per_sample=2),
        flag_source=fixture_flag_source(
            _FLAG_DOCUMENT if flags is None else flags
        ),
        cutter=cutter or _FakeCutter(),
        media_facts=_MEDIA_FACTS if media_facts is None else media_facts,
    )


def _run(tmp_path: Path, *, executor_id: str, observe_step=None):
    sink = _agent_trace()
    controller = _OrganizeThenStopController()
    client = _RecordingAgentClient()
    summary = run_speech_native_agent_loop(
        data_root=tmp_path,
        plan=_plan(
            execution_profile=(
                "model-free-check"
                if executor_id == "reference-trajectory-v1"
                else "bounded-discovery-probe"
            )
        ),
        adapter=_one_sample_adapter(),
        core_client=client,
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings={"s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}},
        controller_policy_id=f"observe-seam-{executor_id}",
        controller_registry=_controller_registry(
            f"observe-seam-{executor_id}", lambda _sample_id: controller
        ),
        max_contacts=2,
        slot_count=1,
        queue_depth=2,
        trace_sink=sink,
        agent_executor_id=executor_id,
        observe_step=observe_step,
    )
    return summary, client, controller, sink


def _records(sink: TraceBuffer):
    return [
        (channel, record_id, payload) for channel, record_id, payload in sink.records
    ]


def _query_packets(client: _RecordingAgentClient) -> list[dict]:
    packets = []
    for messages, _options in client.calls:
        for part in messages[1]["content"]:
            if part["type"] == "input_speech_features":
                packets.append(dict(part["speech_features"]))
    return packets


# --------------------------------------------------------------------------
# 1. The default is inert
# --------------------------------------------------------------------------


def test_an_absent_observer_and_a_silent_reviewer_produce_the_same_graph(
    tmp_path: Path,
):
    absent_summary, absent_client, _, absent_sink = _run(
        tmp_path / "absent", executor_id="reference-trajectory-v1"
    )
    silent_summary, silent_client, _, silent_sink = _run(
        tmp_path / "silent",
        executor_id="reference-trajectory-v1",
        observe_step=_observe_step(flags=[]),
    )

    assert absent_summary.results[0].as_json() == silent_summary.results[0].as_json()
    assert _records(absent_sink) == _records(silent_sink)
    assert _query_packets(absent_client) == _query_packets(silent_client)


def test_an_absent_observer_emits_no_obs_record_and_no_relisten_transition(
    tmp_path: Path,
):
    summary, client, _, sink = _run(
        tmp_path, executor_id="reference-trajectory-v1"
    )
    result = summary.results[0]
    assert [transition.action_kind for transition in result.transitions] == [
        "organize",
        "stop",
    ]
    assert all(
        transition.speech_packet_derivation is None
        for transition in result.transitions
    )
    assert not [record for record in sink.records if record[0] == "OBS"]
    assert result.final_query_state.speech_packet_id == "fake/dev/s1"
    assert {packet["packet_id"] for packet in _query_packets(client)} == {"fake/dev/s1"}
    # The whole result JSON must stay JSON-serializable and free of the new key.
    assert "speech_packet_derivation" not in json.dumps(result.as_json())


# --------------------------------------------------------------------------
# 2. A flagged span really is re-listened to
# --------------------------------------------------------------------------


def test_a_flagged_span_becomes_a_registered_relisten_the_next_wave_listens_to(
    tmp_path: Path,
):
    cutter = _FakeCutter()
    summary, client, controller, sink = _run(
        tmp_path,
        executor_id="reference-trajectory-v1",
        observe_step=_observe_step(cutter=cutter),
    )
    result = summary.results[0]

    assert [transition.action_kind for transition in result.transitions] == [
        "organize",
        "relisten",
        "stop",
    ]
    relisten = result.transitions[1]
    derivation = relisten.speech_packet_derivation
    assert derivation is not None
    assert (derivation.parent_packet_id, derivation.parent_packet_sha256) == (
        "fake/dev/s1",
        _SHA_C,
    )
    assert derivation.derivation_kind == "recut-span"
    derived_packet_id = derivation.derived_packet_id

    # The context margin widened the flagged [4.0, 5.0) span on both sides.
    assert len(cutter.requests) == 1
    request = cutter.requests[0]
    assert (request.start_seconds, request.end_seconds) == (2.5, 6.5)
    assert request.span == FlaggedSpan(4.0, 5.0, "low-confidence-decode")

    # The SECOND wave listens to the derived packet; the first still listened
    # to the original. The re-listen spent no contact: max_contacts was 2.
    assert _query_packets(client) == [
        {"packet_id": "fake/dev/s1", "sha256": _SHA_C, "role": "query"},
        {
            "packet_id": derived_packet_id,
            "sha256": derivation.derived_packet_sha256,
            "role": "query",
        },
    ]
    assert controller.seen_packets == ["fake/dev/s1", derived_packet_id]
    assert len(result.contacts) == 2
    assert result.final_query_state.speech_packet_id == derived_packet_id

    # The controller's own contact was re-bound, not replaced.
    assert [record.plan.purpose for record in result.contacts] == [
        "primary",
        "revise",
    ]
    assert result.contacts[1].plan.contact_id == "contact-1"


def test_the_obs_record_states_the_span_the_margin_and_the_whole_chain(
    tmp_path: Path,
):
    summary, _client, _controller, sink = _run(
        tmp_path,
        executor_id="reference-trajectory-v1",
        observe_step=_observe_step(),
    )
    obs = [record for record in sink.records if record[0] == "OBS"]
    assert len(obs) == 1
    _channel, record_id, payload = obs[0]
    assert record_id == "s1/agent-loop/relisten0000"
    derivation = summary.results[0].transitions[1].speech_packet_derivation
    assert payload["obs_wave_index"] == 0
    assert payload["obs_flag_reason"] == "low-confidence-decode"
    assert payload["obs_flagged_span_start_seconds"] == 4.0
    assert payload["obs_flagged_span_end_seconds"] == 5.0
    assert payload["obs_context_margin_seconds"] == 1.5
    assert payload["obs_cut_start_seconds"] == 2.5
    assert payload["obs_cut_end_seconds"] == 6.5
    assert payload["obs_parent_packet_id"] == "fake/dev/s1"
    assert payload["obs_derived_packet_id"] == derivation.derived_packet_id
    assert payload["obs_derivation_params_hash"] == derivation.derivation_params_hash
    assert payload["obs_derivation_provenance"] == {
        "media_relpath": "derived/obs-slices/s1.wav"
    }


@pytest.mark.skipif(
    not openjiuwen_available(),
    reason="openjiuwen is absent; the reference executor remains dependency-free",
)
def test_both_executors_agree_with_the_observer_active(tmp_path: Path):
    summaries = []
    for executor_id in ("reference-trajectory-v1", "openjiuwen-workflow-v1"):
        summary, _client, _controller, _sink = _run(
            tmp_path / executor_id,
            executor_id=executor_id,
            observe_step=_observe_step(),
        )
        summaries.append(summary)
    assert summaries[0].results[0].as_json() == summaries[1].results[0].as_json()
    assert [
        transition.action_kind for transition in summaries[1].results[0].transitions
    ] == ["organize", "relisten", "stop"]


@pytest.mark.skipif(
    not openjiuwen_available(),
    reason="openjiuwen is absent; the reference executor remains dependency-free",
)
def test_both_executors_agree_when_the_reviewer_is_silent(tmp_path: Path):
    summaries = []
    for executor_id in ("reference-trajectory-v1", "openjiuwen-workflow-v1"):
        summary, _client, _controller, _sink = _run(
            tmp_path / executor_id,
            executor_id=executor_id,
            observe_step=_observe_step(flags=[]),
        )
        summaries.append(summary)
    assert summaries[0].results[0].as_json() == summaries[1].results[0].as_json()


def test_rebinding_a_contact_wave_moves_only_the_query_state_hash():
    """A fan-out wave is re-bound branch by branch: the Observer changes WHAT
    the next contacts listen to, never WHAT they are asked."""

    from speech_aware_evidence_acquisition.rails import AgentContactBatch
    from speech_aware_evidence_acquisition.rails.runner import _rebind_contact

    before = QueryState(
        query_id="q0",
        query_sample_id="s1",
        speech_packet_id="fake/dev/s1",
        speech_packet_sha256=_SHA_C,
        use_split_identity_hash="a" * 64,
    )
    after = QueryState(
        query_id="q0:relisten0000",
        query_sample_id="s1",
        speech_packet_id="fake/dev/s1/relisten0",
        speech_packet_sha256="d" * 64,
        use_split_identity_hash="a" * 64,
        loop_step=1,
    )
    batch = AgentContactBatch(
        batch_id="parallel-factors",
        query_state_sha256=before.content_hash(),
        contacts=(
            _contact(before, 0, "content-factor"),
            _contact(before, 1, "boundary-factor"),
        ),
    ).validate()

    rebound = _rebind_contact(batch, after.content_hash())
    assert rebound.query_state_sha256 == after.content_hash()
    assert all(
        plan.query_state_sha256 == after.content_hash() for plan in rebound.contacts
    )
    assert [plan.contact_id for plan in rebound.contacts] == [
        plan.contact_id for plan in batch.contacts
    ]
    assert [plan.instruction for plan in rebound.contacts] == [
        plan.instruction for plan in batch.contacts
    ]


# --------------------------------------------------------------------------
# 3. Every named failure is closed
# --------------------------------------------------------------------------


class TestFailClosed:
    def test_a_span_outside_its_media_is_refused(self):
        step = _observe_step(
            flags=[
                {
                    "sample_id": "s1",
                    "spans": [{"start": 9.0, "end": 12.0, "reason": "past the end"}],
                }
            ]
        )
        with pytest.raises(ObserveError, match="lies outside sample"):
            step.observe(
                sample_id="s1",
                wave_index=0,
                origin_packet=("fake/dev/s1", _SHA_C),
                relisten_index=0,
            )

    def test_a_sample_with_no_verified_media_is_refused(self):
        step = _observe_step(media_facts={})
        with pytest.raises(ObserveError, match="no verified media"):
            step.observe(
                sample_id="s1",
                wave_index=0,
                origin_packet=("fake/dev/s1", _SHA_C),
                relisten_index=0,
            )

    def test_a_cutter_that_produced_no_derivation_is_refused(self):
        step = _observe_step(cutter=lambda request: None)
        with pytest.raises(ObserveError, match="produced no derived packet"):
            step.observe(
                sample_id="s1",
                wave_index=0,
                origin_packet=("fake/dev/s1", _SHA_C),
                relisten_index=0,
            )

    @pytest.mark.parametrize("margin", [-0.5, float("nan"), float("inf"), "1.0", None])
    def test_a_margin_that_is_not_a_finite_non_negative_number_is_refused(self, margin):
        with pytest.raises(ObserveError, match="context_margin_seconds"):
            ObserveConfig(
                context_margin_seconds=margin, max_relistens_per_sample=2
            ).validate()

    def test_more_flagged_spans_than_the_budget_is_refused(self):
        step = _observe_step(
            config=ObserveConfig(
                context_margin_seconds=0.5, max_relistens_per_sample=1
            ),
            flags=[
                {
                    "sample_id": "s1",
                    "spans": [
                        {"start": 1.0, "end": 2.0, "reason": "first"},
                        {"start": 3.0, "end": 4.0, "reason": "second"},
                    ],
                }
            ],
        )
        with pytest.raises(ObserveError, match="max_relistens_per_sample"):
            step.observe(
                sample_id="s1",
                wave_index=0,
                origin_packet=("fake/dev/s1", _SHA_C),
                relisten_index=0,
            )

    def test_an_exhausted_flag_list_ends_the_relistens_rather_than_raising(self):
        step = _observe_step()
        assert (
            step.observe(
                sample_id="s1",
                wave_index=0,
                origin_packet=("fake/dev/s1", _SHA_C),
                relisten_index=1,
            )
            is None
        )

    def test_a_wave_the_reviewer_did_not_flag_yields_no_observation(self):
        step = _observe_step()
        assert (
            step.observe(
                sample_id="s1",
                wave_index=1,
                origin_packet=("fake/dev/s1", _SHA_C),
                relisten_index=0,
            )
            is None
        )

    def test_a_malformed_flag_fixture_is_refused(self):
        with pytest.raises(ObserveError, match="start/end/reason"):
            fixture_flag_source([{"sample_id": "s1", "spans": [{"start": 1.0}]}])
        with pytest.raises(ObserveError, match="unknown keys"):
            fixture_flag_source([{"sample_id": "s1", "spans": [], "margin": 1.0}])
        with pytest.raises(ObserveError, match="twice"):
            fixture_flag_source(
                [
                    {"sample_id": "s1", "spans": [], "wave_index": 0},
                    {"sample_id": "s1", "spans": [], "wave_index": 0},
                ]
            )

    def test_an_inverted_or_negative_span_is_refused(self):
        with pytest.raises(ObserveError, match="not a positive interval"):
            FlaggedSpan(5.0, 4.0, "inverted").validate()
        with pytest.raises(ObserveError, match="must be non-negative"):
            FlaggedSpan(-1.0, 4.0, "negative").validate()

    def test_a_flag_source_answering_the_wrong_sample_is_refused(self):
        step = ObserveStep(
            config=ObserveConfig(
                context_margin_seconds=0.5, max_relistens_per_sample=1
            ),
            flag_source=lambda _sample_id, _wave: ReviewFlags(
                sample_id="s2", spans=(FlaggedSpan(1.0, 2.0, "other sample"),)
            ),
            cutter=_FakeCutter(),
            media_facts=_MEDIA_FACTS,
        )
        with pytest.raises(ObserveError, match="answered sample"):
            step.observe(
                sample_id="s1",
                wave_index=0,
                origin_packet=("fake/dev/s1", _SHA_C),
                relisten_index=0,
            )


# --------------------------------------------------------------------------
# The byte chain: the replay loop's own re-cut, against real WAV bytes
# --------------------------------------------------------------------------


def _write_wav(path: Path, seconds: float, rate: int = 16000) -> None:
    import numpy as np
    import soundfile as sf

    samples = np.linspace(
        -0.4, 0.4, int(seconds * rate), endpoint=False, dtype="float32"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), samples, rate)


class TestSliceReCutter:
    def _world(self, tmp_path: Path):
        media_relpath = "datasets/earnings21/media/s1.wav"
        _write_wav(tmp_path / media_relpath, _MEDIA_SECONDS)
        registry = SliceRegistry(
            data_root=tmp_path,
            run_id="SAEA-E-TEST-observe",
            parent_facts={"s1": (media_relpath, _MEDIA_SECONDS)},
        )
        return media_relpath, registry

    def test_the_cut_is_registered_against_the_parent_media(self, tmp_path: Path):
        media_relpath, registry = self._world(tmp_path)
        encoded = []

        def encode_packet(record):
            encoded.append(record)
            return (
                f"packets/relisten/{record.iteration}",
                hashlib.sha256(record.sha256.encode("utf-8")).hexdigest(),
            )

        step = ObserveStep(
            config=ObserveConfig(
                context_margin_seconds=0.5, max_relistens_per_sample=2
            ),
            flag_source=fixture_flag_source(
                [
                    {
                        "sample_id": "s1",
                        "spans": [
                            {"start": 4.0, "end": 5.0, "reason": "low-confidence"}
                        ],
                    }
                ]
            ),
            cutter=SliceReCutter(
                registry=registry,
                data_root=tmp_path,
                encode_packet=encode_packet,
            ),
            media_facts={"s1": (media_relpath, _MEDIA_SECONDS)},
        )
        observation = step.observe(
            sample_id="s1",
            wave_index=0,
            origin_packet=("fake/dev/s1", _SHA_C),
            relisten_index=0,
        )
        assert observation is not None
        assert len(encoded) == 1
        record = encoded[0]
        assert record.parent_media_relpath == media_relpath
        assert record.start_seconds == pytest.approx(3.5)
        assert record.audio_seconds == pytest.approx(2.0)
        # Registered, and the written bytes still re-measure to the record.
        assert registry.lookup("s1", record.media_relpath) == record
        registry.verify_slice_bytes(record)
        written = (tmp_path / record.media_relpath).read_bytes()
        assert hashlib.sha256(written).hexdigest() == record.sha256
        assert observation.derivation.derived_packet_id == "packets/relisten/0"
        assert observation.provenance["parent_media_relpath"] == media_relpath

    def test_a_cut_of_an_unregistered_sample_can_never_be_sent(self, tmp_path: Path):
        media_relpath, registry = self._world(tmp_path)
        cutter = SliceReCutter(
            registry=registry,
            data_root=tmp_path,
            encode_packet=lambda record: ("p", _SHA_C),
        )
        step = ObserveStep(
            config=ObserveConfig(
                context_margin_seconds=0.5, max_relistens_per_sample=2
            ),
            flag_source=fixture_flag_source(
                [
                    {
                        "sample_id": "intruder",
                        "spans": [{"start": 1.0, "end": 2.0, "reason": "foreign"}],
                    }
                ]
            ),
            cutter=cutter,
            media_facts={"intruder": (media_relpath, _MEDIA_SECONDS)},
        )
        with pytest.raises(FrozenCoreError, match="not in the verified split"):
            step.observe(
                sample_id="intruder",
                wave_index=0,
                origin_packet=("fake/dev/s1", _SHA_C),
                relisten_index=0,
            )
