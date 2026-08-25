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

Also covers the 2026-08-25 cross-dimension commensurability repair (owner
ruling; authority
``docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-g1/README.md``
section "CORRECTION"): that :func:`~.kb_policy._dimension_scales` is an exact
identity wherever a dimension already respects its bound -- asserted both on
synthetic SLURP-shaped scores and by replaying the SEALED DEV-1000 BLEND
records through the repaired path -- and that on an Audio2Tool-shaped
knowledge base, where prior mass is unbounded, content facets get their
admission window back and the supply path fires.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
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
    RankedFacet,
    RankResult,
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
# Stage 2 (repair): cross-dimension commensurability
#
# The ranker used to sum a cosine bounded by 1 with an UNBOUNDED prior mass
# inside one weighted score. ``rails.kb_policy._dimension_scales`` now divides
# every dimension by ``max(1.0, sup_d)`` over the recalled candidate set, so
# every term lands in the same [0, 1] range before the weights apply. These
# tests pin the three properties the repair has to have: it is an EXACT
# identity wherever a dimension already respects its bound (the SLURP locked
# cell), it shrinks ONLY a dimension that has escaped it (Audio2Tool), and on
# the escaped carrier content facets get their admission window back.
#
# Authority for the defect and the required proof:
# ``docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-g1/README.md``
# section "CORRECTION" (owner ruling, 2026-08-25).
# ---------------------------------------------------------------------------

# The knob table the DEV-1000 baseline is LOCKED at
# (``configs/policy/kb-policy-v1-dev100.json``), restated here so the repair's
# guarantees are asserted at the operating point that actually flies. This is
# a READ of the locked cell; nothing here changes it.
_LOCKED_WEIGHTS = kb_policy.RankWeights(w_cos=0.5, w_prior=0.3, w_agree=0.2)
_LOCKED_FUSE = kb_policy.FuseKnobs(tau=0.65, m=5, c=2, top_l=3)
_LOCKED_TOP_K = 5

# The prior masses ``multidim_recall`` actually returns on the pinned
# Audio2Tool snapshot ``ec2f9ec4...``: its top ``top_k_per_dimension = 5``
# facet masses per prior-mass dimension, measured rather than invented. There
# ``prior_score = tool_total / category_total`` counts a tool's rows across
# every domain against ONE (domain, category) denominator, so the ratio is not
# nested, is not a probability, and 193 of the snapshot's 12,601 values exceed
# 1. SLURP's own sup, on the pinned TRAIN snapshot ``e27b2745...``, is exactly
# 1.0 -- which is the whole reason the defect stayed invisible.
_A2T_PRIOR_MASSES = (
    4.1,
    2.493827160493827,
    1.956043956043956,
    1.5274725274725274,
    1.1908396946564885,
)
# Best content-facet cosine per trajectory over G1's 104 flown trajectories
# ranged 0.7594 to 0.9572 (G1 read section 10.5) -- every one of them clears
# ``tau = 0.65``, which is why the zero-dispatch was never a recall failure.
_A2T_CONTENT_COSINES = (0.9572, 0.9012, 0.8433, 0.7981, 0.7594)


def _pre_repair_ranking(recall_scores, weights) -> list[tuple[str, float]]:
    """The ranker's EXACT pre-repair expression, transcribed.

    Kept verbatim (raw per-dimension scores, no normalisation) so the tests
    below can assert bit-for-bit equality against it in the bounded regime and
    show the eviction it produced in the unbounded one. If this ever stops
    matching the shipped ranker in the bounded regime, the locked baseline has
    moved and the identity claim is dead.
    """

    dims_total = len({dim for scores in recall_scores.values() for dim in scores})
    ranked: list[tuple[str, float]] = []
    for facet_id, dim_scores in recall_scores.items():
        cosine_scores = [
            score
            for dim, score in dim_scores.items()
            if dim not in kb_policy.PRIOR_MASS_DIMENSIONS
        ]
        prior_scores = [
            score
            for dim, score in dim_scores.items()
            if dim in kb_policy.PRIOR_MASS_DIMENSIONS
        ]
        max_cosine = max(cosine_scores) if cosine_scores else 0.0
        max_prior = max(prior_scores) if prior_scores else 0.0
        agreement = len(dim_scores) / dims_total if dims_total else 0.0
        ranked.append(
            (
                facet_id,
                weights.w_cos * max_cosine
                + weights.w_prior * max_prior
                + weights.w_agree * agreement,
            )
        )
    ranked.sort(key=lambda item: (-item[1], item[0]))
    return ranked


