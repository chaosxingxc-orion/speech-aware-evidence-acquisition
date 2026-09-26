"""The PRE-COMPUTED exemplar-intent vote: self-exclusion, determinism and
worker-count independence (2026-09-26; authority
``docs/results/2026-09-26-slurp-intent-retrieval-rank-diagnostic.md`` section 3).

``scripts/build_slurp_intent_exemplar_agreement.py`` is a script, not a package
module, so it is loaded here by path -- the same way the repository's other
script tests reach their subject. What is tested is the pure vote-formation
function and the recall seam it drives, never a real vector file: the fixtures
are synthetic ids and synthetic unit vectors.

No text, transcript, gold label or intent name appears in any assertion.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.kb_policy import FuseKnobs, RankWeights
from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    ValueBundle,
)
from speech_aware_evidence_acquisition.rails.knowledge_provider import KbFacetProvider
from speech_aware_evidence_acquisition.rails.phase_supply import (
    PhaseSupplySpec,
    build_bootstrap_selection,
)

_SHA = "c" * 64
_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "build_slurp_intent_exemplar_agreement.py"
)


def _builder():
    spec = importlib.util.spec_from_file_location(
        "saea_test_agreement_builder", _SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BUILDER = _builder()


# ---------------------------------------------------------------------------
# the utterance identity the self-exclusion keys on
# ---------------------------------------------------------------------------


def test_utterance_identity_is_the_first_three_fields():
    assert (
        BUILDER.utterance_identity("slurp:train:000007:audio--1504197557")
        == "slurp:train:000007"
    )
    # two recordings of ONE utterance share it, which is the point
    assert BUILDER.utterance_identity(
        "slurp:train:000007:audio--1504197557"
    ) == BUILDER.utterance_identity("slurp:train:000007:audio-1504197557-headset")


@pytest.mark.parametrize("sample_id", ["slurp:train", "slurp::000007:a", "", "a:b"])
def test_a_sample_id_with_no_utterance_identity_is_refused(sample_id):
    with pytest.raises(BUILDER.BuildError, match="utterance identity"):
        BUILDER.utterance_identity(sample_id)


# ---------------------------------------------------------------------------
# the vote: self-exclusion, shares, refusals
# ---------------------------------------------------------------------------

_TARGETS = {"value:1": "a", "value:2": "a", "value:3": "b", "value:4": None}
_UTTERANCES = {
    "value:1": {"slurp:train:000001"},
    "value:2": {"slurp:train:000002"},
    "value:3": {"slurp:train:000003"},
    "value:4": {"slurp:train:000004"},
}
_FACETS = {"intent-boundary:a", "intent-boundary:b"}


def _vote(selected, own):
    return BUILDER.form_vote(
        selected,
        own_utterance=own,
        target_of_value=_TARGETS,
        utterances_of_value=_UTTERANCES,
        target_facet_template="intent-boundary:{key}",
        target_facets=_FACETS,
    )


def test_the_vote_is_the_share_of_each_target_over_the_admitted_total():
    shares, total, dropped, untargeted = _vote(
        ["value:1", "value:2", "value:3"], "slurp:train:000099"
    )
    assert total == 3 and dropped == 0 and untargeted == 0
    assert shares == {
        "intent-boundary:a": pytest.approx(2 / 3),
        "intent-boundary:b": pytest.approx(1 / 3),
    }
    assert sum(shares.values()) == pytest.approx(1.0)


def test_the_row_s_own_utterance_is_excluded_from_its_own_vote():
    shares, total, dropped, _ = _vote(
        ["value:1", "value:2", "value:3"], "slurp:train:000001"
    )
    assert dropped == 1 and total == 2
    assert shares == {
        "intent-boundary:a": pytest.approx(0.5),
        "intent-boundary:b": pytest.approx(0.5),
    }


def test_the_exclusion_fires_on_another_recording_of_the_same_utterance():
    """The evaluated row is a DIFFERENT recording of utterance 000003; the pool
    value covering that utterance is still dropped."""

    shares, total, dropped, _ = _vote(
        ["value:1", "value:3"],
        BUILDER.utterance_identity("slurp:train:000003:audio-headset"),
    )
    assert dropped == 1 and total == 1 and shares == {"intent-boundary:a": 1.0}


def test_a_pool_value_with_no_build_time_target_is_counted_not_dropped_silently():
    shares, total, dropped, untargeted = _vote(
        ["value:1", "value:4"], "slurp:train:000099"
    )
    assert untargeted == 1 and dropped == 0 and total == 1
    assert shares == {"intent-boundary:a": 1.0}


def test_a_fully_self_excluded_row_yields_no_vote_and_no_shares():
    shares, total, dropped, _ = _vote(["value:1"], "slurp:train:000001")
    assert (shares, total, dropped) == ({}, 0, 1)


def test_a_selected_value_the_vote_snapshot_lacks_is_refused():
    with pytest.raises(BUILDER.BuildError, match="does not declare"):
        _vote(["value:999"], "slurp:train:000099")


def test_a_target_that_maps_to_no_facet_is_refused_not_dropped():
    with pytest.raises(BUILDER.BuildError, match="does not map to any facet"):
        BUILDER.form_vote(
            ["value:3"],
            own_utterance="slurp:train:000099",
            target_of_value=_TARGETS,
            utterances_of_value=_UTTERANCES,
            target_facet_template="intent-boundary:{key}",
            target_facets={"intent-boundary:a"},
        )


def test_the_vote_is_independent_of_the_order_the_selection_arrives_in():
    reference = _vote(["value:1", "value:2", "value:3"], "slurp:train:000099")
    for order in (
        ["value:3", "value:1", "value:2"],
        ["value:2", "value:3", "value:1"],
        ("value:3", "value:2", "value:1"),
    ):
        assert _vote(order, "slurp:train:000099") == reference


# ---------------------------------------------------------------------------
# worker-count independence of the recall the vote summarises
# ---------------------------------------------------------------------------


def _pool_snapshot(count: int = 12) -> KnowledgeSnapshot:
    return KnowledgeSnapshot(
        snapshot_id="pool-test-v1",
        source_split_identity_hash=_SHA,
        source_sample_ids=tuple(f"slurp:train:{n:06d}:audio--{n}" for n in range(count)),
        builder_policy_id="test-builder-v1",
        facets=tuple(
            KeyFacet(f"facet:content:{n}", "content", "text", f"k{n}", (f"slurp:train:{n:06d}:audio--{n}",))
            for n in range(count)
        ),
        values=tuple(
            ValueBundle(
                value_id=f"value:{n}",
                content=f"body {n}",
                associated_facet_ids=(f"facet:content:{n}",),
                source_sample_ids=(f"slurp:train:{n:06d}:audio--{n}",),
                provenance_refs=(f"sample:slurp:train:{n:06d}",),
                task_target="a" if n % 2 else "b",
            )
            for n in range(count)
        ),
    ).validate()


def _pool_spec() -> PhaseSupplySpec:
    return PhaseSupplySpec(
        phase="solver",
        provider="kb-facet-v1",
        rank_policy="saea-rank-wcos-prior-agree-v1",
        fuse_policy="saea-fuse-supplyfilter-v1",
        k=5,
        tau=0.0,
        dimensions=("content",),
        query_source={
            "kind": "sealed-vectors",
            "relpath": "vectors/q.jsonl",
            "sha256": _SHA,
            "tool_contact_ledger_row": "ROW",
            "embedded_signal": "speech: the row's own sealed utterance vector",
        },
        rank_weights={"w_cos": 1.0, "w_prior": 0.0, "w_agree": 0.0},
        fuse_coverage={"m": 5, "c": 5, "top_l": 5},
    ).validate()


@pytest.mark.parametrize("workers", [1, 2, 4])
def test_the_exemplar_selection_is_identical_at_every_worker_count(workers):
    """``build_bootstrap_selection`` forks for ``workers > 1``; the selection it
    returns must not depend on how many processes computed it. Skipped off
    Linux, where the parallel path is refused by design."""

    if workers > 1 and sys.platform != "linux":
        pytest.skip("the parallel bootstrap path requires Linux/WSL fork semantics")
    count = 12
    snapshot = _pool_snapshot(count)
    keys = {
        f"facet:content:{n}": {"content": tuple(1.0 if i == n else 0.0 for i in range(count))}
        for n in range(count)
    }
    rows = [f"slurp:dev:{r:06d}:audio--{r}" for r in range(6)]
    queries = {
        row: {"content": tuple(1.0 / (1 + abs(i - index)) for i in range(count))}
        for index, row in enumerate(rows)
    }
    packets = {row: {"packet_id": f"p/{row}", "sha256": _SHA} for row in rows}

    def provider():
        built = KbFacetProvider(
            build_spec=None,
            rank_weights=RankWeights(w_cos=1.0, w_prior=0.0, w_agree=0.0),
            fuse_knobs=FuseKnobs(tau=0.0, m=5, c=5, top_l=5),
            top_k_per_dimension=5,
            facet_vectors=lambda facet_id: keys.get(facet_id, {}),
        )
        return built.adopt(
            snapshot, policy_id="frozen-snapshot:solver", snapshot_sha256=_SHA
        )

    serial = build_bootstrap_selection(
        _pool_spec(),
        provider=provider(),
        query_vectors_by_sample=queries,
        speech_packet_bindings=packets,
        split_identity_hash=_SHA,
        workers=1,
    )
    got = build_bootstrap_selection(
        _pool_spec(),
        provider=provider(),
        query_vectors_by_sample=queries,
        speech_packet_bindings=packets,
        split_identity_hash=_SHA,
        workers=workers,
    )
    assert got == serial
    assert set(got[1]) == set(rows)


def test_the_vote_formed_from_a_selection_is_stable_across_worker_counts():
    """Composition of the two properties above: identical selections yield
    identical votes, so the pinned agreement table is reproducible whatever
    ``--workers`` the builder was given."""

    targets = {f"value:{n}": ("a" if n % 2 else "b") for n in range(12)}
    utterances = {f"value:{n}": {f"slurp:train:{n:06d}"} for n in range(12)}
    facets = {"intent-boundary:a", "intent-boundary:b"}
    selection = [f"value:{n}" for n in (7, 3, 11, 2)]
    reference = BUILDER.form_vote(
        selection,
        own_utterance="slurp:dev:000000",
        target_of_value=targets,
        utterances_of_value=utterances,
        target_facet_template="intent-boundary:{key}",
        target_facets=facets,
    )
    for _ in range(5):
        assert (
            BUILDER.form_vote(
                list(reversed(selection)),
                own_utterance="slurp:dev:000000",
                target_of_value=targets,
                utterances_of_value=utterances,
                target_facet_template="intent-boundary:{key}",
                target_facets=facets,
            )
            == reference
        )
