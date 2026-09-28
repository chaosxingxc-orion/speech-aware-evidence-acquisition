"""Cell RANKVIS (owner decision 171): rank-ordered, rank-visible value rendering.

``native_episode.knowledge_value_rendering`` is the one config switch the
RANKVIS conversion probe needs. These proofs pin three things:

1. the key is OFF by default -- absent, the parsed config carries ``None`` and
   the real native episode renders byte-identically (the pre-change request
   digests of ``test_phase_supply_repeat_visit`` are re-asserted here);
2. the parser refuses every malformed, dead or conflicting declaration by name;
3. armed, the real runner re-orders a named store's supplied values by
   retrieval rank at the supply step and prefixes each rendered value of that
   store with its 1-based rank, while the selected SET, every other part and
   every other store are unchanged.

Model-free: the episodes run the real OpenJiuwen role graph and the real
runner through the shared fake transport. No utterance, gold or model text.
"""

from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails.knowledge import (
    FusionDecision,
    RankedFacet,
    RankResult,
)
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    KNOWLEDGE_VALUE_RENDERING_SCHEMA,
    NativeEpisodeRunBinding,
    load_native_episode_config,
    parse_knowledge_value_rendering,
)
from speech_aware_evidence_acquisition.rails.runner import (
    RANK_VISIBLE_LABEL,
    order_supply_by_retrieval_rank,
    rank_visible_value_renderer,
    run_speech_native_agent_loop,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_config import config as episode_config
from test_native_episode_config import program as episode_program
from test_native_episode_runner import _ActualEpisodeHarness
from test_phase_supply_repeat_visit import (
    EXEMPLAR_FACET_IDS,
    EXEMPLAR_VALUE_IDS,
    SUPPLIED_FIRST_VISIT_REQUEST_SHA256,
    _exemplar_snapshot,
    _prepared_supply,
    _rendered_texts,
    _request_digests,
    _supplied_program,
)
from test_rails_runner import _controller_registry

STORE = "train-exemplars"


def _block(**overrides) -> dict:
    block = {
        "schema": KNOWLEDGE_VALUE_RENDERING_SCHEMA,
        "order": "retrieval-rank",
        "rank_visible": True,
        "stores": [STORE],
    }
    block.update(overrides)
    return block


def _values(block=None) -> dict:
    values = episode_config()
    values["knowledge_stores"] = {STORE: {}, "intent-boundaries": {}}
    if block is not None:
        values["native_episode"]["knowledge_value_rendering"] = block
    return values


# ---------------------------------------------------------------------------
# 1. The key: absent is today's config; armed parses to one canonical text.
# ---------------------------------------------------------------------------


def test_absent_key_parses_to_none():
    parsed = load_native_episode_config(_values(), episode_program())
    assert parsed.knowledge_value_rendering_json is None
    assert parsed.knowledge_value_rendering is None


def test_armed_key_parses_to_its_canonical_block():
    parsed = load_native_episode_config(_values(_block()), episode_program())
    assert parsed.knowledge_value_rendering == _block()
    assert json.loads(parsed.knowledge_value_rendering_json) == _block()


@pytest.mark.parametrize(
    "block, match",
    [
        ("retrieval-rank", "must carry exactly"),
        ({**_block(), "extra": 1}, "must carry exactly"),
        (_block(schema="saea-knowledge-value-rendering-v0"), "schema must be"),
        (_block(order="score"), "order must be one of"),
        (_block(rank_visible="yes"), "rank_visible must be a bool"),
        (_block(order="supplied-order", rank_visible=False), "changes nothing"),
        (_block(order="supplied-order", rank_visible=True), "requires order 'retrieval-rank'"),
        (_block(stores=[]), "non-empty list of distinct store ids"),
        (_block(stores=[STORE, STORE]), "non-empty list of distinct store ids"),
        (_block(stores=["train-exemplars::x"]), "non-empty list of distinct store ids"),
        (_block(stores=["slot-contracts"]), "does not bind"),
    ],
)
def test_the_parser_refuses_by_name(block, match):
    with pytest.raises(ValueError, match=match):
        parse_knowledge_value_rendering(block, values=_values())


def test_order_without_visible_rank_is_legal():
    text = parse_knowledge_value_rendering(_block(rank_visible=False), values=_values())
    assert json.loads(text)["rank_visible"] is False


def test_refused_beside_the_knowledge_index_and_phase_tools():
    with pytest.raises(ValueError, match="knowledge_index"):
        parse_knowledge_value_rendering(_block(), values=_values(), knowledge_index_armed=True)
    values = _values(_block())
    values["phase_tools"] = {"reviewer": {
        "mode": "native-tools", "source_authority_role": "reviewer", "allowed_tools": ["analyze"],
    }}
    values["native_episode"]["roles"]["reviewer"]["max_iterations"] = 3
    with pytest.raises(ValueError, match="phase_tools"):
        load_native_episode_config(values, episode_program(ceiling=6))


# ---------------------------------------------------------------------------
# 2. The two pure functions.
# ---------------------------------------------------------------------------


def _supply(snapshot, selected, scores):
    sha = snapshot.content_hash()
    rank = RankResult(
        snapshot_sha256=sha, query_state_sha256="c" * 64,
        ranking_policy_id="saea-rank-wcos-prior-agree-v1",
        candidates=tuple(RankedFacet(facet_id=f, score=s) for f, s in scores),
    ).validate()
    decision = FusionDecision(
        snapshot_sha256=sha, query_state_sha256="c" * 64,
        rank_result_sha256=rank.content_hash(),
        fusion_policy_id="saea-fuse-supplyfilter-v1",
        supporting_facet_ids=tuple(f for f, _ in scores),
        selected_value_ids=tuple(selected),
    ).validate()
    return rc.PhaseSupply(rank_result=rank, fusion_decision=decision).validate()


def test_order_moves_only_the_named_store_and_keeps_the_set():
    snapshot = _exemplar_snapshot()
    # facet b outranks facet a: every odd-index exemplar must come first.
    supply = _supply(snapshot, EXEMPLAR_VALUE_IDS, [(EXEMPLAR_FACET_IDS[1], 0.9), (EXEMPLAR_FACET_IDS[0], 0.5)])
    ordered = order_supply_by_retrieval_rank(supply, snapshot, (STORE,))
    got = ordered.fusion_decision.selected_value_ids
    assert set(got) == set(EXEMPLAR_VALUE_IDS)
    assert got == EXEMPLAR_VALUE_IDS[1::2] + EXEMPLAR_VALUE_IDS[0::2]
    assert ordered.rank_result is supply.rank_result
    assert ordered.fusion_decision.supporting_facet_ids == supply.fusion_decision.supporting_facet_ids
    # A store that is not named is never touched, and an already ranked
    # selection comes back as the SAME object.
    assert order_supply_by_retrieval_rank(supply, snapshot, ("intent-boundaries",)) is supply
    assert order_supply_by_retrieval_rank(ordered, snapshot, (STORE,)) is ordered


def test_renderer_prefixes_the_rank_inside_the_named_store_only():
    values = (
        SimpleNamespace(value_id="intent-boundaries::a", content="boundary A"),
        SimpleNamespace(value_id="train-exemplars::x", content="exemplar X"),
        SimpleNamespace(value_id="slot-contracts::s", content="card S"),
        SimpleNamespace(value_id="train-exemplars::y", content="exemplar Y"),
    )
    snapshot = SimpleNamespace(values=values, facets=())
    state = SimpleNamespace(retrieved_value_ids=tuple(v.value_id for v in values))
    render = rank_visible_value_renderer(snapshot_sha256="d" * 64, stores=(STORE, "intent-boundaries"))
    parts = render(snapshot, state, ())
    assert [p["text"] for p in parts] == [
        RANK_VISIBLE_LABEL.format(rank=1) + "boundary A",
        RANK_VISIBLE_LABEL.format(rank=1) + "exemplar X",
        "card S",
        RANK_VISIBLE_LABEL.format(rank=2) + "exemplar Y",
    ]
    assert [p["evidence_id"] for p in parts] == [v.value_id for v in values]
    assert {p["knowledge_role"] for p in parts} == {"value"}
    assert parts[0]["source_uri"] == f"knowledge-snapshot://{'d' * 64}/intent-boundaries::a"


# ---------------------------------------------------------------------------
# 3. Through the real native episode.
# ---------------------------------------------------------------------------


def _ranked_supply(snapshot):
    """``_prepared_supply`` with facet b ranked above facet a."""

    inner = _prepared_supply(snapshot)

    def supply_for_phase(phase_name, context):
        supply = inner(phase_name, context)
        if supply is None:
            return None
        rank = replace(
            supply.rank_result,
            candidates=(
                RankedFacet(facet_id=EXEMPLAR_FACET_IDS[1], score=0.9),
                RankedFacet(facet_id=EXEMPLAR_FACET_IDS[0], score=0.5),
            ),
        ).validate()
        decision = replace(supply.fusion_decision, rank_result_sha256=rank.content_hash()).validate()
        return replace(supply, rank_result=rank, fusion_decision=decision).validate()

    return supply_for_phase


def _run(tmp_path, *, rendering=None, supply_factory=_prepared_supply):
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=1, max_contacts=7, planner_actions=("ACCEPT",),
    )
    snapshot = _exemplar_snapshot()
    harness.program = _supplied_program(max_contacts=7)
    if rendering is not None:
        harness.config = replace(harness.config, knowledge_value_rendering_json=json.dumps(rendering))
    binding = NativeEpisodeRunBinding(
        config=harness.config, program=harness.program,
        material_for_phase=harness.material_for_phase,
        render_request=harness.transport.render_request,
        request_gate=harness.request_gate, tools_for_phase=harness.tools_for_phase,
        supply_for_phase=supply_factory(snapshot),
    )
    try:
        summary = run_speech_native_agent_loop(
            data_root=harness.world.data_root, plan=harness.plan, adapter=harness.adapter,
            core_client=harness.client, split_id="all", knowledge_snapshot=snapshot,
            speech_packet_bindings=harness.speech_bindings,
            controller_policy_id=harness.program.program_id,
            controller_registry=_controller_registry(harness.program.program_id, lambda _s: object()),
            max_contacts=harness.config.max_contacts, slot_count=1, queue_depth=1,
            trace_sink=harness.trace, agent_executor_id="openjiuwen-workflow-v1",
            decoding_params={"temperature": 0, "max_tokens": 64},
            native_episode_binding=binding,
        )
    finally:
        harness.close()
    return harness, summary, snapshot


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_off_is_byte_identical_to_the_pre_change_requests(tmp_path):
    harness, _summary, _snapshot = _run(tmp_path)
    assert _request_digests(harness) == SUPPLIED_FIRST_VISIT_REQUEST_SHA256


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_armed_orders_by_rank_and_shows_it(tmp_path):
    harness, summary, snapshot = _run(tmp_path, rendering=_block(), supply_factory=_ranked_supply)
    content = {v.value_id: v.content for v in snapshot.values}
    expected_order = EXEMPLAR_VALUE_IDS[1::2] + EXEMPLAR_VALUE_IDS[0::2]
    key = next(k for k in harness.prepared if k[1] == "solver")
    texts = [t for t in _rendered_texts(harness, key) if t.startswith("[evidence ")]
    assert texts == [
        f"[evidence {vid}] {RANK_VISIBLE_LABEL.format(rank=rank)}{content[vid]}"
        for rank, vid in enumerate(expected_order, start=1)
    ]
    acquired = [t for t in summary.results[0].transitions if t.new_value_ids]
    assert acquired and acquired[0].new_value_ids == expected_order


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_armed_order_only_keeps_the_content_unlabelled(tmp_path):
    harness, _summary, snapshot = _run(
        tmp_path, rendering=_block(rank_visible=False), supply_factory=_ranked_supply,
    )
    content = {v.value_id: v.content for v in snapshot.values}
    key = next(k for k in harness.prepared if k[1] == "solver")
    texts = [t for t in _rendered_texts(harness, key) if t.startswith("[evidence ")]
    expected_order = EXEMPLAR_VALUE_IDS[1::2] + EXEMPLAR_VALUE_IDS[0::2]
    assert texts == [f"[evidence {vid}] {content[vid]}" for vid in expected_order]