def _ranked(result) -> list[tuple[str, float]]:
    return [(candidate.facet_id, candidate.score) for candidate in result.candidates]


def test_dimension_scales_are_the_identity_when_every_dimension_respects_its_bound():
    # SLURP's regime: cosine <= 1 as a theorem, prior mass <= 1 because the
    # builder's ratio is genuinely nested. Every divisor is exactly 1.0.
    recall_scores = {
        "facet:content:a": {"content": 0.9007},
        "facet:content:b": {"content": 0.0001},
        "facet:label:x": {"label": 1.0},
        "facet:prior:x": {"prior": 0.0189},
    }
    assert kb_policy._dimension_scales(recall_scores) == {
        "content": 1.0,
        "label": 1.0,
        "prior": 1.0,
    }


def test_dimension_scales_shrink_only_the_dimension_that_escaped_its_bound():
    recall_scores = {
        "facet:content:a": {"content": 0.9572},
        "facet:label:t0": {"label": 4.1},
        "facet:prior:t0": {"prior": 4.1},
        "facet:prior:t4": {"prior": 1.1908396946564885},
    }
    scales = kb_policy._dimension_scales(recall_scores)
    # The bounded dimension is untouched; the two escaped ones are divided by
    # their own observed supremum, never by a shared or a tuned constant.
    assert scales == {"content": 1.0, "label": 4.1, "prior": 4.1}


def test_dimension_scales_never_amplify_and_never_divide_by_zero():
    # A degenerate recall (an all-zero or negative dimension) must not blow up
    # or flip a sign: the floor at 1.0 makes every divisor >= 1 by
    # construction, so the map can only ever shrink.
    scales = kb_policy._dimension_scales(
        {"facet:a": {"content": 0.0, "label": -3.0}}
    )
    assert scales == {"content": 1.0, "label": 1.0}


def test_ranker_is_bit_identical_to_the_pre_repair_form_in_the_slurp_regime():
    """THE LOCKED-CELL IDENTITY, on synthetic SLURP-shaped scores.

    Every dimension respects its bound (the prior dimension even attains it
    exactly, as SLURP's TRAIN snapshot does), so every divisor is 1.0, IEEE-754
    division by 1.0 is exact, and the whole candidate list -- ordering AND
    float scores -- must be what the pre-repair ranker produced. Equality is
    exact ``==`` on floats, deliberately: an approximate match would not prove
    a byte-identical baseline.
    """

    recall_scores = {
        "facet:content:u1": {"content": 0.9007060012340951},
        "facet:content:u2": {"content": 0.7412},
        "facet:content:u3": {"content": 0.6501, "speaker": 0.31},
        "facet:label:alarm_query": {"label": 1.0},
        "facet:label:iot_hue_lightoff": {"label": 0.4517},
        "facet:prior:alarm_query": {"prior": 1.0},
        "facet:prior:iot_hue_lightoff": {"prior": 0.018957345971563982},
    }
    ranker = kb_policy.rank_wcos_prior_agree_factory(_LOCKED_WEIGHTS)

    result = ranker(
        snapshot_sha256=_SHA_B, query_state=_query_state(), recall_scores=recall_scores
    )

    assert _ranked(result) == _pre_repair_ranking(recall_scores, _LOCKED_WEIGHTS)
    result.validate()


