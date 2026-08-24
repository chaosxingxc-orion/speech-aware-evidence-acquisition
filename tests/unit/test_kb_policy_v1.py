"""C3: the first cross-task knowledge policy (owner-approved 2026-08-23
knowledge-plane baseline program; authority
``docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md`` section 5,
design basis section 1 -- the Q-K-V rulings).

Covers, stage by stage: multi-dimensional recall union with injected
vectors; the weighted-cosine/prior/agreement ranker's sort/hash contract and
weight sensitivity; the supply-filter fuser's percept admission and
coverage floor/cap; the full ``saea-kb-alpha-blend-v1`` controller
trajectory through ``rails.runner.run_speech_native_agent_loop`` with a fake
``CoreClient`` (the alpha-blend table across alpha in {0, 0.5, 1}, the
retain-primary safety default, and a task-independence proof that reruns
the SAME registered policy against a 5-label and a 150-label synthetic
label space); and registry idempotence.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.base import (
    AGENT_CONTROLLERS,
    KNOWLEDGE_FUSERS,
    KNOWLEDGE_RANKERS,
    Registry,
)
from speech_aware_evidence_acquisition.core.config import protocol_hash
from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
from speech_aware_evidence_acquisition.rails import kb_policy
from speech_aware_evidence_acquisition.rails.core_client import MockCoreClient
from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    QueryState,
    ValueBundle,
)
from speech_aware_evidence_acquisition.rails.obs import AudioRef, ObsPacket
from speech_aware_evidence_acquisition.rails.runner import (
    AgentRuntimeContext,
    _assert_agent_control_excludes_knowledge_payloads,
    _protected_knowledge_material,
    run_speech_native_agent_loop,
)
from speech_aware_evidence_acquisition.rails.task_adapter import TaskAdapter
from speech_aware_evidence_acquisition.rails.consumption import build_consumption_trace

_SHA_A = "a" * 64
_SHA_B = "b" * 64
_SHA_C = "c" * 64


def _plan(**overrides) -> ExecutionPlan:
    values = dict(
        run_id="SAEA-E-TEST-kb-policy-v1",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="rails-fake",
        split_role="discovery",
        split_identity_hash=_SHA_A,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash=protocol_hash("f" * 64, "bare-core", _SHA_A),
        attempt_id="attempt-kb-policy-v1-0001",
    )
    values.update(overrides)
    return ExecutionPlan(**values)


def _query_state(sample_id: str = "dev:s1") -> QueryState:
    return QueryState(
        query_id="q1",
        query_sample_id=sample_id,
        speech_packet_id="pkt",
        speech_packet_sha256=_SHA_C,
        use_split_identity_hash=_SHA_A,
    ).validate()


# ---------------------------------------------------------------------------
# Fake TaskAdapter/CoreClient plumbing (mirrors tests/unit/test_rails_runner.py)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _FakeSample:
    sample_id: str
    audio_ref: AudioRef
    audio_seconds: float


@dataclass
class _FakeAdapter(TaskAdapter):
    samples: tuple[_FakeSample, ...]

    def load_split(self, split_id):
        if split_id != "all":
            return ()
        return self.samples

    def build_task_contract(self, sample, obs: ObsPacket) -> str:
        return f"Identify the color referenced by {sample.sample_id}."

    def assemble_prompt(self, sample, supply):
        content = []
        if supply is not None:
            content.append({"type": "text", "text": supply.prompt_block})
        content.append({"type": "input_audio", "media_relpath": sample.audio_ref.path})
        return (
            {"role": "system", "content": "fake color task"},
            {"role": "user", "content": content},
        )

    def score(self, sample, response):
        return {"response_length": len(response)}

    def extract_consumption(self, sample, supply, response):
        return build_consumption_trace(span_id="full", supply=supply, response_text=response)


def _one_sample_adapter(sample_id: str = "s1") -> _FakeAdapter:
    return _FakeAdapter(
        samples=(
            _FakeSample(
                sample_id=sample_id,
                audio_ref=AudioRef(path=f"{sample_id}.wav", sha256=_SHA_A),
                audio_seconds=2.0,
            ),
        )
    )


def _evidence_aware_responder(direct_text: str, evidence_text: str):
    """Return ``direct_text`` for the zero-values contact and ``evidence_text``
    once the prompt carries a supplied knowledge value -- distinguished by
    inspecting the assembled ``messages`` (never by contact id/index, so
    this only relies on what ``rails.runner._agent_messages`` actually
    puts in the prompt)."""

    def responder(messages):
        content = messages[1]["content"]
        has_evidence = any(
            isinstance(part, dict) and part.get("knowledge_role") == "value"
            for part in content
        )
        return evidence_text if has_evidence else direct_text

    return responder


def _run_with_controller_factory(
    tmp_path: Path,
    *,
    snapshot: KnowledgeSnapshot,
    factory,
    responder,
    sample_id: str = "s1",
    max_contacts: int = 2,
):
    adapter = _one_sample_adapter(sample_id)
    client = MockCoreClient(responder=responder)
    registry = Registry("test kb-policy controller")
    registry.register(kb_policy.CONTROLLER_POLICY_ID, factory)

    summary = run_speech_native_agent_loop(
        data_root=tmp_path,
        plan=_plan(execution_profile="model-free-check"),
        adapter=adapter,
        core_client=client,
        split_id="all",
        knowledge_snapshot=snapshot,
        speech_packet_bindings={
            sample_id: {"packet_id": f"fake/dev/{sample_id}", "sha256": _SHA_C}
        },
        controller_policy_id=kb_policy.CONTROLLER_POLICY_ID,
        controller_registry=registry,
        max_contacts=max_contacts,
        slot_count=1,
        queue_depth=2,
        trace_sink=TraceBuffer(_plan().run_id),
        agent_executor_id="reference-trajectory-v1",
    )
    assert len(summary.results) == 1
    return summary.results[0]


def _adapter_with_task_contract(sample_id: str, task_contract: str) -> _FakeAdapter:
    """A one-sample ``_FakeAdapter`` whose ``build_task_contract`` returns a
    caller-chosen string -- an instance-attribute override, not a new
    dataclass field, so every other test that builds its own
    ``_FakeAdapter``/``_one_sample_adapter`` is untouched."""

    adapter = _one_sample_adapter(sample_id)
    adapter.build_task_contract = lambda sample, obs: task_contract  # type: ignore[method-assign]
    return adapter


def _run_alpha_blend_with_task_contract(
    tmp_path: Path,
    *,
    snapshot: KnowledgeSnapshot,
    factory,
    responder,
    task_contract: str,
    sample_id: str = "s1",
    max_contacts: int = 2,
):
    """Like :func:`_run_with_controller_factory`, but with an explicit
    ``task_contract`` and the ``MockCoreClient`` returned alongside the
    result, so a test can inspect exactly what was rendered for each
    contact (``client.calls[i]`` is the ``(messages, decoding_params)`` pair
    sent for contact index ``i``)."""

    adapter = _adapter_with_task_contract(sample_id, task_contract)
    client = MockCoreClient(responder=responder)
    registry = Registry("test kb-policy controller - task contract")
    registry.register(kb_policy.CONTROLLER_POLICY_ID, factory)

    summary = run_speech_native_agent_loop(
        data_root=tmp_path,
        plan=_plan(execution_profile="model-free-check"),
        adapter=adapter,
        core_client=client,
        split_id="all",
        knowledge_snapshot=snapshot,
        speech_packet_bindings={
            sample_id: {"packet_id": f"fake/dev/{sample_id}", "sha256": _SHA_C}
        },
        controller_policy_id=kb_policy.CONTROLLER_POLICY_ID,
        controller_registry=registry,
        max_contacts=max_contacts,
        slot_count=1,
        queue_depth=2,
        trace_sink=TraceBuffer(_plan().run_id),
        agent_executor_id="reference-trajectory-v1",
    )
    assert len(summary.results) == 1
    return summary.results[0], client


# ---------------------------------------------------------------------------
# Stage 1: multidim_recall
# ---------------------------------------------------------------------------


def _red_green_recall_snapshot() -> KnowledgeSnapshot:
    return KnowledgeSnapshot(
        snapshot_id="recall-test-v1",
        source_split_identity_hash=_SHA_B,
        source_sample_ids=("train:u1", "train:u2"),
        builder_policy_id="test-builder-v1",
        facets=(
            KeyFacet("facet:content:u1", "content", "text", "red apple", ("train:u1",)),
            KeyFacet("facet:content:u2", "content", "text", "green leaf", ("train:u2",)),
            KeyFacet("facet:label:red", "label", "text", "red", ("train:u1",)),
            KeyFacet("facet:label:green", "label", "text", "green", ("train:u2",)),
        ),
        values=(
            ValueBundle(
                value_id="value:u1",
                content="evidence u1",
                associated_facet_ids=("facet:content:u1", "facet:label:red"),
                source_sample_ids=("train:u1",),
                provenance_refs=("sample:train:u1",),
                task_target="red",
                prior_score=0.7,
            ),
            ValueBundle(
                value_id="value:u2",
                content="evidence u2",
                associated_facet_ids=("facet:content:u2", "facet:label:green"),
                source_sample_ids=("train:u2",),
                provenance_refs=("sample:train:u2",),
                task_target="green",
                prior_score=0.3,
            ),
        ),
    ).validate()


def test_multidim_recall_unions_cosine_and_prior_mass_dimensions():
    snapshot = _red_green_recall_snapshot()
    facet_vectors_by_id = {
        "facet:content:u1": {"content": (1.0, 0.0)},
        "facet:content:u2": {"content": (0.0, 1.0)},
    }

    recalled = kb_policy.multidim_recall(
        snapshot,
        query_vectors={"content": (0.0, 1.0)},
        facet_vectors=lambda facet_id: facet_vectors_by_id.get(facet_id, {}),
        top_k_per_dimension=5,
    )

    assert recalled["facet:content:u2"] == {"content": 1.0}
    assert "facet:content:u1" not in recalled  # cosine 0.0 is filtered out
    # label/prior dimensions recall by prior mass, without any vector at all.
    assert recalled["facet:label:red"] == {"label": 0.7}
    assert recalled["facet:label:green"] == {"label": 0.3}


def test_multidim_recall_ignores_a_dimension_with_no_query_vector():
    snapshot = _red_green_recall_snapshot()
    recalled = kb_policy.multidim_recall(
        snapshot,
        query_vectors={},  # no content vector injected at all
        facet_vectors=lambda facet_id: {"content": (1.0, 0.0)},
        top_k_per_dimension=5,
    )
    assert "facet:content:u1" not in recalled
    assert "facet:content:u2" not in recalled
    # prior-mass dimensions are unaffected by a missing query vector.
    assert recalled["facet:label:red"] == {"label": 0.7}


def test_multidim_recall_top_k_per_dimension_truncates_each_dimension_independently():
    facets = tuple(
        KeyFacet(
            f"facet:label:t{i}", "label", "text", f"target {i}", (f"train:u{i}",)
        )
        for i in range(5)
    )
    values = tuple(
        ValueBundle(
            value_id=f"value:u{i}",
            content=f"evidence {i}",
            associated_facet_ids=(f"facet:label:t{i}",),
            source_sample_ids=(f"train:u{i}",),
            provenance_refs=(f"sample:train:u{i}",),
            task_target=f"t{i}",
            prior_score=1.0 - i * 0.1,
        )
        for i in range(5)
    )
    snapshot = KnowledgeSnapshot(
        snapshot_id="recall-topk-test-v1",
        source_split_identity_hash=_SHA_B,
        source_sample_ids=tuple(f"train:u{i}" for i in range(5)),
        builder_policy_id="test-builder-v1",
        facets=facets,
        values=values,
    ).validate()

    recalled = kb_policy.multidim_recall(
        snapshot, query_vectors={}, facet_vectors=lambda facet_id: {}, top_k_per_dimension=2
    )
    # Highest prior mass wins: t0 (1.0) and t1 (0.9), never t2/t3/t4.
    assert set(recalled) == {"facet:label:t0", "facet:label:t1"}


def test_multidim_recall_rejects_a_non_positive_top_k():
    snapshot = _red_green_recall_snapshot()
    with pytest.raises(Exception, match="top_k_per_dimension"):
        kb_policy.multidim_recall(
            snapshot, query_vectors={}, facet_vectors=lambda facet_id: {}, top_k_per_dimension=0
        )


# ---------------------------------------------------------------------------
# Stage 2: the ranker
# ---------------------------------------------------------------------------


def test_ranker_sorts_score_desc_then_facet_id_asc_and_binds_hashes():
    recall_scores = {
        "facet:b": {"content": 0.5},
        "facet:a": {"content": 0.5},
        "facet:c": {"content": 0.9},
    }
    ranker = kb_policy.rank_wcos_prior_agree_factory(
        kb_policy.RankWeights(w_cos=1.0, w_prior=0.0, w_agree=0.0)
    )
    query_state = _query_state()

    result = ranker(snapshot_sha256=_SHA_B, query_state=query_state, recall_scores=recall_scores)

    assert result.ranking_policy_id == kb_policy.RANK_POLICY_ID
    assert [c.facet_id for c in result.candidates] == ["facet:c", "facet:a", "facet:b"]
    assert result.snapshot_sha256 == _SHA_B
    assert result.query_state_sha256 == query_state.content_hash()
    result.validate()  # contract-valid: sorted score desc, facet_id asc tie-break


def test_ranker_weight_sensitivity_moves_the_top_candidate():
    recall_scores = {
        "facet:cos-strong": {"content": 0.9},
        "facet:prior-strong": {"label": 0.9},
    }
    query_state = _query_state()
    cos_heavy = kb_policy.rank_wcos_prior_agree_factory(
        kb_policy.RankWeights(w_cos=1.0, w_prior=0.0, w_agree=0.0)
    )
    prior_heavy = kb_policy.rank_wcos_prior_agree_factory(
        kb_policy.RankWeights(w_cos=0.0, w_prior=1.0, w_agree=0.0)
    )

    cos_result = cos_heavy(
        snapshot_sha256=_SHA_B, query_state=query_state, recall_scores=recall_scores
    )
    prior_result = prior_heavy(
        snapshot_sha256=_SHA_B, query_state=query_state, recall_scores=recall_scores
    )

    assert cos_result.candidates[0].facet_id == "facet:cos-strong"
    assert prior_result.candidates[0].facet_id == "facet:prior-strong"


def test_ranker_agreement_term_rewards_multi_dimension_hits():
    recall_scores = {
        "facet:single-dim": {"content": 0.5},
        "facet:multi-dim": {"content": 0.5, "label": 0.5},
    }
    ranker = kb_policy.rank_wcos_prior_agree_factory(
        kb_policy.RankWeights(w_cos=0.0, w_prior=0.0, w_agree=1.0)
    )
    result = ranker(
        snapshot_sha256=_SHA_B, query_state=_query_state(), recall_scores=recall_scores
    )
    scores = {c.facet_id: c.score for c in result.candidates}
    assert scores["facet:multi-dim"] > scores["facet:single-dim"]


# ---------------------------------------------------------------------------
# Stage 3: the fuser
# ---------------------------------------------------------------------------


def _fuser_test_snapshot() -> KnowledgeSnapshot:
    def value(value_id, facet_ids, task_target, sample_id):
        return ValueBundle(
            value_id=value_id,
            content=f"evidence {value_id}",
            associated_facet_ids=facet_ids,
            source_sample_ids=(sample_id,),
            provenance_refs=(f"sample:{sample_id}",),
            task_target=task_target,
            prior_score=0.5,
        )

    facets = (
        KeyFacet("facet:content:a1", "content", "text", "a one", ("train:a1",)),
        KeyFacet("facet:content:a2", "content", "text", "a two", ("train:a2",)),
        KeyFacet("facet:content:b1", "content", "text", "b one", ("train:b1",)),
        KeyFacet("facet:content:c1", "content", "text", "c one", ("train:c1",)),
    )
    values = (
        value("value:a1", ("facet:content:a1",), "A", "train:a1"),
        value("value:a2", ("facet:content:a2",), "A", "train:a2"),
        value("value:b1", ("facet:content:b1",), "B", "train:b1"),
        value("value:c1", ("facet:content:c1",), "C", "train:c1"),
    )
    return KnowledgeSnapshot(
        snapshot_id="fuser-test-v1",
        source_split_identity_hash=_SHA_B,
        source_sample_ids=("train:a1", "train:a2", "train:b1", "train:c1"),
        builder_policy_id="test-builder-v1",
        facets=facets,
        values=values,
    ).validate()


def test_fuser_admits_by_tau_and_enforces_coverage_floor_and_cap():
    snapshot = _fuser_test_snapshot()
    recall_scores = {
        "facet:content:a1": {"content": 0.9},
        "facet:content:a2": {"content": 0.8},
        "facet:content:b1": {"content": 0.7},
        "facet:content:c1": {"content": 0.1},  # below tau: never admitted
    }
    query_state = _query_state()
    ranker = kb_policy.rank_wcos_prior_agree_factory(
        kb_policy.RankWeights(w_cos=1.0, w_prior=0.0, w_agree=0.0)
    )
    rank_result = ranker(
        snapshot_sha256=_SHA_B, query_state=query_state, recall_scores=recall_scores
    )

    # top_l=2 -> only the top-2 distinct task_targets (A, B) get any supply
    # at all; C is excluded both by rank AND by tau. c=1 -> at most one
    # value per task_target, even though A has two tau-admitted candidates.
    fuser = kb_policy.fuse_supplyfilter_factory(
        kb_policy.FuseKnobs(tau=0.2, m=10, c=1, top_l=2)
    )
    decision = fuser(
        snapshot=snapshot,
        snapshot_sha256=_SHA_B,
        query_state=query_state,
        rank_result=rank_result,
        recall_scores=recall_scores,
    )

    values_by_id = {value.value_id: value for value in snapshot.values}
    selected_targets = {values_by_id[v].task_target for v in decision.selected_value_ids}
    assert selected_targets == {"A", "B"}
    assert decision.selected_value_ids == ("value:a1", "value:b1")  # best-scoring per target
    decision.validate()


def test_fuser_cap_relaxed_admits_the_second_candidate_for_the_same_target():
    snapshot = _fuser_test_snapshot()
    recall_scores = {
        "facet:content:a1": {"content": 0.9},
        "facet:content:a2": {"content": 0.8},
        "facet:content:b1": {"content": 0.7},
        "facet:content:c1": {"content": 0.1},
    }
    query_state = _query_state()
    ranker = kb_policy.rank_wcos_prior_agree_factory(
        kb_policy.RankWeights(w_cos=1.0, w_prior=0.0, w_agree=0.0)
    )
    rank_result = ranker(
        snapshot_sha256=_SHA_B, query_state=query_state, recall_scores=recall_scores
    )
    fuser = kb_policy.fuse_supplyfilter_factory(
        kb_policy.FuseKnobs(tau=0.2, m=10, c=2, top_l=2)
    )
    decision = fuser(
        snapshot=snapshot,
        snapshot_sha256=_SHA_B,
        query_state=query_state,
        rank_result=rank_result,
        recall_scores=recall_scores,
    )
    assert decision.selected_value_ids == ("value:a1", "value:a2", "value:b1")


def test_fuser_selects_nothing_when_nothing_clears_tau():
    snapshot = _fuser_test_snapshot()
    recall_scores = {"facet:content:c1": {"content": 0.1}}
    query_state = _query_state()
    ranker = kb_policy.rank_wcos_prior_agree_factory(
        kb_policy.RankWeights(w_cos=1.0, w_prior=0.0, w_agree=0.0)
    )
    rank_result = ranker(
        snapshot_sha256=_SHA_B, query_state=query_state, recall_scores=recall_scores
    )
    fuser = kb_policy.fuse_supplyfilter_factory(
        kb_policy.FuseKnobs(tau=0.5, m=10, c=2, top_l=2)
    )
    decision = fuser(
        snapshot=snapshot,
        snapshot_sha256=_SHA_B,
        query_state=query_state,
        rank_result=rank_result,
        recall_scores=recall_scores,
    )
    assert decision.selected_value_ids == ()
    assert decision.supporting_facet_ids == ()
    decision.validate()


# ---------------------------------------------------------------------------
# Stage 4: the alpha-blend controller, full trajectory
# ---------------------------------------------------------------------------


def _red_green_controller_snapshot() -> KnowledgeSnapshot:
    facets = (
        KeyFacet("facet:content:red", "content", "text", "red content", ("train:red",)),
        KeyFacet("facet:content:green", "content", "text", "green content", ("train:green",)),
        KeyFacet("facet:label:red", "label", "text", "red", ("train:red",)),
        KeyFacet("facet:label:green", "label", "text", "green", ("train:green",)),
    )
    values = (
        ValueBundle(
            value_id="value:red",
            content="Evidence: the item is red.",
            associated_facet_ids=("facet:content:red", "facet:label:red"),
            source_sample_ids=("train:red",),
            provenance_refs=("sample:train:red",),
            task_target="red",
            prior_score=0.5,
        ),
        ValueBundle(
            value_id="value:green",
            content="Evidence: the item is green.",
            associated_facet_ids=("facet:content:green", "facet:label:green"),
            source_sample_ids=("train:green",),
            provenance_refs=("sample:train:green",),
            task_target="green",
            prior_score=0.5,
        ),
    )
    return KnowledgeSnapshot(
        snapshot_id="alpha-blend-test-v1",
        source_split_identity_hash=_SHA_B,
        source_sample_ids=("train:red", "train:green"),
        builder_policy_id="test-builder-v1",
        facets=facets,
        values=values,
    ).validate()


# The query vector is exactly aligned with green's content vector and
# orthogonal to red's -- red is therefore NEVER cosine-recalled at all
# (score 0.0 is filtered), so its only path into the blend is the
# direct-decode indicator term.
_RED_GREEN_FACET_VECTORS = {
    "facet:content:red": {"content": (1.0, 0.0)},
    "facet:content:green": {"content": (0.0, 1.0)},
}
_RED_GREEN_QUERY_VECTOR = {"content": (0.0, 1.0)}

_DIRECT_TEXT = "I believe the color is red."
_EVIDENCE_TEXT = "Considering the evidence, the color is green."


def _run_red_green(tmp_path: Path, *, alpha: float, query_vectors_by_sample=None):
    snapshot = _red_green_controller_snapshot()
    if query_vectors_by_sample is None:
        query_vectors_by_sample = {"s1": _RED_GREEN_QUERY_VECTOR}
    factory = kb_policy.make_kb_alpha_blend_controller_factory(
        snapshot=snapshot,
        query_vectors_by_sample=query_vectors_by_sample,
        facet_vectors=lambda facet_id: _RED_GREEN_FACET_VECTORS.get(facet_id, {}),
        rank_weights=kb_policy.RankWeights(w_cos=1.0, w_prior=0.0, w_agree=0.0),
        fuse_knobs=kb_policy.FuseKnobs(tau=0.5, m=10, c=1, top_l=2),
        alpha=alpha,
        top_k_per_dimension=10,
    )
    return _run_with_controller_factory(
        tmp_path,
        snapshot=snapshot,
        factory=factory,
        responder=_evidence_aware_responder(_DIRECT_TEXT, _EVIDENCE_TEXT),
    )


def test_alpha_zero_retains_the_direct_decode_response(tmp_path: Path):
    result = _run_red_green(tmp_path, alpha=0.0)
    assert [t.action_kind for t in result.transitions] == ["stop"]
    assert len(result.contacts) == 1
    assert result.final_response_text == _DIRECT_TEXT


def test_alpha_half_ties_and_the_evidence_decode_answer_breaks_the_tie(tmp_path: Path):
    # At alpha=0.5, red's flat direct-indicator half (0.5) exactly ties
    # green's fused half (0.5*1.0, since green is the sole recalled/fused
    # label) -- this exercises "tie-break by the evidence-decode answer"
    # explicitly, not just a clean outright win.
    result = _run_red_green(tmp_path, alpha=0.5)
    assert [t.action_kind for t in result.transitions] == ["acquire", "stop"]
    assert len(result.contacts) == 2
    assert result.final_response_text == _EVIDENCE_TEXT
    assert result.final_query_state.retrieved_value_ids == ("value:green",)


def test_alpha_one_lets_the_fused_evidence_win_outright(tmp_path: Path):
    result = _run_red_green(tmp_path, alpha=1.0)
    assert [t.action_kind for t in result.transitions] == ["acquire", "stop"]
    assert len(result.contacts) == 2
    assert result.final_response_text == _EVIDENCE_TEXT


def test_retain_primary_default_when_nothing_clears_percept_admission(tmp_path: Path):
    # No vectors injected at all (query_vectors_by_sample={}): the content
    # dimension never recalls anything, and label/prior-mass recall can
    # never clear the cosine-only percept-admission floor -- the fuser
    # selects nothing, and the controller retains the direct-decode
    # response as its documented safety default, in a single contact.
    result = _run_red_green(tmp_path, alpha=1.0, query_vectors_by_sample={})
    assert [t.action_kind for t in result.transitions] == ["stop"]
    assert len(result.contacts) == 1
    assert result.final_response_text == _DIRECT_TEXT


def test_default_registered_controller_is_a_safe_direct_decode_only_degenerate(
    tmp_path: Path,
):
    """The bare ``AGENT_CONTROLLERS`` global entry (module docstring
    "Registry vs. run-time binding"): snapshot-free, so it always performs
    exactly the direct-decode contact and stops."""

    snapshot = _red_green_controller_snapshot()
    adapter = _one_sample_adapter("s1")
    client = MockCoreClient(responder=lambda messages: _DIRECT_TEXT)

    summary = run_speech_native_agent_loop(
        data_root=tmp_path,
        plan=_plan(execution_profile="model-free-check"),
        adapter=adapter,
        core_client=client,
        split_id="all",
        knowledge_snapshot=snapshot,
        speech_packet_bindings={"s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}},
        controller_policy_id=kb_policy.CONTROLLER_POLICY_ID,
        # controller_registry omitted: uses the real global AGENT_CONTROLLERS
        # that kb_policy.register_kb_policy_v1() populated at import.
        max_contacts=2,
        slot_count=1,
        queue_depth=2,
        trace_sink=TraceBuffer(_plan().run_id),
        agent_executor_id="reference-trajectory-v1",
    )
    result = summary.results[0]
    assert len(result.contacts) == 1
    assert result.final_response_text == _DIRECT_TEXT


# ---------------------------------------------------------------------------
# Task independence: the SAME policy over a 5-label and a 150-label space
# ---------------------------------------------------------------------------


def _label_space_snapshot(n_labels: int):
    labels = [f"lbl{i:04d}" for i in range(n_labels)]
    facets: list[KeyFacet] = []
    values: list[ValueBundle] = []
    facet_vectors: dict[str, dict[str, tuple[float, ...]]] = {}
    for index, label in enumerate(labels):
        sample_id = f"train:{label}"
        content_fid = f"facet:content:{label}"
        label_fid = f"facet:label:{label}"
        facets.append(
            KeyFacet(content_fid, "content", "text", f"utterance about {label}", (sample_id,))
        )
        facets.append(KeyFacet(label_fid, "label", "text", label, (sample_id,)))
        vector = [0.0] * n_labels
        vector[index] = 1.0
        facet_vectors[content_fid] = {"content": tuple(vector)}
        values.append(
            ValueBundle(
                value_id=f"value:{label}",
                content=f"Evidence for {label}.",
                associated_facet_ids=(content_fid, label_fid),
                source_sample_ids=(sample_id,),
                provenance_refs=(f"sample:{sample_id}",),
                task_target=label,
                prior_score=1.0 / n_labels,
            )
        )
    snapshot = KnowledgeSnapshot(
        snapshot_id=f"label-space-{n_labels}",
        source_split_identity_hash=_SHA_B,
        source_sample_ids=tuple(f"train:{label}" for label in labels),
        builder_policy_id="test-builder-v1",
        facets=tuple(facets),
        values=tuple(values),
    ).validate()
    return snapshot, labels, facet_vectors


def _run_label_space(tmp_path: Path, n_labels: int, target_index: int):
    snapshot, labels, facet_vectors = _label_space_snapshot(n_labels)
    target_label = labels[target_index]
    other_label = labels[(target_index + 1) % n_labels]
    query_vector = [0.0] * n_labels
    query_vector[target_index] = 1.0

    factory = kb_policy.make_kb_alpha_blend_controller_factory(
        snapshot=snapshot,
        query_vectors_by_sample={"s1": {"content": tuple(query_vector)}},
        facet_vectors=lambda facet_id: facet_vectors.get(facet_id, {}),
        rank_weights=kb_policy.RankWeights(w_cos=1.0, w_prior=0.0, w_agree=0.0),
        fuse_knobs=kb_policy.FuseKnobs(tau=0.5, m=5, c=1, top_l=1),
        alpha=1.0,
        top_k_per_dimension=max(n_labels, 1),
    )
    result = _run_with_controller_factory(
        tmp_path,
        snapshot=snapshot,
        factory=factory,
        responder=_evidence_aware_responder(
            f"My guess is {other_label}.", f"The evidence indicates {target_label}."
        ),
    )
    return result, target_label


@pytest.mark.parametrize("n_labels", [5, 150])
def test_same_policy_is_task_independent_across_label_space_size(
    tmp_path: Path, n_labels: int
):
    result, target_label = _run_label_space(tmp_path, n_labels, target_index=n_labels - 1)
    assert [t.action_kind for t in result.transitions] == ["acquire", "stop"]
    assert result.final_query_state.retrieved_value_ids == (f"value:{target_label}",)
    assert result.final_response_text == f"The evidence indicates {target_label}."


# ---------------------------------------------------------------------------
# Prompt-fit regression (docs/checks/speech-aware-evidence-acquisition/
# 2026-08-24-dev100-c3-prompt-fit): the evidence-decode contact's
# instruction must reference the task contract that
# ``rails.runner._agent_messages`` already places in the system message of
# every contact, never re-render it a second time.
# ---------------------------------------------------------------------------


def test_evidence_contact_instruction_does_not_repeat_the_task_contract(tmp_path: Path):
    """A long sentinel task contract must appear exactly once across the
    whole rendered request for the evidence-decode contact -- in the system
    message ``rails.runner._agent_messages`` builds for every contact --
    never again inside the evidence contact's own control instruction. This
    is the exact duplication the DEV-100 C3 prompt-fit receipt measured at
    ~1,957 tokens (5,494 characters) of the worst-case 7,773-token
    envelope."""

    sentinel_contract = "SENTINEL-TASK-CONTRACT-" + ("Q" * 2000)
    snapshot = _red_green_controller_snapshot()
    factory = kb_policy.make_kb_alpha_blend_controller_factory(
        snapshot=snapshot,
        query_vectors_by_sample={"s1": _RED_GREEN_QUERY_VECTOR},
        facet_vectors=lambda facet_id: _RED_GREEN_FACET_VECTORS.get(facet_id, {}),
        rank_weights=kb_policy.RankWeights(w_cos=1.0, w_prior=0.0, w_agree=0.0),
        fuse_knobs=kb_policy.FuseKnobs(tau=0.5, m=10, c=1, top_l=2),
        alpha=1.0,
        top_k_per_dimension=10,
    )

    result, client = _run_alpha_blend_with_task_contract(
        tmp_path,
        snapshot=snapshot,
        factory=factory,
        responder=_evidence_aware_responder(_DIRECT_TEXT, _EVIDENCE_TEXT),
        task_contract=sentinel_contract,
    )

    assert [record.plan.contact_id for record in result.contacts] == [
        "direct-decode",
        "evidence-decode",
    ]
    evidence_instruction = result.contacts[1].plan.instruction
    evidence_messages, _decoding_params = client.calls[1]
    assert len(evidence_messages) == 2
    system_message = evidence_messages[0]
    assert system_message["role"] == "system"

    # The sentinel appears in the system message every contact already
    # carries ...
    assert sentinel_contract in str(system_message["content"])
    # ... and never again inside the evidence contact's own instruction ...
    assert sentinel_contract not in evidence_instruction
    # ... so across the whole rendered request for this contact (the
    # message list plus the separately-carried CONTROL instruction) it
    # appears exactly once, not twice.
    rendered = "".join(str(message["content"]) for message in evidence_messages)
    rendered += evidence_instruction
    assert rendered.count(sentinel_contract) == 1


_WORST_CASE_INSTRUCTION_CHAR_BOUND = 500  # generous vs. the ~175-char fixed instruction


def _worst_case_fusion_snapshot(
    *, n_targets: int, values_per_target: int, text_length: int
) -> KnowledgeSnapshot:
    """A synthetic snapshot shaped like the prompt-fit receipt's worst case
    (``fusion_m=5``, ``fusion_c=2``, ``fusion_top_l=3`` -> up to 6 selected
    values): every content facet cosine-matches the query exactly, so every
    value across ``n_targets`` distinct task_targets clears percept
    admission and is selected up to ``values_per_target`` each -- with
    facet/value text as long as the receipt's own p99 lengths."""

    long_facet_text = "F" * text_length
    long_value_text = "V" * text_length
    facets: list[KeyFacet] = []
    values: list[ValueBundle] = []
    for index in range(n_targets):
        target = f"target{index}"
        content_fid = f"facet:content:{target}"
        label_fid = f"facet:label:{target}"
        facets.append(
            KeyFacet(content_fid, "content", "text", long_facet_text, (f"train:{target}",))
        )
        facets.append(KeyFacet(label_fid, "label", "text", target, (f"train:{target}",)))
        for value_index in range(values_per_target):
            values.append(
                ValueBundle(
                    value_id=f"value:{target}:{value_index}",
                    content=long_value_text,
                    associated_facet_ids=(content_fid, label_fid),
                    source_sample_ids=(f"train:{target}",),
                    provenance_refs=(f"sample:train:{target}",),
                    task_target=target,
                    prior_score=0.5,
                )
            )
    return KnowledgeSnapshot(
        snapshot_id="worst-case-fusion-v1",
        source_split_identity_hash=_SHA_B,
        source_sample_ids=tuple(f"train:target{index}" for index in range(n_targets)),
        builder_policy_id="test-builder-v1",
        facets=tuple(facets),
        values=tuple(values),
    ).validate()


