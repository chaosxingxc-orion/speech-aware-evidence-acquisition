"""KB-BUILD-A2T v1 (Audio2Tool generality campaign, stage G0): sampler
determinism and pool-order independence, the three hard floors (per tool,
per argument-pattern family, per tier), the block-partition proposal's
disjointness properties, fail-closed decontamination refusal on a planted
evaluation id, frozen-JSON byte-stability, and the lexical reachability
ceiling plus its gate.

Every test here is MODEL-FREE, network-free and filesystem-free: the corpus
is synthetic :class:`A2tKbRow` data built in-process, and the offline guard
the production script arms is irrelevant because nothing here opens a
socket at all.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_lexical_ceiling import (
    Bm25Index,
    content_facet_targets,
    gate_verdict,
    lexical_reachability_ceiling,
    tokenize,
)
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.hashing import canonical_json_bytes
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot
from speech_aware_evidence_acquisition.core.base import KNOWLEDGE_BUILDERS
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (
    A2T_KB_BUILD_POLICY_ID,
    A2tKbRow,
    A2tKnowledgeBuildSpec,
    build_a2t_knowledge_snapshot,
    build_a2t_knowledge_snapshot_from_lock,
    coverage_report_a2t,
    distribution_sample_a2t,
    propose_partition,
)


# ---------------------------------------------------------------------------
# Synthetic corpus helpers
# ---------------------------------------------------------------------------

_TOOLS = (
    ("setLighting", "smart_home", "lighting", ("deviceId", "state")),
    ("setColor", "smart_home", "lighting", ("color", "deviceId")),
    ("getAirQuality", "smart_home", "climate", ("deviceId",)),
    ("setAlarm", "wearable", "alerts", ("time",)),
    ("rebootDevice", "vehicle", "system", ()),
)

_REGISTRY = {
    name: {
        "tool_id": str(index),
        "domain": domain,
        "category": category,
        "tool_name": name,
        "signature": f"{name}({', '.join(keys)})",
        "description": f"Synthetic description of {name}.",
        "argument_defaults": "",
        "argument_constraints": "",
    }
    for index, (name, domain, category, keys) in enumerate(_TOOLS)
}


def _row(
    tier: str,
    query_idx: int,
    *,
    tool: str,
    words: str,
    arg_keys: tuple[str, ...] = (),
    item_ids: tuple[int, ...] = (1,),
) -> A2tKbRow:
    _name, domain, category, _keys = next(item for item in _TOOLS if item[0] == tool)
    sample_ids = tuple(f"{tier}:{item_id:06d}" for item_id in item_ids)
    return A2tKbRow(
        unit_id=f"{tier}:{query_idx:06d}",
        tier=tier,
        query_idx=query_idx,
        text=words,
        domain=domain,
        category=category,
        tool_id=0,
        tool_name=tool,
        arg_signature=tuple(sorted(arg_keys)),
        arg_pairs=tuple((key, f"{key}_value") for key in sorted(arg_keys)),
        call_render=f"{tool}()",
        extra_call_names=(),
        call_count=1,
        sample_ids=sample_ids,
        item_ids=tuple(item_ids),
        media_relpath_by_sample_id={sid: f"audio/{sid}.wav" for sid in sample_ids},
        speaker_ids=tuple("voice_a" for _ in sample_ids),
    )


def _corpus() -> tuple[A2tKbRow, ...]:
    """A synthetic pool with a deliberate long tail: ``rebootDevice`` and the
    ``setAlarm`` no-argument family each appear exactly once."""

    rows: list[A2tKbRow] = []
    item_id = 0
    for tier in ("tier1_direct", "tier2_parametric", "tier7_multiturn"):
        for step in range(14):
            item_id += 2
            tool, _domain, _category, keys = _TOOLS[step % 3]
            rows.append(
                _row(
                    tier,
                    100 + step,
                    tool=tool,
                    words=f"{tier} request number {step} for {tool} please",
                    arg_keys=keys,
                    item_ids=(item_id, item_id + 1),
                )
            )
    rows.append(
        _row(
            "tier1_direct",
            900,
            tool="setAlarm",
            words="wake me at seven tomorrow morning",
            arg_keys=("time",),
            item_ids=(901,),
        )
    )
    rows.append(
        _row(
            "tier1_direct",
            901,
            tool="setAlarm",
            words="cancel every alarm on the watch",
            arg_keys=(),
            item_ids=(902,),
        )
    )
    rows.append(
        _row(
            "tier2_parametric",
            902,
            tool="rebootDevice",
            words="restart the head unit in the car right now",
            arg_keys=(),
            item_ids=(903,),
        )
    )
    return tuple(rows)


def _forbidden() -> frozenset[str]:
    return frozenset({"tier9_absent:000001"})


# ---------------------------------------------------------------------------
# Sampler
# ---------------------------------------------------------------------------


def test_sampler_is_deterministic_and_pool_order_independent() -> None:
    rows = _corpus()
    shuffled = list(rows)
    random.Random(7).shuffle(shuffled)
    first = distribution_sample_a2t(rows, 20, seed=20260825)
    second = distribution_sample_a2t(shuffled, 20, seed=20260825)
    assert [row.unit_id for row in first] == [row.unit_id for row in second]
    # A different seed is allowed to differ, but must still be reproducible.
    third = distribution_sample_a2t(rows, 20, seed=1)
    assert [row.unit_id for row in third] == [
        row.unit_id for row in distribution_sample_a2t(shuffled, 20, seed=1)
    ]


def test_sampler_keeps_every_tool_family_and_tier() -> None:
    rows = _corpus()
    selected = distribution_sample_a2t(rows, 12, seed=20260825)
    assert {row.tool_name for row in selected} == {row.tool_name for row in rows}
    assert {row.family_key for row in selected} == {row.family_key for row in rows}
    assert {row.tier for row in selected} == {row.tier for row in rows}


def test_floors_outrank_a_size_target_that_cannot_hold_them() -> None:
    rows = _corpus()
    selected = distribution_sample_a2t(rows, 2, seed=20260825)
    # Two seats cannot hold five tools; the floor set wins and is returned larger.
    assert len(selected) > 2
    assert {row.tool_name for row in selected} == {row.tool_name for row in rows}


def test_full_selection_is_the_whole_pool_sorted() -> None:
    rows = _corpus()
    selected = distribution_sample_a2t(rows, None, seed=20260825)
    assert [row.unit_id for row in selected] == sorted(row.unit_id for row in rows)


def test_sampler_rejects_duplicate_unit_ids() -> None:
    rows = _corpus()
    with pytest.raises(RailsError, match="unique unit_id"):
        distribution_sample_a2t(rows + (rows[0],), 5, seed=1)


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def _build(size: int | None = None) -> KnowledgeSnapshot:
    return build_a2t_knowledge_snapshot(
        A2tKnowledgeBuildSpec(datastore_size=size),
        rows=_corpus(),
        registry=_REGISTRY,
        forbidden_sample_ids=_forbidden(),
    )


def test_snapshot_shape_and_label_facets() -> None:
    snapshot = _build()
    assert snapshot.builder_policy_id == A2T_KB_BUILD_POLICY_ID
    tool_facets = {
        facet.facet_id for facet in snapshot.facets if facet.facet_id.startswith("facet:label:tool:")
    }
    assert len(tool_facets) == len({row.tool_name for row in _corpus()})
    content_facets = [facet for facet in snapshot.facets if facet.dimension == "content"]
    assert len(content_facets) == len(snapshot.values)
    # Every value carries its gold tool as the task target and is bound to a
    # label facet, so kb_policy's label-identity path can resolve it.
    for value in snapshot.values:
        assert value.task_target is not None
        assert any(
            facet_id.startswith("facet:label:tool:") for facet_id in value.associated_facet_ids
        )
    # The argument-structure bet: the value text names the exemplar's own
    # argument pattern and the tool's registry signature.
    sample = next(value for value in snapshot.values if value.task_target == "setLighting")
    assert "argument pattern" in sample.content
    assert "registry signature" in sample.content


def test_snapshot_round_trips_and_is_byte_stable() -> None:
    first = _build()
    second = _build()
    assert first.snapshot_id == second.snapshot_id
    assert first.content_hash() == second.content_hash()
    assert canonical_json_bytes(first.frozen_json()) == canonical_json_bytes(
        second.frozen_json()
    )
    restored = KnowledgeSnapshot.from_frozen_json(first.frozen_json())
    assert restored.content_hash() == first.content_hash()


def test_decontamination_refuses_a_planted_evaluation_id() -> None:
    rows = _corpus()
    planted = rows[0].sample_ids[0]
    with pytest.raises(RailsError, match="decontamination roster"):
        build_a2t_knowledge_snapshot(
            A2tKnowledgeBuildSpec(),
            rows=rows,
            registry=_REGISTRY,
            forbidden_sample_ids=frozenset({planted}),
        )


def test_build_refuses_an_empty_decontamination_roster() -> None:
    with pytest.raises(RailsError, match="EMPTY"):
        build_a2t_knowledge_snapshot(
            A2tKnowledgeBuildSpec(),
            rows=_corpus(),
            registry=_REGISTRY,
            forbidden_sample_ids=frozenset(),
        )


def test_spec_rejects_a_foreign_carrier_and_a_bad_dimension() -> None:
    with pytest.raises(RailsError, match="Audio2Tool-only"):
        A2tKnowledgeBuildSpec(carrier_lock_key="slurp").validate()
    with pytest.raises(RailsError, match="dimensions"):
        A2tKnowledgeBuildSpec(dimensions=("speaker",)).validate()


def test_coverage_report_reports_full_coverage_for_a_full_build() -> None:
    rows = _corpus()
    report = coverage_report_a2t(_build(), rows, registry_tool_count=len(_REGISTRY))
    assert report["tool_coverage"] == 1.0
    assert report["argument_pattern_family_coverage"] == 1.0
    assert report["tier_coverage"] == 1.0
    assert report["kl_selected_given_pool_over_tool"] == pytest.approx(0.0)
    assert report["counts"]["selected_units"] == len(rows)
    assert report["counts"]["registry_tools"] == len(_REGISTRY)


# ---------------------------------------------------------------------------
# Partition proposal
# ---------------------------------------------------------------------------


def test_partition_is_block_disjoint_and_excludes_the_exposed_roster() -> None:
    rows = _corpus()
    exposed = frozenset({rows[0].sample_ids[0]})
    proposal = propose_partition(
        rows, exposed, seed=20260807, per_tier=2, tool_min_pool_rows=3
    )
    eval_ids = set(proposal.eval_sample_ids)
    construction_ids = {sid for row in proposal.construction for sid in row.sample_ids}
    assert eval_ids and construction_ids
    assert not eval_ids & construction_ids
    assert not eval_ids & set(exposed)
    assert not construction_ids & set(exposed)
    # Block disjointness, the property the item-level check cannot see.
    eval_blocks = set(proposal.eval_blocks)
    assert not eval_blocks & {row.query_idx for row in proposal.construction}
    assert rows[0].query_idx in set(proposal.reserved_exposed_blocks)
    assert rows[0].query_idx not in eval_blocks
    assert proposal.split_identity_hash() == proposal.split_identity_hash()


def test_partition_is_deterministic_and_pool_order_independent() -> None:
    rows = _corpus()
    shuffled = list(rows)
    random.Random(3).shuffle(shuffled)
    exposed = frozenset({rows[0].sample_ids[0]})
    first = propose_partition(rows, exposed, per_tier=2, tool_min_pool_rows=3)
    second = propose_partition(shuffled, exposed, per_tier=2, tool_min_pool_rows=3)
    assert first.eval_sample_ids == second.eval_sample_ids
    assert first.split_identity_hash() == second.split_identity_hash()


def test_partition_refuses_a_draw_larger_than_the_free_pool() -> None:
    rows = _corpus()
    with pytest.raises(RailsError, match="block-free candidates"):
        propose_partition(rows, frozenset(), per_tier=500, tool_min_pool_rows=3)


def test_partition_keeps_every_tool_in_the_construction_pool() -> None:
    rows = _corpus()
    proposal = propose_partition(rows, frozenset(), per_tier=2)
    assert {row.tool_name for row in proposal.construction} == {
        row.tool_name for row in rows
    }


# ---------------------------------------------------------------------------
# Registry entry (E2.1)
# ---------------------------------------------------------------------------


def test_the_a2t_builder_resolves_through_the_shared_registry() -> None:
    """The owner base rule: every builder a config may name resolves in a
    ``core.base`` registry, populated only from one of the six canonical
    files. Importing ``rails.knowledge_build`` is what performs the
    Audio2Tool registration, so the import is the test's own arrangement."""

    import speech_aware_evidence_acquisition.rails.knowledge_build  # noqa: F401

    assert A2T_KB_BUILD_POLICY_ID in KNOWLEDGE_BUILDERS.names()
    assert (
        KNOWLEDGE_BUILDERS.resolve(A2T_KB_BUILD_POLICY_ID)
        is build_a2t_knowledge_snapshot_from_lock
    )