@pytest.mark.parametrize(
    "weights",
    [
        _LOCKED_WEIGHTS,
        kb_policy.RankWeights(w_cos=1.0, w_prior=0.0, w_agree=0.0),
        kb_policy.RankWeights(w_cos=0.0, w_prior=1.0, w_agree=0.0),
        kb_policy.RankWeights(w_cos=0.2, w_prior=0.7, w_agree=0.1),
    ],
)
def test_ranker_identity_in_the_bounded_regime_holds_for_any_weighting(weights):
    # The identity is a property of the normalisation, not of one weight
    # vector: with every divisor at 1.0 the repair cannot move a score
    # whatever the weights are.
    recall_scores = {
        "facet:content:a": {"content": 0.88, "speaker": 0.5},
        "facet:content:b": {"content": 1.0},
        "facet:label:x": {"label": 1.0},
        "facet:prior:x": {"prior": 0.25},
        "facet:prior:y": {"prior": 0.75},
    }
    ranker = kb_policy.rank_wcos_prior_agree_factory(weights)

    result = ranker(
        snapshot_sha256=_SHA_B, query_state=_query_state(), recall_scores=recall_scores
    )

    assert _ranked(result) == _pre_repair_ranking(recall_scores, weights)


def _a2t_shaped_snapshot() -> KnowledgeSnapshot:
    """Audio2Tool's KB SHAPE: one content/label/prior facet triple per tool.

    Mirrors ``rails.knowledge_build_a2t``: each value is associated with its
    tool's content facet AND its label and prior facets, so the label/prior
    facets recall by that value's ``prior_score`` -- which on this carrier is
    an unbounded ratio, here the five masses actually measured on the pinned
    snapshot.
    """

    facets: list[KeyFacet] = []
    values: list[ValueBundle] = []
    for index, mass in enumerate(_A2T_PRIOR_MASSES):
        sample_id = f"train:t{index}"
        facets.extend(
            (
                KeyFacet(f"facet:content:t{index}", "content", "text", f"exemplar {index}", (sample_id,)),
                KeyFacet(f"facet:label:t{index}", "label", "text", f"tool_{index}", (sample_id,)),
                KeyFacet(f"facet:prior:t{index}", "prior", "text", f"prior tool_{index}", (sample_id,)),
            )
        )
        values.append(
            ValueBundle(
                value_id=f"value:t{index}",
                content=f"tool_{index} invocation exemplar",
                associated_facet_ids=(
                    f"facet:content:t{index}",
                    f"facet:label:t{index}",
                    f"facet:prior:t{index}",
                ),
                source_sample_ids=(sample_id,),
                provenance_refs=(f"sample:{sample_id}",),
                task_target=f"tool_{index}",
                prior_score=mass,
            )
        )
    return KnowledgeSnapshot(
        snapshot_id="a2t-shaped-v1",
        source_split_identity_hash=_SHA_B,
        source_sample_ids=tuple(f"train:t{i}" for i in range(len(_A2T_PRIOR_MASSES))),
        builder_policy_id="test-builder-a2t-shaped-v1",
        facets=tuple(facets),
        values=tuple(values),
    ).validate()


def _a2t_shaped_recall(snapshot: KnowledgeSnapshot):
    """Real ``multidim_recall`` over the A2T-shaped snapshot.

    The content query vector is the unit x axis and each content facet's
    vector is ``(c, sqrt(1 - c^2))``, so its cosine is the intended ``c``. The
    prior-mass side is NOT injected: it is derived by ``multidim_recall``
    itself from the snapshot's own ``prior_score`` values, which is the whole
    point -- the unbounded numbers arrive through the production path.
    """

    query_vector = (1.0, 0.0)
    vectors = {
        f"facet:content:t{index}": {
            "content": (cosine, math.sqrt(max(0.0, 1.0 - cosine * cosine)))
        }
        for index, cosine in enumerate(_A2T_CONTENT_COSINES)
    }
    return kb_policy.multidim_recall(
        snapshot,
        {"content": query_vector},
        lambda facet_id: vectors.get(facet_id, {}),
        _LOCKED_TOP_K,
    )