def test_evidence_contact_instruction_is_bounded_for_a_worst_case_fusion(tmp_path: Path):
    """Even at the receipt's worst-case fusion shape (6 selected values,
    long facet/value text, and a large task contract) the evidence-decode
    instruction stays a small, fixed-size reference: it must never grow
    with the fused evidence or with the task contract size."""

    snapshot = _worst_case_fusion_snapshot(n_targets=3, values_per_target=2, text_length=1600)
    large_task_contract = "TASK-CONTRACT-" + ("C" * 6000)  # ~ the receipt's 5,424 characters
    factory = kb_policy.make_kb_alpha_blend_controller_factory(
        snapshot=snapshot,
        query_vectors_by_sample={"s1": {"content": (1.0,)}},
        facet_vectors=lambda facet_id: {"content": (1.0,)},
        rank_weights=kb_policy.RankWeights(w_cos=1.0, w_prior=0.0, w_agree=0.0),
        fuse_knobs=kb_policy.FuseKnobs(tau=0.5, m=10, c=2, top_l=3),
        alpha=1.0,
        top_k_per_dimension=10,
    )
    # A direct answer that matches none of the label texts ("target0" etc.)
    # keeps direct_label=None, so the blend always dispatches evidence-decode
    # (never the retain-primary degenerate stop), regardless of tie shape.
    result, _client = _run_alpha_blend_with_task_contract(
        tmp_path,
        snapshot=snapshot,
        factory=factory,
        responder=_evidence_aware_responder("I have no idea.", "The evidence settles it."),
        task_contract=large_task_contract,
    )

    assert [t.action_kind for t in result.transitions] == ["acquire", "stop"]
    fusion_decision = result.waves[0].fusion_decision
    assert fusion_decision is not None
    assert len(fusion_decision.selected_value_ids) == 6  # 3 targets x 2 values: the worst case

    evidence_instruction = result.contacts[1].plan.instruction
    assert len(evidence_instruction) < _WORST_CASE_INSTRUCTION_CHAR_BOUND
    assert large_task_contract not in evidence_instruction


