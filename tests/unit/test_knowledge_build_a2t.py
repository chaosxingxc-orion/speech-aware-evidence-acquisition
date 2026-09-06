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

import hashlib
import json
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
from speech_aware_evidence_acquisition.core.roster import (
    RosterItem,
    freeze_roster,
    write_roster,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (
    A2T_KB_BUILD_POLICY_ID,
    A2tKbRow,
    A2tKnowledgeBuildSpec,
    build_a2t_knowledge_snapshot,
    build_a2t_knowledge_snapshot_from_lock,
    coverage_report_a2t,
    distribution_sample_a2t,
    exposed_identity_report,
    exposed_sample_ids,
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
# Exposure union (E2.2)
# ---------------------------------------------------------------------------


def _probe_receipt(
    ids: tuple[tuple[str, int], ...], **extra: object
) -> dict[str, object]:
    """A minimal audio2tool probe-sample receipt in the exact legacy shape
    ``data.audio2tool._verify_receipt`` re-verifies (``key`` = the carrier-
    prefixed id; the hash is sha256 over the LF-joined sorted keys)."""

    items = [
        {
            "id": item_id,
            "key": f"audio2tool:{tier}:{item_id:06d}",
            "query_idx": 1000 + item_id,
            "tier": tier,
        }
        for tier, item_id in ids
    ]
    payload: dict[str, object] = {
        "carrier": "audio2tool",
        "design": "synthetic receipt for the exposure-union tests",
        "items": items,
        "probe": "synthetic",
        "split_identity_hash": hashlib.sha256(
            "\n".join(sorted(str(item["key"]) for item in items)).encode("utf-8")
        ).hexdigest(),
        "split_role": "discovery",
    }
    payload.update(extra)
    return payload


def _d1_supplement(ids: tuple[str, ...], **overrides: object) -> dict[str, object]:
    manifest = [
        {
            "id": sample_id,
            "media_relpath": f"datasets/audio2tool/public/{sample_id}.wav",
            "bytes": 1024,
            "sha256": "0" * 64,
            "audio_seconds": 1.0,
            "sample_rate_hz": 24000,
            "roles": ["query"],
        }
        for sample_id in ids
    ]
    document: dict[str, object] = {
        "schema": "saea-d1-media-supplement-v1",
        "study": "speech-aware-evidence-acquisition",
        "carrier_lock_key": "audio2tool",
        "parent_d1_sha256": "1" * 64,
        "source_binding_sha256": "2" * 64,
        "count": len(manifest),
        "ids_sha256": "3" * 64,
        "manifest": manifest,
        "manifest_sha256": "4" * 64,
        "total_bytes": 1024 * len(manifest),
    }
    document.update(overrides)
    return document


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _synthetic_repo(tmp_path: Path) -> Path:
    """A repository skeleton carrying one of every exposure source kind."""

    probes = tmp_path / "docs" / "receipts" / "probe-samples"
    _write_json(
        probes / "r1-audio2tool-sample.json",
        _probe_receipt((("tier1_direct", 1), ("tier2_parametric", 2))),
    )
    _write_json(
        probes / "another-evaluation-cohort.json",
        _probe_receipt((("tier1_direct", 3),), roster_role="evaluation"),
    )
    _write_json(
        probes / "a-construction-cohort.json",
        _probe_receipt((("tier1_direct", 4),), roster_role="construction"),
    )
    _write_json(
        probes / "some-other-carrier.json",
        {"carrier": "slurp", "items": [{"id": "x", "key": "slurp:x"}]},
    )
    _write_json(
        tmp_path / "docs" / "receipts" / "artifacts" / "d1-a2t-cohort.json",
        _d1_supplement(("tier3_multi_intent:000005", "a2t-derived:000006")),
    )
    return tmp_path


def _roster_file(
    tmp_path: Path, name: str, sample_ids: tuple[str, ...], roster_role: str
) -> None:
    receipt = freeze_roster(
        carrier_lock_key="audio2tool",
        candidates=[
            RosterItem(sample_id=sample_id, stratum="tier1_direct")
            for sample_id in sample_ids
        ],
        per_stratum=len(sample_ids),
        seed=1,
        split_role="discovery",
        roster_id=name.upper(),
    )
    receipt["roster_role"] = roster_role
    write_roster(receipt, tmp_path / "docs" / "receipts" / "rosters" / f"{name}.json")


def test_exposure_union_is_every_evaluation_source_and_only_those(
    tmp_path: Path,
) -> None:
    root = _synthetic_repo(tmp_path)
    _roster_file(root, "fresh-eval", ("tier4_implicit:000007",), "evaluation")
    _roster_file(root, "construction-800", ("tier4_implicit:000008",), "construction")

    assert exposed_sample_ids(root) == frozenset(
        {
            "tier1_direct:000001",
            "tier2_parametric:000002",
            "tier1_direct:000003",
            "tier3_multi_intent:000005",
            "a2t-derived:000006",
            "tier4_implicit:000007",
        }
    )


def test_construction_role_sources_are_excluded_by_design(tmp_path: Path) -> None:
    root = _synthetic_repo(tmp_path)
    _roster_file(root, "construction-800", ("tier4_implicit:000008",), "construction")
    union = exposed_sample_ids(root)
    # The two identities gold may legally reach -- a construction-role
    # probe-sample cohort and a construction-role roster -- are not exposure.
    assert "tier1_direct:000004" not in union
    assert "tier4_implicit:000008" not in union


def test_exposure_report_accounts_for_every_source(tmp_path: Path) -> None:
    root = _synthetic_repo(tmp_path)
    _roster_file(root, "fresh-eval", ("tier4_implicit:000007",), "evaluation")
    report = exposed_identity_report(root)

    assert report["policy_id"] == "saea-a2t-exposure-union-v1"
    assert report["excluded_roster_role"] == "construction"
    assert report["sources_by_kind"] == {
        "d1-media-supplement": 1,
        "probe-sample": 2,
        "roster-receipt": 1,
    }
    assert sum(int(row["new_sample_ids"]) for row in report["sources"]) == (
        report["union_sample_ids"]
    )
    assert report["union_sample_ids"] == len(exposed_sample_ids(root))
    by_name = {str(row["name"]): row for row in report["sources"]}
    assert by_name["r1-audio2tool-sample"]["sample_ids"] == 2
    assert by_name["d1-a2t-cohort"]["sample_ids"] == 2
    assert "a-construction-cohort" not in by_name


def test_union_refuses_a_malformed_d1_supplement(tmp_path: Path) -> None:
    root = _synthetic_repo(tmp_path)
    _write_json(
        root / "docs" / "receipts" / "artifacts" / "d1-a2t-broken.json",
        _d1_supplement(("tier1_direct:000009",), count=99),
    )
    with pytest.raises(RailsError, match="count/manifest/id-uniqueness disagree"):
        exposed_sample_ids(root)


def test_union_refuses_a_supplement_of_another_carrier(tmp_path: Path) -> None:
    root = _synthetic_repo(tmp_path)
    _write_json(
        root / "docs" / "receipts" / "artifacts" / "d1-a2t-foreign.json",
        _d1_supplement(("tier1_direct:000009",), carrier_lock_key="slurp"),
    )
    with pytest.raises(RailsError, match="names carrier"):
        exposed_sample_ids(root)


def test_union_refuses_an_unknown_roster_role(tmp_path: Path) -> None:
    root = _synthetic_repo(tmp_path)
    _write_json(
        root / "docs" / "receipts" / "probe-samples" / "odd-role.json",
        _probe_receipt((("tier1_direct", 10),), roster_role="calibration"),
    )
    with pytest.raises(RailsError, match="roster_role"):
        exposed_sample_ids(root)


def test_union_still_fails_closed_without_the_frozen_400(tmp_path: Path) -> None:
    root = _synthetic_repo(tmp_path)
    (
        root / "docs" / "receipts" / "probe-samples" / "r1-audio2tool-sample.json"
    ).unlink()
    with pytest.raises(RailsError, match="r1-audio2tool-sample"):
        exposed_sample_ids(root)


def test_partition_protects_the_whole_block_of_a_construction_only_tool() -> None:
    """The 2026-09-05 repair: a rare tool's row is not merely dropped from
    eval candidacy -- its whole ``query_idx`` block is, because a sibling row
    of another tier in the same block would otherwise reserve the block and
    take the rare tool's last exemplar with it."""

    shared_block = 100
    rare = _row(
        "tier5_needle",
        shared_block,
        tool="setAlarm",
        words="set the alarm for the early meeting",
        arg_keys=("time",),
        item_ids=(9001,),
    )
    rows = _corpus() + (rare,)
    siblings = [row for row in rows if row.query_idx == shared_block]
    assert len(siblings) > 1, "the fixture must share this block across tiers"

    proposal = propose_partition(rows, frozenset(), per_tier=1, tool_min_pool_rows=4)
    assert shared_block not in set(proposal.eval_blocks)
    assert rare.unit_id in {row.unit_id for row in proposal.construction}
    assert int(proposal.report["blocks_protected_for_construction_only_tools"]) >= 1


def test_partition_keeps_one_block_for_every_tool_the_free_pool_can_supply() -> None:
    """The 2026-09-05 SECOND repair (MF-1): protecting only the RARE tools'
    blocks still let the draw starve a tool that clears
    ``tool_min_pool_rows`` but holds few free blocks -- under the exposure
    union that now also reserves A2T-FRESH-800, a per_tier=50 draw wiped out
    nine smart_home tools and the floor check refused the whole partition.
    Every tool the free pool can supply now keeps one deterministic block, so
    the starvation branch is unreachable rather than luck-dependent."""

    rows: list[A2tKbRow] = []
    item_id = 0
    for step in range(5):
        item_id += 2
        rows.append(
            _row(
                "tier1_direct",
                100 + step,
                tool="setLighting",
                words=f"tier1 lighting request {step}",
                arg_keys=("deviceId", "state"),
                item_ids=(item_id, item_id + 1),
            )
        )
    for step in range(5):
        item_id += 2
        rows.append(
            _row(
                "tier1_direct",
                200 + step,
                tool="setColor",
                words=f"tier1 colour request {step}",
                arg_keys=("color", "deviceId"),
                item_ids=(item_id, item_id + 1),
            )
        )
    for step in range(10):
        item_id += 2
        rows.append(
            _row(
                "tier2_parametric",
                300 + step,
                tool="setColor",
                words=f"tier2 colour request {step}",
                arg_keys=("color", "deviceId"),
                item_ids=(item_id, item_id + 1),
            )
        )

    proposal = propose_partition(
        tuple(rows), frozenset(), per_tier=8, tool_min_pool_rows=5
    )
    report = proposal.report
    assert int(report["blocks_protected_for_construction_only_tools"]) == 0
    assert int(report["blocks_protected_for_tool_floor"]) == 2
    assert int(report["blocks_protected_total"]) == 2
    surviving = {row.tool_name for row in proposal.construction}
    assert surviving == {"setLighting", "setColor"}
    # The protected block is the tool's lexicographically first unit's block,
    # and it never enters the evaluation draw.
    assert 100 not in set(proposal.eval_blocks)
    assert 200 not in set(proposal.eval_blocks)


def test_partition_names_tools_the_exposure_union_reserved_entirely() -> None:
    """A tool whose every unit sits inside an exposed block cannot enter the
    construction pool however the eval tier is drawn, so it is REPORTED by
    name rather than raised on -- raising would blame the draw for the union.
    """

    rows = _corpus()
    exposed = frozenset(
        sid
        for row in rows
        if row.tool_name == "getAirQuality"
        for sid in row.sample_ids
    )
    proposal = propose_partition(rows, exposed, per_tier=1, tool_min_pool_rows=3)
    assert "getAirQuality" in proposal.report["tools_reserved_entirely_by_exposure"]
    assert "getAirQuality" not in {row.tool_name for row in proposal.construction}

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