def test_unbounded_prior_mass_no_longer_evicts_content_from_the_admission_window():
    """THE A2T REGRESSION: the top-``m`` window is content's again.

    Pre-repair this is the measured G1 outcome -- ``w_prior * 4.1 = 1.23``
    against a best ``w_cos * 0.9572 = 0.4786``, so the ten prior-mass facets
    filled the whole ``m = 5`` window and ZERO content facets were admitted on
    any of 104 trajectories. Both halves are asserted here: that the pre-repair
    expression really does evict (so this test would fail if the defect came
    back), and that the shipped ranker does not.
    """

    snapshot = _a2t_shaped_snapshot()
    recall_scores = _a2t_shaped_recall(snapshot)
    content_ids = {f"facet:content:t{i}" for i in range(len(_A2T_CONTENT_COSINES))}
    # Recall itself was never the problem: every dimension recalled its five.
    assert len(recall_scores) == 3 * len(_A2T_CONTENT_COSINES)
    assert all(
        max(recall_scores[facet_id].values()) >= _LOCKED_FUSE.tau
        for facet_id in content_ids
    )

    pre_repair = _pre_repair_ranking(recall_scores, _LOCKED_WEIGHTS)
    evicted = [facet_id for facet_id, _score in pre_repair[: _LOCKED_FUSE.m]]
    assert not (set(evicted) & content_ids), "the defect this test guards is gone from the fixture"

    ranker = kb_policy.rank_wcos_prior_agree_factory(_LOCKED_WEIGHTS)
    result = ranker(
        snapshot_sha256=_SHA_B, query_state=_query_state(), recall_scores=recall_scores
    )
    window = [candidate.facet_id for candidate in result.candidates[: _LOCKED_FUSE.m]]

    # Every content facet is now inside the window, and in cosine order.
    assert window == [f"facet:content:t{i}" for i in range(len(_A2T_CONTENT_COSINES))]
    result.validate()


def test_dispatch_becomes_possible_on_an_a2t_shaped_knowledge_base():
    """End to end recall -> rank -> fuse: supply is non-empty where it was empty.

    The fuser's percept-admission gate reads only non-prior-mass dimensions, so
    a window full of label/prior facets admits nothing and the controller can
    only retain. Same snapshot, same locked knobs, same recalled set -- only
    the ranking differs -- and the supply path fires.
    """

    snapshot = _a2t_shaped_snapshot()
    recall_scores = _a2t_shaped_recall(snapshot)
    query_state = _query_state()
    fuser = kb_policy.fuse_supplyfilter_factory(_LOCKED_FUSE)

    # Pre-repair ranking, reconstructed as a contract-valid RankResult so the
    # fuser sees exactly what it saw on the 104 G1 trajectories.
    pre_repair = RankResult(
        snapshot_sha256=_SHA_B,
        query_state_sha256=query_state.content_hash(),
        ranking_policy_id=kb_policy.RANK_POLICY_ID,
        candidates=tuple(
            RankedFacet(facet_id=facet_id, score=score)
            for facet_id, score in _pre_repair_ranking(recall_scores, _LOCKED_WEIGHTS)
        ),
    ).validate()
    before = fuser(
        snapshot=snapshot,
        snapshot_sha256=_SHA_B,
        query_state=query_state,
        rank_result=pre_repair,
        recall_scores=recall_scores,
    )
    assert before.selected_value_ids == ()
    assert before.supporting_facet_ids == ()

    ranker = kb_policy.rank_wcos_prior_agree_factory(_LOCKED_WEIGHTS)
    after = fuser(
        snapshot=snapshot,
        snapshot_sha256=_SHA_B,
        query_state=query_state,
        rank_result=ranker(
            snapshot_sha256=_SHA_B,
            query_state=query_state,
            recall_scores=recall_scores,
        ),
        recall_scores=recall_scores,
    )

    # top_l = 3 distinct task_targets, c = 2 values each, one value per tool
    # here -> the three best-scoring tools are supplied.
    assert after.selected_value_ids == ("value:t0", "value:t1", "value:t2")
    assert set(after.supporting_facet_ids) == {
        "facet:content:t0",
        "facet:content:t1",
        "facet:content:t2",
    }
    after.validate()


