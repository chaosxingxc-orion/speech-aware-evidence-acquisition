"""Synthetic tests for source-bound knowledge lookup by task target."""

from __future__ import annotations

from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.rails.candidate_contract_lookup import (
    CandidateContractLookupError,
)
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    QueryState,
    ValueBundle,
    assert_knowledge_use_binding,
)
from speech_aware_evidence_acquisition.rails.knowledge_target_lookup import (
    TOOL_ID,
    KnowledgeTargetLookupError,
    lookup_knowledge_targets,
)


SHA_A = "a" * 64
SHA_B = "b" * 64


def _facet(facet_id: str) -> KeyFacet:
    return KeyFacet(
        facet_id=facet_id,
        dimension="task semantics",
        representation_kind="text",
        representation=f"English guidance for {facet_id}.",
        source_sample_ids=("train-1",),
    )


def _value(
    value_id: str,
    task_target: str | None,
    *facet_ids: str,
) -> ValueBundle:
    return ValueBundle(
        value_id=value_id,
        content=f"English evidence for {value_id}.",
        associated_facet_ids=tuple(facet_ids),
        source_sample_ids=("train-1",),
        provenance_refs=(f"synthetic://{value_id}",),
        task_target=task_target,
    )


def _snapshot() -> KnowledgeSnapshot:
    facets = tuple(
        _facet(facet_id)
        for facet_id in (
            "facet-alpha-1",
            "facet-alpha-2",
            "facet-beta-1",
            "facet-beta-2",
            "facet-none",
        )
    )
    return KnowledgeSnapshot(
        snapshot_id="synthetic-target-snapshot",
        source_split_identity_hash=SHA_A,
        source_sample_ids=("train-1",),
        builder_policy_id="synthetic-target-builder-v1",
        facets=facets,
        values=(
            _value("z-beta-2", "beta", "facet-beta-2"),
            _value("alpha-looking-id", "beta", "facet-beta-1"),
            _value("beta-looking-id", "alpha", "facet-alpha-1"),
            _value("z-alpha-2", "alpha", "facet-alpha-2"),
            _value("alpha-id-without-target", None, "facet-none"),
        ),
    ).validate()


def _query(*, loop_step: int = 0) -> QueryState:
    return QueryState(
        query_id="query:dev-1",
        query_sample_id="dev-1",
        speech_packet_id="packet:dev-1",
        speech_packet_sha256=SHA_B,
        use_split_identity_hash=SHA_A,
        loop_step=loop_step,
    ).validate()


def _lookup(
    *,
    candidate_ids=("beta", "alpha"),
    max_values_per_candidate=2,
    max_total_values=3,
    already_visible_value_ids=(),
    snapshot=None,
    query_state=None,
):
    return lookup_knowledge_targets(
        snapshot or _snapshot(),
        query_state or _query(),
        candidate_ids,
        max_values_per_candidate=max_values_per_candidate,
        max_total_values=max_total_values,
        already_visible_value_ids=already_visible_value_ids,
    )


def test_task_target_is_authoritative_despite_misleading_value_ids():
    result = _lookup(
        candidate_ids=("alpha",),
        max_values_per_candidate=3,
        max_total_values=3,
    )

    assert result.selected_value_ids == ("beta-looking-id", "z-alpha-2")
    assert result.audit["mappings"] == [
        {
            "candidate_id": "alpha",
            "mapped_value_ids": ["beta-looking-id", "z-alpha-2"],
            "selected_value_ids": ["beta-looking-id", "z-alpha-2"],
            "ignored_mappings": [],
            "status": "mapped",
        }
    ]
    assert "alpha-id-without-target" not in result.selected_value_ids


def test_candidate_order_and_both_caps_drive_round_robin_selection():
    result = _lookup()

    assert result.selected_value_ids == (
        "alpha-looking-id",
        "beta-looking-id",
        "z-beta-2",
    )
    assert [item["candidate_id"] for item in result.audit["mappings"]] == [
        "beta",
        "alpha",
    ]
    assert result.audit["mappings"][1]["ignored_mappings"] == [
        {"value_id": "z-alpha-2", "reason": "total-limit"}
    ]
    unhashed_audit = dict(result.audit)
    selection_sha256 = unhashed_audit.pop("selection_sha256")
    assert selection_sha256 == content_hash(unhashed_audit)


def test_partial_overlap_does_not_refill_and_supply_contains_only_new_values():
    snapshot = _snapshot()
    query_state = _query()
    result = _lookup(
        snapshot=snapshot,
        query_state=query_state,
        already_visible_value_ids=("alpha-looking-id",),
    )

    assert result.selected_value_ids == (
        "alpha-looking-id",
        "beta-looking-id",
        "z-beta-2",
    )
    assert result.audit["already_visible_selected_value_ids"] == ["alpha-looking-id"]
    assert result.audit["new_value_ids"] == ["beta-looking-id", "z-beta-2"]
    assert result.audit["supply_disposition"] == "acquired"
    assert result.supply is not None
    assert result.supply.fusion_decision.selected_value_ids == (
        "beta-looking-id",
        "z-beta-2",
    )
    assert result.supply.fusion_decision.supporting_facet_ids == (
        "facet-alpha-1",
        "facet-beta-2",
    )
    assert tuple(
        candidate.facet_id for candidate in result.supply.rank_result.candidates
    ) == ("facet-alpha-1", "facet-beta-2")
    assert result.supply.action_target_ref == (
        f"{TOOL_ID}:selection={result.audit['selection_sha256']}"
    )
    assert_knowledge_use_binding(
        snapshot=snapshot,
        query_state=query_state,
        rank_result=result.supply.rank_result,
        fusion_decision=result.supply.fusion_decision,
        snapshot_sha256=snapshot.content_hash(),
    )


