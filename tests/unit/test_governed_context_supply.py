"""Synthetic contract tests for deterministic parent-scoped context supply."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.governed_context_supply import (
    SOURCE_SCOPED_CONTEXT_FUSE_POLICY_ID,
    GovernedContextSupplyError,
    SourceScopedContextProvider,
)
from speech_aware_evidence_acquisition.rails.knowledge import (
    EXTERNAL_GOVERNED_PARTITION_ROLE,
    KeyFacet,
    KnowledgeSnapshot,
    QueryState,
    ValueBundle,
)

SHA = "a" * 64


def _snapshot(*, malformed=False):
    facets = tuple(
        KeyFacet(
            facet_id=f"scope-{sample}", dimension="source-scope",
            representation_kind="parent-sample-id", representation=sample,
            source_sample_ids=(f"external-{sample}",),
        )
        for sample in ("parent-a", "parent-b")
    )
    values = tuple(
        ValueBundle(
            value_id=f"value-{sample}", content=f"governed context {sample}",
            associated_facet_ids=(("scope-parent-a", "scope-parent-b") if malformed and sample == "parent-a" else (f"scope-{sample}",)),
            source_sample_ids=(f"external-{sample}",), provenance_refs=("synthetic",),
        )
        for sample in ("parent-a", "parent-b")
    )
    return KnowledgeSnapshot(
        snapshot_id="governed-context", source_split_identity_hash=SHA,
        source_sample_ids=("external-parent-a", "external-parent-b"), builder_policy_id="synthetic",
        source_partition_role=EXTERNAL_GOVERNED_PARTITION_ROLE, facets=facets, values=values,
    ).validate()


def _query(parent):
    return QueryState(
        query_id=f"query:{parent}", query_sample_id=parent,
        speech_packet_id=f"speech/{parent}", speech_packet_sha256=SHA,
        use_split_identity_hash=SHA,
    ).validate()


def test_two_sibling_windows_route_only_their_shared_parent_scope():
    provider = SourceScopedContextProvider(snapshot=_snapshot())
    for window in ("window-0", "window-1"):
        query = _query("parent-a")
        ranking = provider.candidates(
            {"context": SimpleNamespace(sample_id="parent-a", window=window), "query_state": query}, k=1
        )
        decision = provider.fuse([ranking], k=1, policy_id=SOURCE_SCOPED_CONTEXT_FUSE_POLICY_ID)
        assert decision.selected_value_ids == ("value-parent-a",)
        assert decision.supporting_facet_ids == ("scope-parent-a",)


def test_scope_swap_and_mixed_associations_are_refused():
    provider = SourceScopedContextProvider(snapshot=_snapshot())
    with pytest.raises(GovernedContextSupplyError, match="original query"):
        provider.candidates(
            {"context": SimpleNamespace(sample_id="parent-b"), "query_state": _query("parent-a")}, k=1
        )
    with pytest.raises(GovernedContextSupplyError, match="mixed association"):
        SourceScopedContextProvider(snapshot=_snapshot(malformed=True))
