"""The ``ValueBundle.prior_score`` range contract, and the corrected
conditional prior in both knowledge builders.

Row ``SAEA-SN-MF-PRIOR-SCORE-SEMANTICS-REPAIR``; verdict
``docs/readiness/2026-08-25-prior-score-semantics-repair.md``.

Two things are under test and they pull in opposite directions, which is the
whole reason the contract needed designing rather than asserting:

* CONSTRUCTION must refuse a non-probability fail-closed, so the defect that
  produced a supremum of 4.1 on Audio2Tool cannot be re-introduced silently;
* LOADING a snapshot frozen BEFORE the contract existed must still work, with
  the violation recorded, because those bytes are the record of what actually
  flew and every landed replay reads them.

Every test here is MODEL-FREE, network-free and filesystem-free: the corpora
are synthetic rows built in-process.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.knowledge import (
    PRIOR_SCORE_MAX,
    PRIOR_SCORE_MIN,
    KeyFacet,
    KnowledgeSnapshot,
    ValueBundle,
    assert_prior_scores_are_probabilities,
    prior_score_range_violation,
)
from speech_aware_evidence_acquisition.rails.knowledge_build import (
    KbRow,
    KnowledgeBuildSpec,
    build_knowledge_snapshot,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (
    A2tKbRow,
    A2tKnowledgeBuildSpec,
    build_a2t_knowledge_snapshot,
)

_SHA = "a" * 64


# ---------------------------------------------------------------------------
# The classifier
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [None, 0.0, -0.0, 0.5, 1.0, 0, 1])
def test_in_range_prior_scores_are_not_violations(value) -> None:
    assert prior_score_range_violation(value) is None


@pytest.mark.parametrize("value", [1.0000001, 4.1, 2, -0.5, -1])
def test_out_of_range_prior_scores_are_violations(value) -> None:
    assert prior_score_range_violation(value) == pytest.approx(float(value))


def test_the_range_is_the_unit_interval_and_is_not_a_knob() -> None:
    assert (PRIOR_SCORE_MIN, PRIOR_SCORE_MAX) == (0.0, 1.0)


# ---------------------------------------------------------------------------
# Fixtures: a snapshot whose prior_score is under the caller's control
# ---------------------------------------------------------------------------


def _snapshot(prior_score: float | None) -> KnowledgeSnapshot:
    """A minimal but fully valid snapshot. Note that CONSTRUCTING it never
    raises whatever ``prior_score`` says -- the dataclass invariant stays
    'finite', deliberately, so that a historical document can be
    reconstructed and re-hashed."""

    return KnowledgeSnapshot(
        snapshot_id="prior-contract-fixture",
        source_split_identity_hash=_SHA,
        source_sample_ids=("train:s0",),
        builder_policy_id="test-prior-contract-v1",
        facets=(
            KeyFacet("facet:label:t0", "label", "text", "tool_0", ("train:s0",)),
        ),
        values=(
            ValueBundle(
                value_id="value:v0",
                content="one exemplar",
                associated_facet_ids=("facet:label:t0",),
                source_sample_ids=("train:s0",),
                provenance_refs=("sample:train:s0",),
                task_target="tool_0",
                prior_score=prior_score,
            ),
        ),
    ).validate()


def _pre_contract_frozen_document(snapshot: KnowledgeSnapshot) -> dict:
    """Exactly what ``frozen_json`` produced BEFORE the range contract: the
    canonical document plus its own hash, with no range gate in between.
    This is how the pinned Audio2Tool snapshot ``ec2f9ec4...9fb2`` came to
    exist, and reproducing it here is the only honest way to test that such a
    document still loads."""

    document = snapshot.as_json()
    return {**document, "snapshot_sha256": content_hash(document)}


# ---------------------------------------------------------------------------
# Side one: construction refuses, fail-closed
# ---------------------------------------------------------------------------


def test_the_construction_gate_accepts_probabilities() -> None:
    assert_prior_scores_are_probabilities(
        _snapshot(0.25).values, builder="unit-test"
    )
    assert_prior_scores_are_probabilities(
        _snapshot(None).values, builder="unit-test"
    )


@pytest.mark.parametrize("value", [4.1, 1.0000001, -0.5])
def test_the_construction_gate_refuses_a_non_probability(value: float) -> None:
    with pytest.raises(RailsError, match="prior_score must be a probability"):
        assert_prior_scores_are_probabilities(
            _snapshot(value).values, builder="unit-test"
        )


def test_freezing_a_snapshot_with_an_out_of_range_prior_is_refused() -> None:
    """The durable-bytes gate. ``frozen_json`` is the ONLY point at which a
    snapshot becomes a content-addressed artifact, so it is where a
    non-probability is stopped from ever acquiring a hash."""

    snapshot = _snapshot(4.1)
    with pytest.raises(RailsError, match="prior_score must be a probability"):
        snapshot.frozen_json()


def test_freezing_an_in_range_snapshot_is_unaffected() -> None:
    snapshot = _snapshot(0.5)
    frozen = snapshot.frozen_json()
    assert frozen["snapshot_sha256"] == snapshot.content_hash()
    assert snapshot.prior_score_range_violations() == ()


def test_the_gate_names_the_offending_values() -> None:
    snapshot = _snapshot(4.1)
    with pytest.raises(RailsError) as excinfo:
        snapshot.frozen_json()
    assert "value:v0" in str(excinfo.value)
    assert "4.1" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Side two: a historical snapshot still loads, and the violation is recorded
# ---------------------------------------------------------------------------


def test_a_historical_out_of_range_snapshot_still_loads() -> None:
    """THE REQUIREMENT THAT SHAPED THE DESIGN. The pinned Audio2Tool snapshot
    reaches 4.1. If loading refused, every landed replay and every future
    audit of what actually flew would break -- a worse failure than the defect
    being audited."""

    document = _pre_contract_frozen_document(_snapshot(4.1))
    with pytest.warns(RuntimeWarning, match="HISTORICAL"):
        loaded = KnowledgeSnapshot.from_frozen_json(document)
    assert loaded.content_hash() == document["snapshot_sha256"]
    assert loaded.values[0].prior_score == pytest.approx(4.1)


def test_a_historical_load_records_the_violation_explicitly() -> None:
    document = _pre_contract_frozen_document(_snapshot(4.1))
    with pytest.warns(RuntimeWarning):
        loaded = KnowledgeSnapshot.from_frozen_json(document)
    recorded = loaded.historical_prior_score_range_violations
    assert len(recorded) == 1
    value_id, score = recorded[0]
    assert value_id == "value:v0"
    assert score == pytest.approx(4.1)


def test_an_in_range_historical_load_records_nothing_and_does_not_warn() -> None:
    document = _pre_contract_frozen_document(_snapshot(0.5))
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        loaded = KnowledgeSnapshot.from_frozen_json(document)
    assert loaded.historical_prior_score_range_violations == ()


def test_a_loaded_historical_snapshot_cannot_be_re_frozen() -> None:
    """The boundary is one-directional: violating bytes may come IN and be
    labelled; none may go OUT."""

    document = _pre_contract_frozen_document(_snapshot(4.1))
    with pytest.warns(RuntimeWarning):
        loaded = KnowledgeSnapshot.from_frozen_json(document)
    with pytest.raises(RailsError, match="prior_score must be a probability"):
        loaded.frozen_json()


def test_recording_the_violation_does_not_perturb_snapshot_identity() -> None:
    """The record is a non-field instance attribute, exactly like
    ``_validated``, so a loaded snapshot still hashes and compares as the
    document says it does."""

    document = _pre_contract_frozen_document(_snapshot(4.1))
    with pytest.warns(RuntimeWarning):
        loaded = KnowledgeSnapshot.from_frozen_json(document)
    assert loaded.as_json() == {
        key: value for key, value in document.items() if key != "snapshot_sha256"
    }
    assert loaded == _snapshot(4.1)


# ---------------------------------------------------------------------------
# The corrected computation: SLURP
# ---------------------------------------------------------------------------


def _slurp_row(utterance_id: str, *, scenario: str, intent: str, words: str) -> KbRow:
    """A KbRow whose ``intent`` is supplied INDEPENDENTLY of its scenario.

    The production loader builds ``intent = f"{scenario}_{action}"``, which is
    exactly the nesting that made the old unconditioned ratio accidentally
    correct. Decoupling them here is what lets the test see the difference the
    repair makes."""

    sample_id = f"slurp:train:{utterance_id}:audio-{utterance_id}"
    return KbRow(
        utterance_id=utterance_id,
        content=words,
        scenario=scenario,
        action=intent.split("_", 1)[-1],
        intent=intent,
        entity_types=(),
        entity_fillers={},
        sample_ids=(sample_id,),
        speaker_by_sample_id={sample_id: "speaker-0"},
        media_relpath_by_sample_id={sample_id: f"datasets/slurp/{utterance_id}.flac"},
    )


def _non_nesting_slurp_rows() -> tuple[KbRow, ...]:
    """One intent spanning TWO scenarios: ten rows under ``wide`` and one
    under ``narrow``. Under the OLD expression the ``narrow`` row's prior was
    ``11 / 1 = 11.0``."""

    rows = [
        _slurp_row(f"w{i}", scenario="wide", intent="shared_intent", words=f"wide utterance {i}")
        for i in range(10)
    ]
    rows.append(
        _slurp_row("n0", scenario="narrow", intent="shared_intent", words="narrow utterance")
    )
    return tuple(rows)


def _nesting_slurp_rows() -> tuple[KbRow, ...]:
    """The production label scheme: ``intent = f"{scenario}_{action}"``, so an
    intent strictly determines its scenario."""

    return tuple(
        _slurp_row(
            f"{scenario}-{action}-{index}",
            scenario=scenario,
            intent=f"{scenario}_{action}",
            words=f"{scenario} {action} utterance {index}",
        )
        for scenario, actions in (("alarm", ("set", "query")), ("news", ("query",)))
        for action in actions
        for index in range(4)
    )


def _build_slurp(rows: tuple[KbRow, ...]) -> KnowledgeSnapshot:
    return build_knowledge_snapshot(
        KnowledgeBuildSpec(carrier_lock_key="slurp"),
        rows=rows,
        forbidden_sample_ids=frozenset({"slurp:devel:absent:audio-absent"}),
    )


def test_the_slurp_builder_refuses_a_non_nesting_label_scheme_outright() -> None:
    """A SECOND, INDEPENDENT PLACE THE NESTING IS STRUCTURAL, found while
    writing this test rather than assumed.

    The SLURP builder emits ONE label facet per intent, parented by
    ``scenario -> action``. An intent appearing under two scenarios therefore
    produces a duplicate ``facet_id`` and the snapshot refuses to validate --
    before any prior is read. So the nesting is not merely what made the old
    prior expression accidentally correct; the whole SLURP KB shape depends on
    it. The corrected prior expression does not depend on it: it conditions
    whether or not the labels nest, which is the point of the repair."""

    with pytest.raises(RailsError, match="duplicate facet_id"):
        _build_slurp(_non_nesting_slurp_rows())


def test_slurp_prior_is_a_genuine_conditional_probability() -> None:
    """Two intents inside one scenario, in a 3:1 ratio."""

    rows = tuple(
        [
            _slurp_row(f"a{i}", scenario="s", intent="s_alpha", words=f"alpha {i}")
            for i in range(6)
        ]
        + [
            _slurp_row(f"b{i}", scenario="s", intent="s_beta", words=f"beta {i}")
            for i in range(2)
        ]
    )
    snapshot = _build_slurp(rows)
    priors = {
        value.value_id: value.prior_score
        for value in snapshot.values
        if value.prior_score is not None
    }
    assert priors["value:a0"] == pytest.approx(0.75)
    assert priors["value:b0"] == pytest.approx(0.25)


def test_slurp_prior_is_unchanged_when_intent_nests_inside_scenario() -> None:
    """THE IDENTITY. With the production label scheme
    ``intent = f"{scenario}_{action}"`` the restricted numerator is the SAME
    SET as the unrestricted one, so the repair moves nothing. Both counts are
    recomputed here from the rows and compared."""

    rows = _nesting_slurp_rows()
    by_intent: dict[str, list[KbRow]] = {}
    by_scenario: dict[str, list[KbRow]] = {}
    for row in rows:
        by_intent.setdefault(row.intent, []).append(row)
        by_scenario.setdefault(row.scenario, []).append(row)
    for intent, intent_rows in by_intent.items():
        scenario = intent_rows[0].scenario
        restricted = [row for row in by_scenario[scenario] if row.intent == intent]
        assert {row.utterance_id for row in restricted} == {
            row.utterance_id for row in intent_rows
        }, f"intent {intent!r} does not nest inside its scenario"

    snapshot = _build_slurp(rows)
    priors = {
        value.value_id: value.prior_score
        for value in snapshot.values
        if value.prior_score is not None
    }
    assert priors["value:alarm-set-0"] == pytest.approx(0.5)
    assert priors["value:news-query-0"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# The corrected computation: Audio2Tool
# ---------------------------------------------------------------------------


_A2T_REGISTRY = {
    name: {
        "tool_id": "0",
        "domain": "d",
        "category": "c",
        "tool_name": name,
        "signature": f"{name}()",
        "description": f"Synthetic description of {name}.",
        "argument_defaults": "",
        "argument_constraints": "",
    }
    for name in ("sharedTool", "otherTool")
}


def _a2t_row(
    tier: str,
    query_idx: int,
    *,
    tool: str,
    domain: str,
    category: str,
    words: str,
) -> A2tKbRow:
    sample_ids = (f"{tier}:{query_idx:06d}",)
    return A2tKbRow(
        unit_id=f"{tier}:{query_idx:06d}",
        tier=tier,
        query_idx=query_idx,
        text=words,
        domain=domain,
        category=category,
        tool_id=0,
        tool_name=tool,
        arg_signature=(),
        arg_pairs=(),
        call_render=f"{tool}()",
        extra_call_names=(),
        call_count=1,
        sample_ids=sample_ids,
        item_ids=(query_idx,),
        media_relpath_by_sample_id={sid: f"audio/{sid}.wav" for sid in sample_ids},
        speaker_ids=("voice_a",),
    )


def _cross_category_a2t_rows() -> tuple[A2tKbRow, ...]:
    """``sharedTool`` appears ten times in ``(home, wide)`` and once in
    ``(car, narrow)``. Under the OLD expression the ``(car, narrow)`` row's
    prior was ``11 / 1 = 11.0``."""

    rows = [
        _a2t_row(
            "tier1_direct",
            100 + index,
            tool="sharedTool",
            domain="home",
            category="wide",
            words=f"home request number {index} for the shared tool please",
        )
        for index in range(10)
    ]
    rows.append(
        _a2t_row(
            "tier2_parametric",
            900,
            tool="sharedTool",
            domain="car",
            category="narrow",
            words="in the car, use the shared tool right now",
        )
    )
    return tuple(rows)


def _build_a2t(rows: tuple[A2tKbRow, ...]) -> KnowledgeSnapshot:
    return build_a2t_knowledge_snapshot(
        A2tKnowledgeBuildSpec(),
        rows=rows,
        registry=_A2T_REGISTRY,
        forbidden_sample_ids=frozenset({"tier9_absent:000001"}),
    )


def test_a2t_prior_conditions_on_the_domain_category_cell() -> None:
    snapshot = _build_a2t(_cross_category_a2t_rows())
    priors = {
        value.value_id: value.prior_score
        for value in snapshot.values
        if value.prior_score is not None
    }
    assert priors, "the build produced no prior-carrying values"
    assert max(priors.values()) <= PRIOR_SCORE_MAX
    assert priors["value:tier2_parametric:000900"] == pytest.approx(1.0)
    assert priors["value:tier1_direct:000100"] == pytest.approx(1.0)


def test_a2t_prior_is_a_genuine_conditional_probability() -> None:
    """Two tools inside one ``(domain, category)`` cell, in a 3:1 ratio."""

    rows = tuple(
        [
            _a2t_row(
                "tier1_direct",
                100 + index,
                tool="sharedTool",
                domain="home",
                category="wide",
                words=f"home shared request number {index} please now",
            )
            for index in range(6)
        ]
        + [
            _a2t_row(
                "tier1_direct",
                200 + index,
                tool="otherTool",
                domain="home",
                category="wide",
                words=f"home other request number {index} please now",
            )
            for index in range(2)
        ]
    )
    snapshot = _build_a2t(rows)
    priors = {
        value.value_id: value.prior_score
        for value in snapshot.values
        if value.prior_score is not None
    }
    assert priors["value:tier1_direct:000100"] == pytest.approx(0.75)
    assert priors["value:tier1_direct:000200"] == pytest.approx(0.25)


def test_a2t_priors_sum_to_one_over_each_domain_category_cell() -> None:
    """The defining property of a conditional distribution, and the one the
    pre-repair expression could not have: over the tools present in a cell,
    the distinct per-tool priors sum to exactly 1."""

    rows = _cross_category_a2t_rows() + tuple(
        _a2t_row(
            "tier1_direct",
            300 + index,
            tool="otherTool",
            domain="home",
            category="wide",
            words=f"home other request number {index} please now",
        )
        for index in range(5)
    )
    snapshot = _build_a2t(rows)
    by_cell: dict[tuple[str, str], dict[str, float]] = {}
    tool_by_unit = {row.unit_id: row for row in rows}
    for value in snapshot.values:
        if value.prior_score is None:
            continue
        row = tool_by_unit[value.value_id.removeprefix("value:")]
        by_cell.setdefault((row.domain, row.category), {})[row.tool_name] = float(
            value.prior_score
        )
    assert by_cell
    for cell, priors in by_cell.items():
        assert sum(priors.values()) == pytest.approx(1.0), cell


def test_both_builders_refuse_to_emit_a_non_probability() -> None:
    """The construction gate is wired into BOTH builders, not just into
    ``frozen_json``. Monkeypatched so the refusal is provoked without
    re-introducing the defect in source."""

    import speech_aware_evidence_acquisition.rails.knowledge_build as slurp_build
    import speech_aware_evidence_acquisition.rails.knowledge_build_a2t as a2t_build

    def _poison(builder_module, original):
        def _wrapped(*args, **kwargs):
            facets, values = original(*args, **kwargs)
            poisoned = tuple(
                ValueBundle(
                    value_id=value.value_id,
                    content=value.content,
                    associated_facet_ids=value.associated_facet_ids,
                    source_sample_ids=value.source_sample_ids,
                    provenance_refs=value.provenance_refs,
                    task_target=value.task_target,
                    prior_score=4.1,
                )
                for value in values
            )
            return facets, poisoned

        return _wrapped

    original_slurp = slurp_build._build_facets_and_values
    original_a2t = a2t_build._build_facets_and_values
    try:
        slurp_build._build_facets_and_values = _poison(slurp_build, original_slurp)
        with pytest.raises(RailsError, match="KB-BUILD: prior_score"):
            _build_slurp(_nesting_slurp_rows())
        a2t_build._build_facets_and_values = _poison(a2t_build, original_a2t)
        with pytest.raises(RailsError, match="KB-BUILD-A2T: prior_score"):
            _build_a2t(_cross_category_a2t_rows())
    finally:
        slurp_build._build_facets_and_values = original_slurp
        a2t_build._build_facets_and_values = original_a2t