def test_the_registered_builder_validates_its_spec_before_touching_the_lock() -> None:
    """Fail-closed ordering: a foreign carrier is refused by the spec itself,
    before ``a2t_pool_rows`` can open a single governed manifest -- so the
    registry entry can never read another carrier's bytes."""

    spec = A2tKnowledgeBuildSpec(carrier_lock_key="slurp")
    with pytest.raises(RailsError, match="Audio2Tool-only"):
        build_a2t_knowledge_snapshot_from_lock(
            spec, lock={}, root=Path("/nonexistent"), repo_root=Path("/nonexistent")
        )

# ---------------------------------------------------------------------------
# Lexical ceiling and the G0 gate
# ---------------------------------------------------------------------------


def test_tokenizer_and_bm25_ranking_are_deterministic() -> None:
    assert tokenize("Turn ON the light_1, please!") == (
        "turn",
        "on",
        "the",
        "light",
        "1",
        "please",
    )
    index = Bm25Index.build(
        [("b", "turn on the kitchen light"), ("a", "restart the head unit"), ("c", "x")]
    )
    ranking = index.ranking("turn on the light")
    assert index.doc_ids[ranking[0]] == "b"
    assert ranking == index.ranking("turn on the light")
    # Every document is ranked, including those with a zero score.
    assert sorted(ranking) == list(range(len(index.doc_ids)))