def test_repeated_lookup_of_full_selection_returns_no_new_supply():
    first = _lookup()
    repeated = _lookup(already_visible_value_ids=first.selected_value_ids)

    assert repeated.selected_value_ids == first.selected_value_ids
    assert repeated.supply is None
    assert repeated.audit["new_value_ids"] == []
    assert repeated.audit["already_visible_selected_value_ids"] == list(
        first.selected_value_ids
    )
    assert repeated.audit["supply_disposition"] == "already-visible"


def test_missing_targets_are_explicit_and_all_missing_returns_no_supply():
    result = _lookup(
        candidate_ids=("missing", "alpha"),
        max_values_per_candidate=1,
        max_total_values=1,
    )
    missing = result.audit["mappings"][0]
    assert missing == {
        "candidate_id": "missing",
        "mapped_value_ids": [],
        "selected_value_ids": [],
        "ignored_mappings": [],
        "status": "absent",
    }
    assert result.selected_value_ids == ("beta-looking-id",)

    all_missing = _lookup(candidate_ids=("missing",))
    assert all_missing.selected_value_ids == ()
    assert all_missing.supply is None
    assert all_missing.audit["supply_disposition"] == "no-mapping"


def test_query_change_rebinds_hashes_and_selection_receipt():
    snapshot = _snapshot()
    first = _lookup(snapshot=snapshot, query_state=_query(loop_step=0))
    changed = _lookup(snapshot=snapshot, query_state=_query(loop_step=1))

    assert first.audit["snapshot_sha256"] == snapshot.content_hash()
    assert changed.audit["snapshot_sha256"] == snapshot.content_hash()
    assert first.audit["query_state_sha256"] != changed.audit["query_state_sha256"]
    assert first.audit["selection_sha256"] != changed.audit["selection_sha256"]
    assert first.supply is not None and changed.supply is not None
    assert (
        first.supply.rank_result.query_state_sha256 == first.audit["query_state_sha256"]
    )
    assert (
        changed.supply.rank_result.query_state_sha256
        == changed.audit["query_state_sha256"]
    )
    assert first.supply.fusion_decision.snapshot_sha256 == snapshot.content_hash()
    assert changed.supply.fusion_decision.snapshot_sha256 == snapshot.content_hash()


@pytest.mark.parametrize("bound", [0, -1, True, 1.5, 33])
def test_bounds_must_be_positive_non_bool_integers_at_most_32(bound):
    with pytest.raises(KnowledgeTargetLookupError, match="max_values_per_candidate"):
        _lookup(max_values_per_candidate=bound)
    with pytest.raises(KnowledgeTargetLookupError, match="max_total_values"):
        _lookup(max_total_values=bound)


@pytest.mark.parametrize(
    "candidate_ids",
    [(), ("alpha", "alpha"), ("non-ascii-\N{LATIN SMALL LETTER E WITH ACUTE}",)],
)
def test_candidate_request_uses_shared_strict_validation(candidate_ids):
    with pytest.raises(CandidateContractLookupError, match="candidate_ids"):
        _lookup(candidate_ids=candidate_ids)


@pytest.mark.parametrize(
    "visible_ids, message",
    [
        (("beta-looking-id", "beta-looking-id"), "duplicate"),
        (("foreign-value",), "snapshot"),
        ("beta-looking-id", "sequence"),
    ],
)
def test_already_visible_ids_must_be_unique_local_snapshot_members(
    visible_ids, message
):
    with pytest.raises(KnowledgeTargetLookupError, match=message):
        _lookup(already_visible_value_ids=visible_ids)


def test_snapshot_and_query_state_are_validated():
    invalid_snapshot = replace(_snapshot(), values=())
    with pytest.raises(RailsError, match="values"):
        _lookup(snapshot=invalid_snapshot)

    invalid_query = replace(_query(), query_id="")
    with pytest.raises(RailsError, match="query_id"):
        _lookup(query_state=invalid_query)

    with pytest.raises(KnowledgeTargetLookupError, match="KnowledgeSnapshot"):
        _lookup(snapshot=object())
    with pytest.raises(KnowledgeTargetLookupError, match="QueryState"):
        _lookup(query_state=object())


def test_reread_returns_only_previously_visible_values_in_bound_order():
    snapshot = _snapshot()
    result = lookup_knowledge_targets(snapshot, _query(), ("alpha",),
        max_values_per_candidate=1, max_total_values=2,
        already_visible_value_ids=("z-beta-2", "beta-looking-id", "z-alpha-2"),
        selection_mode="reread")
    assert result.selected_value_ids == ("z-beta-2", "beta-looking-id")
    assert result.supply is None
    assert result.audit["new_value_ids"] == []
    assert result.audit["selection_mode"] == "reread"


def test_reread_empty_does_not_fall_back_to_new_knowledge():
    result = lookup_knowledge_targets(_snapshot(), _query(), ("alpha",),
        max_values_per_candidate=1, max_total_values=2, selection_mode="reread")
    assert result.selected_value_ids == ()
    assert result.supply is None


def test_unknown_selection_mode_is_refused():
    with pytest.raises(KnowledgeTargetLookupError, match="selection_mode"):
        lookup_knowledge_targets(_snapshot(), _query(), ("alpha",),
            max_values_per_candidate=1, max_total_values=2, selection_mode="guess")