# ---------------------------------------------------------------------------
# DEV-100 round-0 guard-trip regression (docs/checks/speech-aware-evidence-
# acquisition/2026-08-24-dev100-round0/round0-attempt1-abort.json, takeoff
# 3): the DIRECT contact's instruction re-rendered the same task contract
# ``rails.runner._agent_messages`` already places in the system message of
# every contact, and TRAIN content-facet representations that are >=8-char
# substrings of the real SLURP roster tripped
# ``rails.runner._assert_agent_control_excludes_knowledge_payloads`` on the
# very first wave. This is the same duplication class amendment 5b remedy 1
# fixed for the EVIDENCE contact (commit 72096bad), now applied to DIRECT.
# ---------------------------------------------------------------------------

_DIRECT_INSTRUCTION_CHAR_BOUND = 300  # generous vs. the ~135-char fixed instruction


def test_direct_contact_instruction_does_not_repeat_the_task_contract(tmp_path: Path):
    """A long sentinel task contract must appear exactly once across the
    whole rendered request for the direct-decode contact -- in the system
    message ``rails.runner._agent_messages`` builds for every contact --
    never again inside the direct contact's own control instruction; the
    instruction itself must also stay a small, fixed-size reference
    regardless of contract size (mirrors
    ``test_evidence_contact_instruction_does_not_repeat_the_task_contract``
    for the DIRECT contact)."""

    sentinel_contract = "SENTINEL-TASK-CONTRACT-" + ("Q" * 2000)
    snapshot = _red_green_controller_snapshot()
    factory = kb_policy.make_kb_alpha_blend_controller_factory(
        snapshot=snapshot,
        query_vectors_by_sample={"s1": _RED_GREEN_QUERY_VECTOR},
        facet_vectors=lambda facet_id: _RED_GREEN_FACET_VECTORS.get(facet_id, {}),
        rank_weights=kb_policy.RankWeights(w_cos=1.0, w_prior=0.0, w_agree=0.0),
        fuse_knobs=kb_policy.FuseKnobs(tau=0.5, m=10, c=1, top_l=2),
        alpha=1.0,
        top_k_per_dimension=10,
    )

    result, client = _run_alpha_blend_with_task_contract(
        tmp_path,
        snapshot=snapshot,
        factory=factory,
        responder=_evidence_aware_responder(_DIRECT_TEXT, _EVIDENCE_TEXT),
        task_contract=sentinel_contract,
    )

    assert result.contacts[0].plan.contact_id == "direct-decode"
    direct_instruction = result.contacts[0].plan.instruction
    direct_messages, _decoding_params = client.calls[0]
    assert len(direct_messages) == 2
    system_message = direct_messages[0]
    assert system_message["role"] == "system"

    # The sentinel appears in the system message every contact already
    # carries ...
    assert sentinel_contract in str(system_message["content"])
    # ... and never again inside the direct contact's own instruction ...
    assert sentinel_contract not in direct_instruction
    # ... so across the whole rendered request for this contact (the
    # message list plus the separately-carried CONTROL instruction) it
    # appears exactly once, not twice.
    rendered = "".join(str(message["content"]) for message in direct_messages)
    rendered += direct_instruction
    assert rendered.count(sentinel_contract) == 1

    # The instruction itself never grows with the contract size.
    assert len(direct_instruction) < _DIRECT_INSTRUCTION_CHAR_BOUND


