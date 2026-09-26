"""The EXEMPLAR-INTENT AGREEMENT term on the intent-boundary retrieval channel
(2026-09-26; authority
``docs/results/2026-09-26-slurp-intent-retrieval-rank-diagnostic.md`` sections 3
and 6).

Five obligations the registration brief names, each asserted rather than argued:

1. THE DEFAULT IS BYTE-IDENTICAL. With no agreement dimension in the recall the
   ranker's scores, order and ``RankResult`` content hash are bit-for-bit the
   pre-change arithmetic at every weighting, including a non-zero ``w_agree``
   that still reads the legacy cross-dimension fraction.
2. THE VOTE IS SELF-EXCLUDED. A pool value covering the evaluated row's own
   utterance is dropped before the shares are formed, and the exclusion keys on
   the utterance identity rather than the exact sample id, so another recording
   of the same utterance is dropped too.
3. THE VOTE IS DETERMINISTIC AND WORKER-COUNT INDEPENDENT.
4. A MISSING INPUT REFUSES, NEVER SCORES 0.0 -- the silent
   ``.get()``/``continue`` skip the 2026-09-26 read found elsewhere is not
   reproduced. A row absent from the agreement table is refused by the provider;
   a roster row with no exemplar query vector is refused by the builder; a
   recalled facet the table gives no share is a ZERO vote, which is different
   and is scored 0.0 on purpose.
5. TIES ARE STABLE. The ranker's order under equal scores is ``facet_id``
   ascending, with or without the agreement term.

Plus the loader's fail-closed contract, since the agreement table is a
receipt-pinned input like the key vectors beside it.

No text, transcript, gold label or intent name appears in any assertion: the
fixtures are synthetic ids.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails import kb_policy
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.kb_policy import (
    AGREEMENT_DIMENSIONS,
    EXEMPLAR_INTENT_AGREEMENT_DIMENSION,
    FuseKnobs,
    RankWeights,
    cosine_dimension_items,
    fuse_associated_values_factory,
    rank_wcos_prior_agree_factory,
)
from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    QueryState,
    ValueBundle,
)
from speech_aware_evidence_acquisition.rails.knowledge_provider import KbFacetProvider
from speech_aware_evidence_acquisition.rails.phase_supply import (
    PhaseSupplyError,
    PhaseSupplySpec,
    SEALED_AGREEMENT_SCHEMA,
    load_sealed_agreement,
)

_SHA = "b" * 64
_DIM = "intent-boundary"


# ---------------------------------------------------------------------------
# fixtures: a 1:1 boundary-shaped store, three intents
# ---------------------------------------------------------------------------


def _boundary_snapshot(intents: tuple[str, ...] = ("a", "b", "c")) -> KnowledgeSnapshot:
    """The flown intent-boundary shape: one facet per intent, one value per
    facet, facet id == value id, one dimension, no ``task_target`` and no
    ``prior_score`` (the read measured 0 of 60 carrying either)."""

    return KnowledgeSnapshot(
        snapshot_id="boundary-test-v1",
        source_split_identity_hash=_SHA,
        source_sample_ids=tuple(f"train:{i}" for i in intents),
        builder_policy_id="test-builder-v1",
        facets=tuple(
            KeyFacet(f"{_DIM}:{i}", _DIM, "text", f"boundary {i}", (f"train:{i}",))
            for i in intents
        ),
        values=tuple(
            ValueBundle(
                value_id=f"{_DIM}:{i}",
                content=f"body {i}",
                associated_facet_ids=(f"{_DIM}:{i}",),
                source_sample_ids=(f"train:{i}",),
                provenance_refs=(f"sample:train:{i}",),
            )
            for i in intents
        ),
    ).validate()


def _recall(scores: dict[str, float]) -> dict[str, dict[str, float]]:
    return {facet_id: {_DIM: score} for facet_id, score in scores.items()}


def _with_agreement(
    recall: dict[str, dict[str, float]], shares: dict[str, float]
) -> dict[str, dict[str, float]]:
    return {
        facet_id: {**dims, EXEMPLAR_INTENT_AGREEMENT_DIMENSION: shares.get(facet_id, 0.0)}
        for facet_id, dims in recall.items()
    }


def _query_state(sample_id: str = "slurp:train:000007:audio--1") -> QueryState:
    return QueryState(
        query_id=f"q:{sample_id}",
        query_sample_id=sample_id,
        speech_packet_id="packet",
        speech_packet_sha256=_SHA,
        use_split_identity_hash=_SHA,
    ).validate()


def _pre_change_ranking(recall_scores, weights) -> list[tuple[str, float]]:
    """The ranker's EXACT pre-change expression, transcribed from the commit
    that introduced the agreement term. If this stops matching the shipped
    ranker on a recall with no agreement dimension, the identity claim is dead
    and the locked cell has moved."""

    dims_total = len({dim for scores in recall_scores.values() for dim in scores})
    sups: dict[str, float] = {}
    for dim_scores in recall_scores.values():
        for dimension, score in dim_scores.items():
            sups[dimension] = max(sups.get(dimension, float(score)), float(score))
    scales = {dim: (sup if sup > 1.0 else 1.0) for dim, sup in sups.items()}
    ranked: list[tuple[str, float]] = []
    for facet_id, dim_scores in recall_scores.items():
        cosine_scores = [
            float(score) / scales[dim]
            for dim, score in dim_scores.items()
            if dim not in kb_policy.PRIOR_MASS_DIMENSIONS
        ]
        prior_scores = [
            float(score) / scales[dim]
            for dim, score in dim_scores.items()
            if dim in kb_policy.PRIOR_MASS_DIMENSIONS
        ]
        ranked.append(
            (
                facet_id,
                weights.w_cos * (max(cosine_scores) if cosine_scores else 0.0)
                + weights.w_prior * (max(prior_scores) if prior_scores else 0.0)
                + weights.w_agree * (len(dim_scores) / dims_total if dims_total else 0.0),
            )
        )
    ranked.sort(key=lambda item: (-item[1], item[0]))
    return ranked


def _ranked(result) -> list[tuple[str, float]]:
    return [(candidate.facet_id, candidate.score) for candidate in result.candidates]


# ---------------------------------------------------------------------------
# 1. the default is byte-identical
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "weights",
    [
        RankWeights(w_cos=1.0, w_prior=0.0, w_agree=0.0),
        RankWeights(w_cos=1.0, w_prior=0.0, w_agree=1.0),
        RankWeights(w_cos=0.5, w_prior=0.3, w_agree=0.2),
        RankWeights(w_cos=0.0, w_prior=0.0, w_agree=2.0),
    ],
)
def test_no_agreement_dimension_is_bit_identical_to_the_pre_change_ranker(weights):
    """The identity the whole registration rests on: a recall carrying no
    agreement dimension ranks EXACTLY as it did before the term existed, at any
    weighting -- including a non-zero ``w_agree``, which still reads the legacy
    cross-dimension fraction."""

    recall = {
        "facet:content:1": {"content": 0.90, "speaker": 0.10},
        "facet:content:2": {"content": 0.80},
        "facet:label:1": {"label": 0.50},
        "facet:content:3": {"content": 0.80, "speaker": 0.40, "label": 0.10},
    }
    got = _ranked(
        rank_wcos_prior_agree_factory(weights)(
            snapshot_sha256=_SHA, query_state=_query_state(), recall_scores=recall
        )
    )
    assert got == _pre_change_ranking(recall, weights)


def test_the_flown_boundary_channel_default_is_bit_identical():
    """The one-dimension, 60-way channel this change targets, at its flown
    weights. The legacy agreement term is the constant 1.0 there, so it cannot
    move the order -- which is exactly why replacing it costs nothing."""

    weights = RankWeights(w_cos=1.0, w_prior=0.0, w_agree=0.0)
    recall = _recall({f"{_DIM}:i{n:02d}": 0.9 - n / 100 for n in range(60)})
    result = rank_wcos_prior_agree_factory(weights)(
        snapshot_sha256=_SHA, query_state=_query_state(), recall_scores=recall
    )
    assert _ranked(result) == _pre_change_ranking(recall, weights)
    # the whole contract object, not just the order
    assert result.content_hash() == result.validate().content_hash()
    assert all(
        candidate.score == pytest.approx(recall[candidate.facet_id][_DIM], abs=0.0)
        for candidate in result.candidates
    )


def test_cosine_dimension_items_is_the_identity_without_an_agreement_dimension():
    dim_scores = {"content": 0.9, "label": 0.5, "speaker": 0.2}
    assert cosine_dimension_items(dim_scores) == [("content", 0.9), ("speaker", 0.2)]
    with_agreement = {**dim_scores, EXEMPLAR_INTENT_AGREEMENT_DIMENSION: 1.0}
    assert cosine_dimension_items(with_agreement) == [("content", 0.9), ("speaker", 0.2)]


def test_the_agreement_dimension_is_not_a_percept_admission_cosine():
    """A facet whose ONLY positive score is its agreement share must not pass a
    cosine floor: the fuser's admission asks whether the speech matched the key,
    and an agreement share is not that evidence."""

    snapshot = _boundary_snapshot()
    fuser = fuse_associated_values_factory(FuseKnobs(tau=0.5, m=3, c=1, top_l=3))
    recall = {
        f"{_DIM}:a": {_DIM: 0.9, EXEMPLAR_INTENT_AGREEMENT_DIMENSION: 0.0},
        f"{_DIM}:b": {_DIM: 0.1, EXEMPLAR_INTENT_AGREEMENT_DIMENSION: 1.0},
    }
    rank_result = rank_wcos_prior_agree_factory(
        RankWeights(w_cos=1.0, w_prior=0.0, w_agree=1.0)
    )(snapshot_sha256=_SHA, query_state=_query_state(), recall_scores=recall)
    # the agreement term puts b on top of the RANKING ...
    assert rank_result.candidates[0].facet_id == f"{_DIM}:b"
    decision = fuser(
        snapshot=snapshot,
        snapshot_sha256=_SHA,
        query_state=_query_state(),
        rank_result=rank_result,
        recall_scores=recall,
    )
    # ... and yet only a's cosine clears tau, so only a's value is supplied.
    assert decision.selected_value_ids == (f"{_DIM}:a",)


# ---------------------------------------------------------------------------
# 5. tie stability
# ---------------------------------------------------------------------------


def test_ties_break_on_facet_id_ascending_with_and_without_the_agreement_term():
    flat = _recall({f"{_DIM}:c": 0.5, f"{_DIM}:a": 0.5, f"{_DIM}:b": 0.5})
    ranker = rank_wcos_prior_agree_factory(RankWeights(w_cos=1.0, w_prior=0.0, w_agree=1.0))
    plain = ranker(snapshot_sha256=_SHA, query_state=_query_state(), recall_scores=flat)
    assert [c.facet_id for c in plain.candidates] == [f"{_DIM}:a", f"{_DIM}:b", f"{_DIM}:c"]
    # equal cosines AND equal shares: still facet_id ascending
    tied = _with_agreement(flat, {f"{_DIM}:a": 0.5, f"{_DIM}:b": 0.5, f"{_DIM}:c": 0.5})
    supplied = ranker(snapshot_sha256=_SHA, query_state=_query_state(), recall_scores=tied)
    assert [c.facet_id for c in supplied.candidates] == [
        f"{_DIM}:a",
        f"{_DIM}:b",
        f"{_DIM}:c",
    ]
    # and the order is invariant under the insertion order of the recall
    for permutation in itertools.permutations(sorted(tied)):
        shuffled = {key: tied[key] for key in permutation}
        assert [
            c.facet_id
            for c in ranker(
                snapshot_sha256=_SHA, query_state=_query_state(), recall_scores=shuffled
            ).candidates
        ] == [f"{_DIM}:a", f"{_DIM}:b", f"{_DIM}:c"]


def test_the_agreement_term_promotes_a_lower_cosine_candidate_it_agrees_with():
    """The mechanism itself: at ``w_agree`` 1.0 a candidate the exemplar vote
    concentrates on overtakes a higher-cosine candidate it does not. This is the
    reranking the 2026-09-26 read measured; the test asserts only that it
    happens, never a score effect."""

    recall = _recall({f"{_DIM}:a": 0.40, f"{_DIM}:b": 0.30, f"{_DIM}:c": 0.20})
    ranker = rank_wcos_prior_agree_factory(RankWeights(w_cos=1.0, w_prior=0.0, w_agree=1.0))
    without = ranker(
        snapshot_sha256=_SHA, query_state=_query_state(), recall_scores=recall
    )
    assert [c.facet_id for c in without.candidates][0] == f"{_DIM}:a"
    voted = _with_agreement(recall, {f"{_DIM}:c": 0.75, f"{_DIM}:a": 0.25})
    with_vote = ranker(
        snapshot_sha256=_SHA, query_state=_query_state(), recall_scores=voted
    )
    assert [c.facet_id for c in with_vote.candidates][0] == f"{_DIM}:c"
    # a zero-vote candidate keeps exactly its cosine: the term adds, never scales
    assert dict(_ranked(with_vote))[f"{_DIM}:b"] == pytest.approx(0.30, abs=0.0)


# ---------------------------------------------------------------------------
# 4. a missing input refuses; a zero vote is a measurement
# ---------------------------------------------------------------------------


def _provider(agreement=None) -> KbFacetProvider:
    provider = KbFacetProvider(
        build_spec=None,
        rank_policy_id=kb_policy.RANK_POLICY_ID,
        rank_weights=RankWeights(w_cos=1.0, w_prior=0.0, w_agree=1.0),
        fuse_knobs=FuseKnobs(tau=0.0, m=3, c=1, top_l=3),
        top_k_per_dimension=3,
        facet_vectors=lambda facet_id: {_DIM: (1.0, 0.0)},
        agreement_scores=agreement,
    )
    return provider.adopt(
        _boundary_snapshot(), policy_id="frozen-snapshot:test", snapshot_sha256=_SHA
    )


def test_a_row_absent_from_the_agreement_table_is_refused_not_scored_zero():
    provider = _provider({"slurp:train:000007:audio--1": {f"{_DIM}:a": 1.0}})
    with pytest.raises(RailsError, match="has no row for query sample"):
        provider.candidates(
            {
                "query_state": _query_state("slurp:train:000099:audio--9"),
                "query_vectors": {_DIM: (1.0, 0.0)},
            },
            k=3,
        )


def test_a_recalled_facet_with_no_share_is_a_zero_vote_not_a_refusal():
    provider = _provider({"slurp:train:000007:audio--1": {f"{_DIM}:a": 1.0}})
    ranking = provider.candidates(
        {"query_state": _query_state(), "query_vectors": {_DIM: (1.0, 0.0)}}, k=3
    )
    scores = {entry.entry_id: entry.score for entry in ranking.entries}
    # a recalled the whole vote, b and c none of it; all three still ranked
    assert scores[f"{_DIM}:a"] > scores[f"{_DIM}:b"]
    assert scores[f"{_DIM}:b"] == pytest.approx(scores[f"{_DIM}:c"], abs=0.0)


def test_no_agreement_table_leaves_the_recall_object_untouched():
    provider = _provider(None)
    ranking = provider.candidates(
        {"query_state": _query_state(), "query_vectors": {_DIM: (1.0, 0.0)}}, k=3
    )
    recall = provider._last_recall_scores
    assert all(
        not (set(dims) & AGREEMENT_DIMENSIONS) for dims in recall.values()
    ), "a provider with no agreement signal must not synthesise one"
    assert len(ranking.entries) == 3


@pytest.mark.parametrize(
    "bad",
    [
        {"s": {"f": 1.5}},
        {"s": {"f": -0.1}},
        {"s": {"f": True}},
        {"s": {"f": float("nan")}},
        {"s": {"": 0.5}},
        {"s": "not a mapping"},
        {"": {"f": 0.5}},
    ],
)
def test_an_out_of_range_or_malformed_agreement_table_is_refused_at_construction(bad):
    with pytest.raises(RailsError):
        _provider(bad)


def test_an_unreserved_agreement_dimension_is_refused():
    with pytest.raises(RailsError, match="AGREEMENT_DIMENSIONS"):
        KbFacetProvider(
            build_spec=None,
            rank_weights=RankWeights(w_cos=1.0, w_prior=0.0, w_agree=1.0),
            top_k_per_dimension=3,
            agreement_dimension="content",
        )


# ---------------------------------------------------------------------------
# the loader's fail-closed contract
# ---------------------------------------------------------------------------


def _agreement_file(tmp_path: Path, rows: list[dict]) -> tuple[Path, str]:
    payload = "".join(
        json.dumps(row, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")
    path = tmp_path / "agreement.jsonl"
    path.write_bytes(payload)
    return path, hashlib.sha256(payload).hexdigest()


def _row(sample_id: str, shares: dict[str, float], *, total: int = 20, dropped: int = 0):
    return {
        "schema": SEALED_AGREEMENT_SCHEMA,
        "id": sample_id,
        "dimension": EXEMPLAR_INTENT_AGREEMENT_DIMENSION,
        "scores": shares,
        "vote_total": total,
        "self_excluded": dropped,
    }


def test_load_sealed_agreement_round_trips_and_binds_its_hash(tmp_path):
    rows = [
        _row("s1", {f"{_DIM}:a": 0.75, f"{_DIM}:b": 0.25}),
        _row("s2", {f"{_DIM}:c": 1.0}, dropped=2),
    ]
    path, sha = _agreement_file(tmp_path, rows)
    table = load_sealed_agreement(
        path,
        expected_sha256=sha,
        dimension=EXEMPLAR_INTENT_AGREEMENT_DIMENSION,
        facet_ids=[f"{_DIM}:a", f"{_DIM}:b", f"{_DIM}:c"],
    )
    assert table == {
        "s1": {f"{_DIM}:a": 0.75, f"{_DIM}:b": 0.25},
        "s2": {f"{_DIM}:c": 1.0},
    }
    with pytest.raises(PhaseSupplyError, match="hashes to"):
        load_sealed_agreement(
            path, expected_sha256="0" * 64, dimension=EXEMPLAR_INTENT_AGREEMENT_DIMENSION
        )


@pytest.mark.parametrize(
    "rows, match",
    [
        ([_row("s1", {f"{_DIM}:a": 0.5})], "shares sum to"),
        ([_row("s1", {f"{_DIM}:a": 1.0}), _row("s1", {f"{_DIM}:b": 1.0})], "duplicate id"),
        ([_row("s1", {f"{_DIM}:a": 1.0}, total=0)], "no votes yet carries shares"),
        ([_row("s1", {f"{_DIM}:a": 1.0}, dropped=-1)], "non-negative integer"),
        ([_row("s1", {f"{_DIM}:a": 1.2})], "within"),
        ([{**_row("s1", {f"{_DIM}:a": 1.0}), "schema": "other-v1"}], "declares schema"),
        ([{**_row("s1", {f"{_DIM}:a": 1.0}), "dimension": "content"}], "declares dimension"),
        ([], "no agreement rows"),
    ],
)
def test_load_sealed_agreement_is_fail_closed(tmp_path, rows, match):
    path, sha = _agreement_file(tmp_path, rows)
    with pytest.raises(PhaseSupplyError, match=match):
        load_sealed_agreement(
            path, expected_sha256=sha, dimension=EXEMPLAR_INTENT_AGREEMENT_DIMENSION
        )


def test_load_sealed_agreement_refuses_a_facet_the_target_snapshot_lacks(tmp_path):
    path, sha = _agreement_file(tmp_path, [_row("s1", {f"{_DIM}:zz": 1.0})])
    with pytest.raises(PhaseSupplyError, match="does not declare"):
        load_sealed_agreement(
            path,
            expected_sha256=sha,
            dimension=EXEMPLAR_INTENT_AGREEMENT_DIMENSION,
            facet_ids=[f"{_DIM}:a"],
        )


# ---------------------------------------------------------------------------
# the spec: the pin is agreement-only, and it needs a weight to read it
# ---------------------------------------------------------------------------


def _spec(**overrides) -> dict:
    spec = {
        "phase": "perception",
        "provider": "kb-facet-v1",
        "rank_policy": kb_policy.RANK_POLICY_ID,
        "fuse_policy": kb_policy.ASSOCIATED_VALUES_FUSE_POLICY_ID,
        "k": 8,
        "tau": 0.0,
        "dimensions": (_DIM,),
        "query_source": {
            "kind": "sealed-vectors",
            "relpath": "vectors/q.jsonl",
            "sha256": _SHA,
            "tool_contact_ledger_row": "ROW",
            "embedded_signal": "speech: the row's own sealed utterance vector",
        },
        "rank_weights": {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 1.0},
        "fuse_coverage": {"m": 8, "c": 1, "top_l": 8},
    }
    spec.update(overrides)
    return spec


_AGREEMENT_PIN = {
    "kind": "sealed-agreement",
    "relpath": "prepared/X/agreement.jsonl",
    "sha256": _SHA,
    "tool_contact_ledger_row": "ROW",
    "embedded_signal": "derived: the row's own self-excluded exemplar-intent vote",
}


def test_a_spec_may_declare_an_agreement_source_and_it_enters_the_identity():
    with_pin = PhaseSupplySpec(**_spec(agreement_source=_AGREEMENT_PIN)).validate()
    without = PhaseSupplySpec(**_spec()).validate()
    assert with_pin.as_json()["agreement_source"] == _AGREEMENT_PIN
    # and an undeclared pin adds NO key, so every existing cell's identity view
    # is byte-unchanged (PhaseSupplySpec.as_json docstring)
    assert "agreement_source" not in without.as_json()


def test_the_agreement_kind_is_agreement_only():
    with pytest.raises(PhaseSupplyError, match="agreement-only"):
        PhaseSupplySpec(**_spec(query_source=_AGREEMENT_PIN)).validate()
    with pytest.raises(PhaseSupplyError, match="must be 'sealed-agreement'"):
        PhaseSupplySpec(
            **_spec(
                agreement_source={
                    **_AGREEMENT_PIN,
                    "kind": "sealed-vectors",
                }
            )
        ).validate()


def test_an_agreement_source_with_no_explicit_rank_weights_is_refused():
    spec = _spec(agreement_source=_AGREEMENT_PIN)
    spec.pop("rank_weights")
    with pytest.raises(PhaseSupplyError, match="requires explicit rank_weights"):
        PhaseSupplySpec(**spec).validate()


# ---------------------------------------------------------------------------
# the pre-flight prompt bound must count what the fuser DELIVERS
# ---------------------------------------------------------------------------


def _prompt_bound(*, k: int, top_l: int, fuse_policy: str) -> int:
    """``len(blocks)`` from ``FlightRuntime._phase_supply_prompt_bound`` for a
    one-phase stub, called unbound so the test needs no repo and no data root."""

    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    from speech_aware_evidence_acquisition.rails import controllers as rc

    program = rc.default_phase_program("phase-direct-evidence-alpha-blend-v1")
    snapshot = KnowledgeSnapshot(
        snapshot_id="bound-test-v1",
        source_split_identity_hash=_SHA,
        source_sample_ids=tuple(f"train:{n}" for n in range(60)),
        builder_policy_id="test-builder-v1",
        facets=tuple(
            KeyFacet(f"facet:content:{n}", "content", "text", "k" * (10 + n), (f"train:{n}",))
            for n in range(60)
        ),
        values=tuple(
            ValueBundle(
                value_id=f"value:{n}",
                content="v" * (10 + n),
                associated_facet_ids=(f"facet:content:{n}",),
                source_sample_ids=(f"train:{n}",),
                provenance_refs=(f"sample:train:{n}",),
            )
            for n in range(60)
        ),
    ).validate()
    stub = SimpleNamespace(
        _composed=SimpleNamespace(
            values={
                "phase_supply": {
                    "evidence": {
                        "provider": "kb-facet-v1",
                        "rank_policy": kb_policy.RANK_POLICY_ID,
                        "fuse_policy": fuse_policy,
                        "k": k,
                        "tau": 0.0,
                        "dimensions": ["content"],
                        "expose_facets": False,
                        "fuse_coverage": {"m": 8, "c": 1, "top_l": top_l},
                        "query_source": {
                            "kind": "sealed-vectors",
                            "relpath": "v/q.jsonl",
                            "sha256": _SHA,
                            "tool_contact_ledger_row": "TEST-EMB-0001",
                            "embedded_signal": "speech: synthetic",
                        },
                    }
                }
            }
        ),
        _load_knowledge_snapshot=lambda: snapshot,
    )
    return len(FlightRuntime._phase_supply_prompt_bound(stub, program)["evidence"])


def test_the_prompt_bound_counts_the_delivered_width_under_the_associated_fuser():
    """THE DEFECT THIS PINS. The bound counted ``k`` values -- the RECALL width
    -- which was the delivered width in every cell committed before the
    agreement cell, and is 7.5x too many for a cell that recalls 60 and delivers
    8. Counting a request at 30,309 tokens when its own prepared artifact carries
    8 value ids per row is not conservatism, it is a wrong refusal."""

    assert _prompt_bound(
        k=60, top_l=8, fuse_policy=kb_policy.ASSOCIATED_VALUES_FUSE_POLICY_ID
    ) == 8


@pytest.mark.parametrize("k, top_l", [(8, 8), (16, 16), (60, 61)])
def test_the_narrowing_is_an_identity_on_every_committed_shape(k, top_l):
    """Of the committed specs using this fuser, 171 declare k = top_l = 8, two
    declare 16 = 16 and one declares k = 60 with top_l = 61, so ``min`` returns
    ``k`` in every one of them and no existing bound moves."""

    assert _prompt_bound(
        k=k, top_l=top_l, fuse_policy=kb_policy.ASSOCIATED_VALUES_FUSE_POLICY_ID
    ) == k


def test_every_other_fuser_keeps_the_recall_width_as_its_bound():
    """``saea-fuse-supplyfilter-v1`` selects up to ``c`` values per
    ``task_target`` over ``top_l`` targets and one facet may carry several
    values, so ``top_l`` is not a cap for it and narrowing there could
    UNDER-count. It is deliberately left alone."""

    assert _prompt_bound(k=60, top_l=8, fuse_policy=kb_policy.FUSE_POLICY_ID) == 60