def test_locked_knobs_put_every_admissible_content_facet_above_every_prior_facet():
    """The property the repair restores, stated as an inequality.

    A recalled facet carries entries only for the dimensions that admitted it,
    so on a single-dimension recall the agreement term is equal for every
    candidate and cancels. What is left is ``w_cos * cos`` against
    ``w_prior * normalised_prior``, and the normalised prior can no longer
    exceed 1. Under the locked knobs that makes the comparison decidable in
    closed form for ANY carrier -- no measurement required.
    """

    prior_ceiling = _LOCKED_WEIGHTS.w_prior * kb_policy._DIMENSION_SCORE_BOUND
    admissible_floor = _LOCKED_WEIGHTS.w_cos * _LOCKED_FUSE.tau
    assert prior_ceiling < admissible_floor
    assert admissible_floor - prior_ceiling == pytest.approx(0.025)


# ---------------------------------------------------------------------------
# Stage 2 (repair): the locked-cell regression against SEALED DEV-1000 records
# ---------------------------------------------------------------------------

_SEALED_RUN_ID = "SAEA-DEV1000-BASELINE-LOCK"
_SEALED_ATTEMPT_ID = "attempt-20260825T054707Z-dev1000blend"
_SEALED_MECHANICAL_SHA256 = "e55b6632d85a0037fb928d565fb2ef1b40c987c915dd98a9f2599d78113c828e"
_SEALED_SNAPSHOT_SHA256 = "e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57"
_SEALED_SNAPSHOT_RELPATH = "knowledge/slurp/saea-kb-distmodel-v1/size-full"


def _sealed_data_root() -> Path | None:
    raw = os.environ.get("SPEECHRL_DATA_DIR")
    if not raw:
        return None
    root = Path(raw)
    needed = (
        root / "runs" / _SEALED_RUN_ID / _SEALED_ATTEMPT_ID / "arm2-blend-mechanical.json",
        root / "runs" / _SEALED_RUN_ID / _SEALED_ATTEMPT_ID / "query-vectors.jsonl",
        root / _SEALED_SNAPSHOT_RELPATH / "snapshot.json",
        root / _SEALED_SNAPSHOT_RELPATH / "vectors-content-facets.npz",
    )
    return root if all(path.exists() for path in needed) else None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