def test_direct_contact_instruction_passes_the_protected_knowledge_guard_reproducing_round0(
    tmp_path: Path,
):
    """Reproduce the round-0 takeoff-3 trip shape: a synthetic snapshot
    whose content-facet representation ("temperature") is a >=8-char
    substring of the task contract, exactly like the real SLURP roster's
    content-facet texts were substrings of the registered chain's
    re-rendered contract. The OLD-style instruction (task contract
    re-rendered verbatim, the pre-fix construction) trips
    ``rails.runner._assert_agent_control_excludes_knowledge_payloads``; the
    FIXED reference-only instruction this module now builds clears the same
    guard call on contact 0."""

    task_contract = (
        "Classify the caller's intent. Roster fillers include temperature, "
        "calendar, and freezing, drawn from the SLURP ontology roster."
    )
    snapshot = KnowledgeSnapshot(
        snapshot_id="round0-guard-repro-v1",
        source_split_identity_hash=_SHA_B,
        source_sample_ids=("train:temp",),
        builder_policy_id="test-builder-v1",
        facets=(
            KeyFacet(
                "facet:content:temp", "content", "text", "temperature", ("train:temp",)
            ),
        ),
        values=(
            ValueBundle(
                value_id="value:temp",
                content="Evidence: the reading is temperature-related.",
                associated_facet_ids=("facet:content:temp",),
                source_sample_ids=("train:temp",),
                provenance_refs=("sample:train:temp",),
                task_target="temp",
                prior_score=0.5,
            ),
        ),
    ).validate()
    protected = _protected_knowledge_material(snapshot)
    # Precondition reproducing the round-0 trip: the facet representation
    # really is a substring of the task contract text.
    assert any(material in task_contract.casefold() for material in protected)

    controller = kb_policy.KbAlphaBlendController(
        snapshot=snapshot,
        query_vectors={},
        facet_vectors=lambda facet_id: {},
        normalizer=kb_policy.default_label_normalizer,
        ranker=kb_policy.rank_wcos_prior_agree_factory(
            kb_policy.RankWeights(w_cos=0.0, w_prior=0.0, w_agree=0.0)
        ),
        fuser=kb_policy.fuse_supplyfilter_factory(
            kb_policy.FuseKnobs(tau=1.0, m=1, c=1, top_l=1)
        ),
        alpha=0.5,
        top_k_per_dimension=1,
    )
    context = AgentRuntimeContext(
        sample_id="dev:round0-guard-repro",
        knowledge_snapshot_sha256=snapshot.content_hash(),
        catalog_facet_ids=tuple(facet.facet_id for facet in snapshot.facets),
        catalog_value_ids=(),
        query_state=_query_state("dev:round0-guard-repro"),
        task_contract=task_contract,
        agent_states=(),
        prior_response_sha256s=(),
        contact_index=0,
    )

    # The OLD (pre-fix) construction -- task_contract re-rendered verbatim
    # into the instruction -- reproduces the exact takeoff-3 trip.
    old_style_plan = replace(
        controller.initial_contact(context),
        instruction=(
            f"{task_contract}\n"
            "Answer using only the speech query; no external knowledge has "
            "been supplied yet."
        ),
    )
    with pytest.raises(Exception, match="frozen knowledge key/value payloads"):
        _assert_agent_control_excludes_knowledge_payloads(old_style_plan, protected)

    # The FIXED instruction -- this module's real initial_contact -- is a
    # pure reference and clears the same guard call cleanly.
    fixed_plan = controller.initial_contact(context)
    assert task_contract not in fixed_plan.instruction
    _assert_agent_control_excludes_knowledge_payloads(fixed_plan, protected)  # must not raise