def test_ceiling_finds_the_gold_tool_and_the_gate_passes() -> None:
    snapshot = _build()
    targets = content_facet_targets(snapshot)
    assert targets
    # Paraphrases, not copies: the near-duplicate audit must classify both as
    # NOVEL (max token Jaccard below the 0.8 threshold) and still reach the
    # gold tool, which is exactly the property the pooled ceiling claims.
    eval_items = (
        ("tier1_direct", 5001, "restart the head unit", "rebootDevice"),
        ("tier1_direct", 5002, "wake me at seven", "setAlarm"),
    )
    ceiling = lexical_reachability_ceiling(snapshot, eval_items, k_grid=(1, 5))
    assert ceiling["population"] == 2
    assert ceiling["recall_at_k"]["1"] == 1.0
    assert ceiling["recall_at_k"]["5"] == 1.0
    assert ceiling["random_ranking_expectation_at_k"]["1"] < 0.5
    audit = ceiling["near_duplicate_audit"]
    assert audit["novel_subgroup_population"] == 2
    assert audit["share_at_or_above"]["0.8"] == 0.0
    assert audit["novel_subgroup_recall_at_k"]["5"] == 1.0
    verdict = gate_verdict(ceiling, gate_k=5, a0_tool_accuracy=0.5425)
    assert verdict["verdict"] == "PASS"
    assert verdict["margin"] == pytest.approx(1.0 - 0.5425)


