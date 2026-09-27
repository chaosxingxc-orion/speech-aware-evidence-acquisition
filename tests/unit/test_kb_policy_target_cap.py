"""Contract tests for the W3 target-capped supply filter (owner decision 164).

``saea-fuse-supplyfilter-target-cap-v1`` walks the admitted ranking in rank
order, takes at most ``c`` values per task target and stops at ``top_l``
values. With the cap at or above the total it must equal the flown supply
filter on a one-value-per-facet store; below it, the freed slots go to the
next-ranked values of other targets. All fixtures are synthetic English
metadata; no dataset payloads are read here.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.core.base import KNOWLEDGE_FUSERS
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.kb_policy import (
    TARGET_CAP_FUSE_POLICY_ID,
    FuseKnobs,
    fuse_supplyfilter_factory,
    fuse_supplyfilter_target_cap_factory,
    select_target_capped,
)
from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    QueryState,
    RankedFacet,
    RankResult,
    ValueBundle,
)

_SNAPSHOT_SHA256 = "a" * 64
_SPEECH_SHA256 = "b" * 64
_SPLIT_SHA256 = "c" * 64


def _query_state(retrieved: tuple[str, ...] = ()) -> QueryState:
    return QueryState(
        query_id="query-target-cap",
        query_sample_id="train:target-cap",
        speech_packet_id="packet-target-cap",
        speech_packet_sha256=_SPEECH_SHA256,
        use_split_identity_hash=_SPLIT_SHA256,
        retrieved_value_ids=retrieved,
    ).validate()


def _store(targets: list[str]) -> KnowledgeSnapshot:
    """One value per facet, facet i carries target ``targets[i]``."""

    facets, values = [], []
    for index, target in enumerate(targets):
        facet_id = f"facet:content:{index:03d}"
        facets.append(KeyFacet(facet_id, "content", "text", f"English key {index}", (f"train:{index}",)))
        values.append(
            ValueBundle(
                value_id=f"value:{index:03d}",
                content=f"English exemplar {index} | {target}",
                associated_facet_ids=(facet_id,),
                source_sample_ids=(f"train:{index}",),
                provenance_refs=(f"synthetic:{index}",),
                task_target=target,
                prior_score=0.5,
            )
        )
    return KnowledgeSnapshot(
        snapshot_id="target-cap-fuser-test-v1",
        source_split_identity_hash=_SPLIT_SHA256,
        source_sample_ids=tuple(f"train:{index}" for index in range(len(targets))),
        builder_policy_id="synthetic-target-cap-builder-v1",
        facets=tuple(facets),
        values=tuple(values),
    ).validate()


def _decide(fuser, snapshot, *, order: list[int], cosines: dict[int, float] | None = None, retrieved=()):
    query_state = _query_state(retrieved)
    candidates = tuple(
        RankedFacet(f"facet:content:{index:03d}", 1.0 - 0.001 * rank)
        for rank, index in enumerate(order)
    )
    rank = RankResult(
        snapshot_sha256=_SNAPSHOT_SHA256,
        query_state_sha256=query_state.content_hash(),
        ranking_policy_id="synthetic-ranked-facets-v1",
        candidates=candidates,
    ).validate()
    cos = cosines or {}
    recall = {f"facet:content:{index:03d}": {"content": cos.get(index, 0.5)} for index in order}
    return fuser(
        snapshot=snapshot,
        snapshot_sha256=_SNAPSHOT_SHA256,
        query_state=query_state,
        rank_result=rank,
        recall_scores=recall,
    )


def test_registered_under_its_own_id():
    assert TARGET_CAP_FUSE_POLICY_ID == "saea-fuse-supplyfilter-target-cap-v1"
    assert TARGET_CAP_FUSE_POLICY_ID in KNOWLEDGE_FUSERS.names()
    assert KNOWLEDGE_FUSERS.resolve(TARGET_CAP_FUSE_POLICY_ID) is fuse_supplyfilter_target_cap_factory


def test_cap_at_or_above_total_equals_the_flown_supply_filter():
    targets = ["a"] * 14 + ["b"] * 4 + ["c"] * 6 + ["d"] * 6
    snapshot = _store(targets)
    order = list(range(len(targets)))[::-1]
    flown = fuse_supplyfilter_factory(FuseKnobs(tau=0.0, m=20, c=20, top_l=20))
    for cap in (20, 25):
        capped = fuse_supplyfilter_target_cap_factory(FuseKnobs(tau=0.0, m=20, c=cap, top_l=20))
        assert _decide(capped, snapshot, order=order).selected_value_ids == _decide(flown, snapshot, order=order).selected_value_ids
    # A deeper admission changes nothing while the cap does not bind: the walk stops at 20.
    deep = fuse_supplyfilter_target_cap_factory(FuseKnobs(tau=0.0, m=30, c=20, top_l=20))
    assert _decide(deep, snapshot, order=order).selected_value_ids == _decide(flown, snapshot, order=order).selected_value_ids


def test_cap_binds_and_refills_from_deeper_ranks():
    # Rank order: 14 x a, 4 x b, 6 x c, 6 x d, 3 x e.
    targets = ["a"] * 14 + ["b"] * 4 + ["c"] * 6 + ["d"] * 6 + ["e"] * 3
    snapshot = _store(targets)
    order = list(range(len(targets)))
    fuser = fuse_supplyfilter_target_cap_factory(FuseKnobs(tau=0.0, m=33, c=5, top_l=20))
    decision = _decide(fuser, snapshot, order=order)
    chosen = [targets[int(value.split(":")[1])] for value in decision.selected_value_ids]
    assert len(chosen) == 20
    assert {t: chosen.count(t) for t in "abcde"} == {"a": 5, "b": 4, "c": 5, "d": 5, "e": 1}
    # The a-values kept are the five best-ranked ones.
    assert [v for v in decision.selected_value_ids if targets[int(v.split(":")[1])] == "a"] == [f"value:{i:03d}" for i in range(5)]
    assert decision.fusion_policy_id == TARGET_CAP_FUSE_POLICY_ID


def test_short_admission_delivers_fewer_rather_than_breaking_the_cap():
    targets = ["a"] * 10 + ["b"] * 2
    snapshot = _store(targets)
    fuser = fuse_supplyfilter_target_cap_factory(FuseKnobs(tau=0.0, m=12, c=3, top_l=20))
    decision = _decide(fuser, snapshot, order=list(range(12)))
    assert len(decision.selected_value_ids) == 5


def test_tau_is_a_cosine_floor_and_visible_values_cost_nothing():
    targets = ["a", "b", "c", "d"]
    snapshot = _store(targets)
    fuser = fuse_supplyfilter_target_cap_factory(FuseKnobs(tau=0.3, m=4, c=1, top_l=2))
    decision = _decide(fuser, snapshot, order=[0, 1, 2, 3], cosines={0: 0.2}, retrieved=("value:001",))
    # facet 0 fails the floor, value 1 is already visible: the next two are taken.
    assert decision.selected_value_ids == ("value:002", "value:003")


def test_explicit_knobs_are_required_and_the_pure_rule_validates():
    with pytest.raises(RailsError):
        fuse_supplyfilter_target_cap_factory(None)
    with pytest.raises(RailsError):
        select_target_capped((), targets_by_facet={}, per_target_cap=0, total=20)
    selected, supporting = select_target_capped(
        [("f1", 0.9), ("f2", 0.8), ("f3", 0.7)],
        targets_by_facet={"f1": [("v1", "x")], "f2": [("v2", "x")], "f3": [("v3", "y")]},
        per_target_cap=1,
        total=2,
    )
    assert selected == ("v1", "v3") and supporting == ("f1", "f3")


def test_the_prompt_bound_counts_the_delivered_width_under_the_target_cap_fuser():
    """The pre-flight prompt bound counts the longest ``min(k, top_l)`` values under this fuser, as
    under the associated-values fuser: the walk stops at ``top_l`` values overall, so a cell that
    recalls 300 and delivers 20 is bounded at 20 blocks, not 300. The flown supply filter keeps ``k``."""

    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    from speech_aware_evidence_acquisition.rails import controllers as rc
    from speech_aware_evidence_acquisition.rails.kb_policy import FUSE_POLICY_ID

    program = rc.default_phase_program("phase-direct-evidence-alpha-blend-v1")
    snapshot = _store([f"t{n % 7}" for n in range(60)])

    def bound(k: int, top_l: int, fuse_policy: str) -> int:
        stub = SimpleNamespace(
            _composed=SimpleNamespace(values={"phase_supply": {"evidence": {
                "provider": "kb-facet-v1", "rank_policy": "saea-rank-wcos-prior-agree-v1",
                "fuse_policy": fuse_policy, "k": k, "tau": 0.0, "dimensions": ["content"],
                "expose_facets": False, "fuse_coverage": {"m": k, "c": 5, "top_l": top_l},
                "query_source": {"kind": "sealed-vectors", "relpath": "v/q.jsonl", "sha256": "d" * 64,
                                 "tool_contact_ledger_row": "TEST-EMB-0001", "embedded_signal": "speech: synthetic"},
            }}}),
            _load_knowledge_snapshot=lambda: snapshot,
        )
        return len(FlightRuntime._phase_supply_prompt_bound(stub, program)["evidence"])

    assert bound(50, 20, TARGET_CAP_FUSE_POLICY_ID) == 20
    assert bound(50, 20, FUSE_POLICY_ID) == 50