# ---------------------------------------------------------------------------
# Registry idempotence
# ---------------------------------------------------------------------------


def test_register_kb_policy_v1_is_idempotent():
    assert kb_policy.RANK_POLICY_ID in KNOWLEDGE_RANKERS.names()
    assert kb_policy.FUSE_POLICY_ID in KNOWLEDGE_FUSERS.names()
    assert kb_policy.CONTROLLER_POLICY_ID in AGENT_CONTROLLERS.names()

    rank_entry_before = KNOWLEDGE_RANKERS.resolve(kb_policy.RANK_POLICY_ID)
    fuse_entry_before = KNOWLEDGE_FUSERS.resolve(kb_policy.FUSE_POLICY_ID)
    controller_entry_before = AGENT_CONTROLLERS.resolve(kb_policy.CONTROLLER_POLICY_ID)

    kb_policy.register_kb_policy_v1()  # must not raise CoreError on re-registration
    kb_policy.register_kb_policy_v1()

    assert KNOWLEDGE_RANKERS.resolve(kb_policy.RANK_POLICY_ID) is rank_entry_before
    assert KNOWLEDGE_FUSERS.resolve(kb_policy.FUSE_POLICY_ID) is fuse_entry_before
    assert AGENT_CONTROLLERS.resolve(kb_policy.CONTROLLER_POLICY_ID) is controller_entry_before


# ---------------------------------------------------------------------------
# Config file
# ---------------------------------------------------------------------------


def test_default_policy_config_loads_and_carries_dev_tuned_only_semantics():
    config = kb_policy.load_policy_config()
    assert config["schema"] == "saea-kb-policy-v1"
    assert isinstance(config["knob_semantics"], str) and config["knob_semantics"].strip()
    weights = kb_policy.rank_weights_from_config(config)
    knobs = kb_policy.fuse_knobs_from_config(config)
    assert weights.validate() is weights
    assert knobs.validate() is knobs
    alpha = kb_policy.alpha_from_config(config)
    assert 0.0 <= alpha <= 1.0
    top_k = kb_policy.top_k_per_dimension_from_config(config)
    assert top_k > 0