@pytest.mark.skipif(
    _sealed_data_root() is None,
    reason="the sealed DEV-1000 BLEND attempt store is not present under SPEECHRL_DATA_DIR",
)
def test_sealed_dev1000_blend_records_replay_byte_identically_after_the_repair():
    """THE HARD REQUIREMENT, against real landed bytes rather than a fixture.

    Replays sealed DEV-1000 BLEND trajectories through the REPAIRED
    recall -> rank -> fuse path, on their OWN landed query vectors and the
    pinned TRAIN snapshot, and requires two things at once:

    1. the fused ``selected_value_ids`` equal the ``replay_selected_value_ids``
       the sealed per-sample mechanical record already carries -- the same
       branch-only replay the lock campaign landed, re-derived by the new code;
    2. the ranker's whole candidate list, ordering and float scores, is
       bit-identical to :func:`_pre_repair_ranking` on the same recalled set.

    Every input is pinned by hash and a mismatch fails the test rather than
    warning, so this cannot silently replay the wrong bytes. Model-free: zero
    frozen-core contacts, zero embedding-tool contacts, no gold read.

    Cost: the recall step is a pure-Python cosine over 11,514 content facets,
    about a second per trajectory, so a deterministic even stride of
    ``_SEALED_REPLAY_LIMIT`` trajectories is replayed by default. Set
    ``SAEA_KB_POLICY_SEALED_REPLAY_LIMIT=0`` to replay all 1,000.
    """

    import numpy as np

    data_root = _sealed_data_root()
    assert data_root is not None
    run_dir = data_root / "runs" / _SEALED_RUN_ID / _SEALED_ATTEMPT_ID
    snapshot_dir = data_root / _SEALED_SNAPSHOT_RELPATH

    mechanical_path = run_dir / "arm2-blend-mechanical.json"
    assert _sha256_file(mechanical_path) == _SEALED_MECHANICAL_SHA256, (
        "the DEV-1000 BLEND mechanical record is not the sealed bytes the lock read pinned"
    )
    records = json.loads(mechanical_path.read_text(encoding="utf-8"))
    assert len(records) == 1000

    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads((snapshot_dir / "snapshot.json").read_text(encoding="utf-8"))
    )
    assert snapshot.content_hash() == _SEALED_SNAPSHOT_SHA256

    npz = np.load(snapshot_dir / "vectors-content-facets.npz")
    facet_ids = [str(value) for value in npz["ids"]]
    matrix = npz["vectors"]
    vector_table = {
        facet_id: {"content": tuple(matrix[index].tolist())}
        for index, facet_id in enumerate(facet_ids)
    }

    query_vectors: dict[str, tuple[float, ...]] = {}
    with (run_dir / "query-vectors.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            contact_id = str(record["contact_id"])
            if contact_id.startswith("query:"):
                query_vectors[contact_id[len("query:") :]] = tuple(record["values"])

    replayable = sorted(
        sample_id
        for sample_id, record in records.items()
        if record.get("replay_selected_value_ids") is not None
        and sample_id in query_vectors
    )
    assert replayable, "no sealed trajectory carries a landed branch-only replay decision"
    limit = int(os.environ.get("SAEA_KB_POLICY_SEALED_REPLAY_LIMIT", "8"))
    if limit:
        stride = max(1, len(replayable) // limit)
        replayable = replayable[::stride][:limit]

    ranker = kb_policy.rank_wcos_prior_agree_factory(_LOCKED_WEIGHTS)
    fuser = kb_policy.fuse_supplyfilter_factory(_LOCKED_FUSE)
    query_state = _query_state()
    non_empty = 0

    for sample_id in replayable:
        recall_scores = kb_policy.multidim_recall(
            snapshot,
            {"content": query_vectors[sample_id]},
            lambda facet_id: vector_table.get(facet_id, {}),
            _LOCKED_TOP_K,
        )
        rank_result = ranker(
            snapshot_sha256=_SEALED_SNAPSHOT_SHA256,
            query_state=query_state,
            recall_scores=recall_scores,
        )
        # (2) the ranker is the pre-repair ranker on these bytes, exactly.
        assert _ranked(rank_result) == _pre_repair_ranking(recall_scores, _LOCKED_WEIGHTS), (
            f"{sample_id}: the repair moved a locked-cell score"
        )
        # ... which is a consequence of every divisor being exactly 1.0 here.
        assert set(kb_policy._dimension_scales(recall_scores).values()) == {1.0}

        decision = fuser(
            snapshot=snapshot,
            snapshot_sha256=_SEALED_SNAPSHOT_SHA256,
            query_state=query_state,
            rank_result=rank_result,
            recall_scores=recall_scores,
        )
        landed = tuple(records[sample_id]["replay_selected_value_ids"])
        # (1) the supplied value ids are the landed ones, id for id.
        assert tuple(decision.selected_value_ids) == landed, (
            f"{sample_id}: supply diverged from the sealed lock-campaign replay"
        )
        non_empty += 1 if landed else 0

    assert non_empty, "every replayed trajectory supplied nothing -- the regression proves nothing"


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
    # task_target is shaped like a real intent identity ("{scenario}_
    # {action}") rather than a bare "red"/"green" so that _DIRECT_TEXT /
    # _EVIDENCE_TEXT below -- compact JSON, mirroring the real task
    # contract's answer shape -- exercise the repaired
    # kb_policy.default_label_normalizer for real (docs/readiness/
    # 2026-08-24-dev100-damage-channel-analysis.md sec 4.2/9): it recovers
    # a label facet's identity from the response's OWN parsed scenario/
    # action, never from a facet's prose representation.
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
            task_target="red_color",
            prior_score=0.5,
        ),
        ValueBundle(
            value_id="value:green",
            content="Evidence: the item is green.",
            associated_facet_ids=("facet:content:green", "facet:label:green"),
            source_sample_ids=("train:green",),
            provenance_refs=("sample:train:green",),
            task_target="green_color",
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

# Compact JSON, exactly the task contract's real answer shape -- the
# repaired kb_policy.default_label_normalizer parses these fields directly
# (identity "red_color" / "green_color") rather than substring-matching a
# label facet's prose representation.
_DIRECT_TEXT = '{"scenario": "red", "action": "color", "entities": []}'
_EVIDENCE_TEXT = '{"scenario": "green", "action": "color", "entities": []}'


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
    # At alpha=0.0 the fused evidence term is fully zeroed, so the direct
    # label wins outright via kb_policy.default_label_normalizer's real
    # parsed-scenario/action match against "red_color" -- not a substring
    # coincidence (the prior, defective normalizer's failure mode).
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


# ---------------------------------------------------------------------------
# Label-identity binding repair (docs/readiness/2026-08-24-dev100-damage-
# channel-analysis.md sec 4.2/9): default_label_normalizer recovers the
# direct-decode label from the response's OWN parsed scenario/action
# instead of substring-matching a label facet's prose representation.
# ---------------------------------------------------------------------------


def test_default_label_normalizer_recovers_facet_identity_from_parsed_scenario_action():
    """The flown-response shape: the task contract's answers are compact
    JSON, never a label facet's prose representation. The repaired
    normalizer must recover the label identity from the answer's OWN
    parsed scenario/action, matched exactly against label_targets (facet_id
    -> intent identity, i.e. ``_label_identities``'s own output) -- never
    via a substring match."""

    label_targets = {
        "facet:label:intent:alarm_query": "alarm_query",
        "facet:label:intent:alarm_set": "alarm_set",
    }
    response = '{"scenario": "alarm", "action": "query", "entities": []}'
    assert (
        kb_policy.default_label_normalizer(response, label_targets)
        == "facet:label:intent:alarm_query"
    )


def test_default_label_normalizer_breaks_ties_by_facet_id_ascending():
    label_targets = {"facet:label:z": "alarm_query", "facet:label:a": "alarm_query"}
    response = '{"scenario": "alarm", "action": "query"}'
    assert kb_policy.default_label_normalizer(response, label_targets) == "facet:label:a"


def test_default_label_normalizer_does_not_match_a_scenario_action_swap():
    """Exact-identity match only. The damage-channel analysis measured that
    a further 5/100 direct answers name a real TRAIN intent only with
    scenario/action exchanged, but explicitly declined to endorse
    tolerating the swap as an unambiguous repair (sec 9) -- this normalizer
    must NOT resolve it."""

    label_targets = {"facet:label:intent:alarm_query": "alarm_query"}
    swapped_response = '{"scenario": "query", "action": "alarm", "entities": []}'
    assert kb_policy.default_label_normalizer(swapped_response, label_targets) is None


def test_default_label_normalizer_returns_none_when_nothing_matches():
    """The no-label-facet / no-match case: the blend must fall back to the
    same dead-direct behaviour it had before this repair (fused-only
    argmax, no retain-primary) whenever the response's parsed identity
    names no facet in label_targets, fails to parse at all, or
    label_targets is empty."""

    label_targets = {"facet:label:intent:alarm_query": "alarm_query"}
    # a real, parseable answer naming an intent absent from label_targets
    assert (
        kb_policy.default_label_normalizer(
            '{"scenario": "calendar", "action": "query"}', label_targets
        )
        is None
    )
    # unparseable / non-JSON text must fail closed to None, never raise
    assert kb_policy.default_label_normalizer("I have no idea.", label_targets) is None
    # no label facets registered at all
    assert (
        kb_policy.default_label_normalizer('{"scenario": "alarm", "action": "query"}', {})
        is None
    )


def _alarm_intent_snapshot() -> KnowledgeSnapshot:
    """A SLURP-shaped label snapshot: facet ids/representations mirror
    ``rails.knowledge_build``'s real intent facets, and ``task_target`` is
    the real ``"{scenario}_{action}"`` intent identity -- used to prove the
    repaired DEFAULT normalizer makes retain-primary reachable end to end,
    the first real test of that path (retain_primary_samples was 0 across
    all three sealed DEV-100 rounds)."""

    facets = (
        KeyFacet(
            "facet:content:query", "content", "text", "is my alarm set", ("train:query",)
        ),
        KeyFacet("facet:content:set", "content", "text", "wake me at seven", ("train:set",)),
        KeyFacet(
            "facet:label:intent:alarm_query",
            "label",
            "text",
            "Intent 'alarm_query' (scenario='alarm', action='query'); 1 TRAIN "
            "utterance in this snapshot.",
            ("train:query",),
        ),
        KeyFacet(
            "facet:label:intent:alarm_set",
            "label",
            "text",
            "Intent 'alarm_set' (scenario='alarm', action='set'); 1 TRAIN "
            "utterance in this snapshot.",
            ("train:set",),
        ),
    )
    values = (
        ValueBundle(
            value_id="value:query",
            content="Evidence: the caller is asking about an existing alarm.",
            associated_facet_ids=("facet:content:query", "facet:label:intent:alarm_query"),
            source_sample_ids=("train:query",),
            provenance_refs=("sample:train:query",),
            task_target="alarm_query",
            prior_score=0.5,
        ),
        ValueBundle(
            value_id="value:set",
            content="Evidence: the caller wants a new alarm set.",
            associated_facet_ids=("facet:content:set", "facet:label:intent:alarm_set"),
            source_sample_ids=("train:set",),
            provenance_refs=("sample:train:set",),
            task_target="alarm_set",
            prior_score=0.5,
        ),
    )
    return KnowledgeSnapshot(
        snapshot_id="alarm-retain-primary-test-v1",
        source_split_identity_hash=_SHA_B,
        source_sample_ids=("train:query", "train:set"),
        builder_policy_id="test-builder-v1",
        facets=facets,
        values=values,
    ).validate()


def test_repaired_default_normalizer_makes_retain_primary_reachable_end_to_end(
    tmp_path: Path,
):
    """The first real test of the retain-primary path
    (docs/readiness/2026-08-24-dev100-damage-channel-analysis.md sec
    4.2/9): a compact JSON direct answer names ``alarm_query`` while the
    query vector cosine-recalls and fuses only the ``alarm_set`` content
    facet (mirroring the red/green orthogonal-vector pattern above), so the
    pre-evidence blend genuinely competes the direct-decode indicator term
    against a NONZERO fused mass on a different label -- at alpha=0.3 the
    direct term (0.7) still uniquely outweighs the fused term (0.3*1.0),
    so retain-primary fires in a single contact even though evidence was
    available and fused. Uses the registered DEFAULT normalizer
    (unoverridden), exactly as the campaign launchers wire it."""

    snapshot = _alarm_intent_snapshot()
    direct_text = '{"scenario": "alarm", "action": "query", "entities": []}'
    facet_vectors = {
        "facet:content:query": {"content": (1.0, 0.0)},
        "facet:content:set": {"content": (0.0, 1.0)},
    }
    factory = kb_policy.make_kb_alpha_blend_controller_factory(
        snapshot=snapshot,
        query_vectors_by_sample={"s1": {"content": (0.0, 1.0)}},  # aligned with "set" only
        facet_vectors=lambda facet_id: facet_vectors.get(facet_id, {}),
        rank_weights=kb_policy.RankWeights(w_cos=1.0, w_prior=0.0, w_agree=0.0),
        fuse_knobs=kb_policy.FuseKnobs(tau=0.5, m=10, c=1, top_l=2),
        alpha=0.3,
        top_k_per_dimension=10,
    )
    result = _run_with_controller_factory(
        tmp_path,
        snapshot=snapshot,
        factory=factory,
        responder=lambda messages: direct_text,
        sample_id="s1",
    )

    assert [t.action_kind for t in result.transitions] == ["stop"]
    assert len(result.contacts) == 1
    assert result.final_response_text == direct_text


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