def test_gate_stops_when_the_ceiling_does_not_exceed_the_a0_baseline() -> None:
    verdict = gate_verdict(
        {"recall_at_k": {"5": 0.5425}}, gate_k=5, a0_tool_accuracy=0.5425
    )
    assert verdict["verdict"] == "STOP"
    assert verdict["margin"] == pytest.approx(0.0)
    with pytest.raises(RailsError, match="no recall at k"):
        gate_verdict({"recall_at_k": {"5": 0.9}}, gate_k=7)


def test_near_duplicate_audit_flags_a_verbatim_copy() -> None:
    snapshot = _build()
    eval_items = (
        ("tier1_direct", 5003, "restart the head unit in the car right now", "rebootDevice"),
    )
    audit = lexical_reachability_ceiling(snapshot, eval_items, k_grid=(1, 5))[
        "near_duplicate_audit"
    ]
    assert audit["max_jaccard"]["max"] == pytest.approx(1.0)
    assert audit["share_at_or_above"]["0.9"] == 1.0
    assert audit["novel_subgroup_population"] == 0
    assert audit["novel_subgroup_recall_at_k"] == {}


def test_ceiling_refuses_an_empty_population() -> None:
    with pytest.raises(RailsError, match="eval_items must be non-empty"):
        lexical_reachability_ceiling(_build(), ())
