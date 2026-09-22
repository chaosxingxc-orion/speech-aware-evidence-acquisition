"""E36b: the Acquisition node's kind (a) re-query, repaired to SEARCH the released stores by the
Reviewer's findings with a discriminability rule, instead of filtering the Solver's own supply
(owner decisions 90 and 70; design note ``docs/superpowers/specs/
2026-09-22-e36b-findings-keyed-requery-design.md``).

Proves, over a synthetic snapshot and zero contacts:

1. the config loader: the two new keys (``acquisition.budget.max_items_per_acquisition`` and
   ``acquisition.retrieval``) are one module (refused half-armed), their own value bounds, and
   that the OFF form (both absent) composes a config byte-identical in effect to the pre-E36b
   tree (``NativeEpisodeConfig.max_items_per_acquisition`` / ``.acquisition_retrieval`` both
   ``None``, ``AcquisitionBudget.as_json()`` omitting the key entirely);
2. the runtime binding's ON path: inverse-document-frequency ranking, ``min_token_chars``,
   ``max_document_frequency``, ``exclude_visible_tokens``, the exclusion set honoured, the cap
   honoured, an empty result when nothing matches, determinism and the value-id tie-break;
3. a wire proof: the E32 ACQUIRE -> ACCEPT episode, re-run with the ON-path production binding,
   returns a NON-EMPTY item set (the E36 predecessor's own residual: the un-repaired binding
   always returns empty on this shape, because the excluded set and the re-run selection are the
   same ids).
"""

from __future__ import annotations

import math
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
)
from speech_aware_evidence_acquisition.rails import acquisition as acq
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.knowledge import ValueBundle
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_e18_acquisition_node import ACQUISITION_PHASE, PHASES, _armed_values, _loader_program
from test_e32_acquisition_phase_program import _wire_proof_values
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness

REPO_ROOT = Path(__file__).resolve().parents[2]
PROGRAM_ID = "phase-native-candidates-review-revise-acquire-v1"


def _value(value_id: str, content: str, *, facet: str = "intent-boundaries") -> ValueBundle:
    return ValueBundle(
        value_id=value_id,
        content=content,
        associated_facet_ids=(facet,),
        source_sample_ids=("s1",),
        provenance_refs=("prov:1",),
    )


def _build(native_config, supply_for_phase, *, snapshot=None, store_binding=None):
    fake_self = SimpleNamespace()
    if store_binding is not None:
        fake_self._knowledge_store_binding = store_binding
    return FlightRuntime._acquisition_requery_binding(
        fake_self, native_config, supply_for_phase, snapshot,
    )


def _retrieval(
    *, min_token_chars=1, max_document_frequency=1.0, exclude_visible_tokens=True,
):
    return {
        "policy": acq.KNOWLEDGE_REQUERY_RETRIEVAL_POLICY_ID,
        "min_token_chars": min_token_chars,
        "max_document_frequency": max_document_frequency,
        "exclude_visible_tokens": exclude_visible_tokens,
    }


def _armed_on(*, max_items=5, retrieval=None) -> SimpleNamespace:
    """The ON-path test double: an armed knowledge-requery config with both E36b keys set,
    permissive by default (``min_token_chars=1``, ``max_document_frequency=1.0``) so a test that
    is not ITSELF about a drop rule is not accidentally gated by one."""

    return SimpleNamespace(
        acquisition_policy_id=acq.KNOWLEDGE_REQUERY_POLICY_ID,
        max_items_per_acquisition=max_items,
        acquisition_retrieval=retrieval or _retrieval(),
    )


def _any_supply(phase_id, context):
    return None  # never called on the ON path


# ---------------------------------------------------------------------------
# 1. The config loader.
# ---------------------------------------------------------------------------


def _e36b_armed_values(*, max_items=5, retrieval=None):
    values = _armed_values(max_revisions=1)
    values["native_episode"]["acquisition"]["budget"]["max_items_per_acquisition"] = max_items
    values["native_episode"]["acquisition"]["retrieval"] = retrieval or _retrieval()
    return values


def test_the_off_form_composes_both_e36b_properties_as_none():
    values = _armed_values(max_revisions=1)
    parsed = load_native_episode_config(
        values, _loader_program(ceiling=7, phases=(*PHASES, ACQUISITION_PHASE)),
    )
    assert parsed.max_items_per_acquisition is None
    assert parsed.acquisition_retrieval is None
    assert "max_items_per_acquisition" not in parsed.acquisition_budget


def test_the_armed_form_populates_both_e36b_properties():
    values = _e36b_armed_values(max_items=3)
    parsed = load_native_episode_config(
        values, _loader_program(ceiling=7, phases=(*PHASES, ACQUISITION_PHASE)),
    )
    assert parsed.max_items_per_acquisition == 3
    assert parsed.acquisition_budget["max_items_per_acquisition"] == 3
    assert parsed.acquisition_retrieval == _retrieval()


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (
            lambda v: v["native_episode"]["acquisition"]["budget"].update(
                max_items_per_acquisition=3,
            ),
            "one module",
        ),
        (
            lambda v: v["native_episode"]["acquisition"].update(retrieval=_retrieval()),
            "one module",
        ),
    ],
)
def test_the_two_e36b_keys_are_one_module(mutate, match):
    values = _armed_values(max_revisions=1)
    mutate(values)
    with pytest.raises(ValueError, match=match):
        load_native_episode_config(
            values, _loader_program(ceiling=7, phases=(*PHASES, ACQUISITION_PHASE)),
        )


@pytest.mark.parametrize(
    ("max_items", "match"),
    [
        (0, "max_items_per_acquisition"),
        (-1, "max_items_per_acquisition"),
        (True, "max_items_per_acquisition"),
        (17, "max_items_per_acquisition"),
    ],
)
def test_max_items_per_acquisition_bounds(max_items, match):
    values = _e36b_armed_values(max_items=max_items)
    with pytest.raises(ValueError, match=match):
        load_native_episode_config(
            values, _loader_program(ceiling=7, phases=(*PHASES, ACQUISITION_PHASE)),
        )


@pytest.mark.parametrize(
    ("retrieval", "match"),
    [
        ({**_retrieval(), "policy": "saea-requery-ghost-v9"}, "not registered"),
        ({**_retrieval(), "min_token_chars": 0}, "min_token_chars"),
        ({**_retrieval(), "min_token_chars": True}, "min_token_chars"),
        ({**_retrieval(), "max_document_frequency": 0.0}, "max_document_frequency"),
        ({**_retrieval(), "max_document_frequency": 1.5}, "max_document_frequency"),
        ({**_retrieval(), "exclude_visible_tokens": 1}, "exclude_visible_tokens"),
    ],
)
def test_retrieval_value_bounds(retrieval, match):
    values = _e36b_armed_values(retrieval=retrieval)
    with pytest.raises(ValueError, match=match):
        load_native_episode_config(
            values, _loader_program(ceiling=7, phases=(*PHASES, ACQUISITION_PHASE)),
        )


def test_acquisition_budget_as_json_omits_the_key_when_none():
    assert acq.AcquisitionBudget(1, 0).as_json() == {
        "max_acquisitions_per_row": 1, "contact_budget": 0,
    }
    assert acq.AcquisitionBudget(1, 0, 5).as_json() == {
        "max_acquisitions_per_row": 1, "contact_budget": 0, "max_items_per_acquisition": 5,
    }


# ---------------------------------------------------------------------------
# 2. The runtime binding's ON path (synthetic snapshot, zero contacts).
# ---------------------------------------------------------------------------


def test_none_config_returns_none_on_path_selection():
    """The dispatch guard (``native_config is None``) is unaffected by E36b."""

    assert _build(None, _any_supply) is None


def test_no_supply_for_phase_is_still_an_always_empty_callable():
    """Item E36b does not touch this guard: with no supply bound at all the
    re-query is still a legal, zero-contact empty result."""

    requery = _build(_armed_on(), None)
    assert requery is not None
    assert tuple(requery(
        phase_id="solver", filters=(), exclude_value_ids=frozenset(),
        scope={}, context=object(),
    )) == ()


def test_scope_mismatch_is_refused_on_the_on_path_too():
    requery = _build(_armed_on(), _any_supply, snapshot=SimpleNamespace(values=()))
    with pytest.raises(FlightRuntimeError, match="knowledge-requery"):
        requery(
            phase_id="solver", filters=(), exclude_value_ids=frozenset(),
            scope={"kinds": ["speech-reobserve"]}, context=SimpleNamespace(),
        )


def test_idf_ranks_a_rarer_matched_token_above_a_universal_one():
    # "raretoken" occurs in exactly one of five values; "commontoken" occurs in all five, so its
    # IDF weight is log(5/5) == 0 -- it contributes nothing to a score. v1 is the only value whose
    # matched-token set includes the rare token, so it must outrank every other value.
    values = (
        _value("kb:v1", "raretoken commontoken"),
        _value("kb:v2", "commontoken"),
        _value("kb:v3", "commontoken"),
        _value("kb:v4", "commontoken"),
        _value("kb:v5", "commontoken"),
    )
    snapshot = SimpleNamespace(values=values)
    requery = _build(_armed_on(max_items=5), _any_supply, snapshot=snapshot)
    items = list(requery(
        phase_id="solver", filters=("raretoken", "commontoken"),
        exclude_value_ids=frozenset(), scope={}, context=SimpleNamespace(),
    ))
    assert [item.evidence_id for item in items][0] == "kb:v1"


def test_a_universal_token_alone_matches_everything_with_zero_weight():
    # With ONLY the universal token as a filter, every value matches (weight 0 each), so the tie
    # is broken purely by value id -- proving the weight really is zero, not merely small.
    values = tuple(_value(f"kb:v{i}", "commontoken") for i in range(4))
    snapshot = SimpleNamespace(values=values)
    requery = _build(_armed_on(max_items=4), _any_supply, snapshot=snapshot)
    items = list(requery(
        phase_id="solver", filters=("commontoken",), exclude_value_ids=frozenset(),
        scope={}, context=SimpleNamespace(),
    ))
    assert [item.evidence_id for item in items] == ["kb:v0", "kb:v1", "kb:v2", "kb:v3"]


def test_min_token_chars_drops_short_query_tokens():
    values = (
        _value("kb:v1", "ab-only-value has no long token"),
        _value("kb:v2", "alarm_set: set an alarm"),
    )
    snapshot = SimpleNamespace(values=values)
    requery = _build(
        _armed_on(retrieval=_retrieval(min_token_chars=4)), _any_supply, snapshot=snapshot,
    )
    # "ab" (2 chars) is dropped by min_token_chars; "alarm" (5 chars) survives and matches v2 only.
    items = list(requery(
        phase_id="solver", filters=("ab", "alarm"), exclude_value_ids=frozenset(),
        scope={}, context=SimpleNamespace(),
    ))
    assert [item.evidence_id for item in items] == ["kb:v2"]


def test_max_document_frequency_drops_too_common_tokens():
    # "common" occurs in 3 of 5 values (share 0.6); "rare" occurs in 1 of 5 (share 0.2). A cap of
    # 0.3 keeps "rare" and drops "common" -- so only the value matching "rare" is a candidate.
    values = (
        _value("kb:v1", "rare common"),
        _value("kb:v2", "common"),
        _value("kb:v3", "common"),
        _value("kb:v4", "neither"),
        _value("kb:v5", "neither"),
    )
    snapshot = SimpleNamespace(values=values)
    requery = _build(
        _armed_on(retrieval=_retrieval(max_document_frequency=0.3)),
        _any_supply, snapshot=snapshot,
    )
    items = list(requery(
        phase_id="solver", filters=("rare", "common"), exclude_value_ids=frozenset(),
        scope={}, context=SimpleNamespace(),
    ))
    assert [item.evidence_id for item in items] == ["kb:v1"]


def test_exclude_visible_tokens_drops_a_token_already_in_a_held_value():
    values = (
        _value("kb:held", "seenword"),
        _value("kb:candidate", "seenword other stuff entirely"),
    )
    snapshot = SimpleNamespace(values=values)
    excluded = frozenset({"kb:held"})

    on = _build(
        _armed_on(retrieval=_retrieval(exclude_visible_tokens=True)),
        _any_supply, snapshot=snapshot,
    )
    assert list(on(
        phase_id="solver", filters=("seenword",), exclude_value_ids=excluded,
        scope={}, context=SimpleNamespace(),
    )) == []

    off = _build(
        _armed_on(retrieval=_retrieval(exclude_visible_tokens=False)),
        _any_supply, snapshot=snapshot,
    )
    items = list(off(
        phase_id="solver", filters=("seenword",), exclude_value_ids=excluded,
        scope={}, context=SimpleNamespace(),
    ))
    assert [item.evidence_id for item in items] == ["kb:candidate"]


def test_exclude_value_ids_are_dropped_even_when_matched():
    values = (_value("kb:v1", "alarm_set: set an alarm"),)
    snapshot = SimpleNamespace(values=values)
    requery = _build(_armed_on(), _any_supply, snapshot=snapshot)
    items = list(requery(
        phase_id="solver", filters=("alarm",), exclude_value_ids=frozenset({"kb:v1"}),
        scope={}, context=SimpleNamespace(),
    ))
    assert items == []


def test_the_cap_is_honoured():
    values = tuple(_value(f"kb:v{i}", "alarm_set: set an alarm") for i in range(10))
    snapshot = SimpleNamespace(values=values)
    requery = _build(_armed_on(max_items=3), _any_supply, snapshot=snapshot)
    items = list(requery(
        phase_id="solver", filters=("alarm",), exclude_value_ids=frozenset(),
        scope={}, context=SimpleNamespace(),
    ))
    assert len(items) == 3


def test_empty_when_nothing_matches():
    values = (_value("kb:v1", "calendar_set: add an event"),)
    snapshot = SimpleNamespace(values=values)
    requery = _build(_armed_on(), _any_supply, snapshot=snapshot)
    items = list(requery(
        phase_id="solver", filters=("nonexistentword",), exclude_value_ids=frozenset(),
        scope={}, context=SimpleNamespace(),
    ))
    assert items == []


def test_determinism_same_inputs_same_output():
    values = tuple(_value(f"kb:v{i}", "alarm_set: set an alarm") for i in range(6))
    snapshot = SimpleNamespace(values=values)
    requery = _build(_armed_on(max_items=4), _any_supply, snapshot=snapshot)
    kwargs = dict(
        phase_id="solver", filters=("alarm",), exclude_value_ids=frozenset(),
        scope={}, context=SimpleNamespace(),
    )
    first = [(item.evidence_id, item.source_id, item.content) for item in requery(**kwargs)]
    second = [(item.evidence_id, item.source_id, item.content) for item in requery(**kwargs)]
    assert first == second


def test_ties_are_broken_by_value_id_ascending():
    # Every value carries the SAME single token, so every score is identical; the ranking must
    # then be exactly ascending value id.
    values = (
        _value("kb:zzz", "alarm"),
        _value("kb:aaa", "alarm"),
        _value("kb:mmm", "alarm"),
    )
    snapshot = SimpleNamespace(values=values)
    requery = _build(_armed_on(max_items=3), _any_supply, snapshot=snapshot)
    items = list(requery(
        phase_id="solver", filters=("alarm",), exclude_value_ids=frozenset(),
        scope={}, context=SimpleNamespace(),
    ))
    assert [item.evidence_id for item in items] == ["kb:aaa", "kb:mmm", "kb:zzz"]


# ---------------------------------------------------------------------------
# 3. Wire proof: the ON-path production binding returns a NON-EMPTY item set.
# ---------------------------------------------------------------------------


def _e36b_wire_proof_values() -> dict:
    values = _wire_proof_values()
    values["native_episode"]["acquisition"]["budget"]["max_items_per_acquisition"] = 2
    values["native_episode"]["acquisition"]["retrieval"] = _retrieval(min_token_chars=4)
    return values


def _force_perception_json_object(harness) -> None:
    base_material_for_phase = harness.material_for_phase

    def material_for_phase(phase, context, sealed):
        material = base_material_for_phase(phase, context, sealed)
        if phase == "perception":
            material = PhaseMaterial(
                instruction=material.instruction,
                response_format={"type": "json_object"},
                contact_id=material.contact_id,
                purpose=material.purpose,
            )
        return material

    harness.material_for_phase = material_for_phase


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_on_path_production_binding_returns_a_non_empty_item_set():
    """The E36 predecessor's own residual: with the LEGACY binding this exact wire shape always
    returns item_count 0 (the excluded set and the re-run selection are the same ids, so the
    intersection is empty by construction -- the B9a-rec finding this item repairs). With the
    ON-path production binding armed, the same wire proof must return a NON-EMPTY item set."""

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        harness = _ActualEpisodeHarness(
            tmp_path, sample_count=1, max_revisions=1, max_contacts=11,
            planner_actions=("ACQUIRE", "ACCEPT"),
            exhaustion_policy="deliver-latest-solver",
        )
        program = default_phase_program(PROGRAM_ID)
        config = load_native_episode_config(_e36b_wire_proof_values(), program)
        harness.config = config
        harness.program = program
        harness.repo_root = REPO_ROOT
        _force_perception_json_object(harness)

        # "acquire" (the Planner's own lowercased action name, derive_state_filters' guaranteed
        # token) plus a second value the row does NOT already hold and does not need supply_for_
        # phase to find -- exactly the shape a real released store carries.
        values = (
            _value("kb:v9", "acquire alarm_set: set an alarm"),
            _value("kb:v10", "acquire calendar_set: add an event"),
        )
        snapshot = SimpleNamespace(values=values)

        def supply_for_phase(phase_id, context):
            assert phase_id == "solver"
            return SimpleNamespace(fusion_decision=SimpleNamespace(selected_value_ids=()))

        harness.acquisition_requery = _build(config, supply_for_phase, snapshot=snapshot)

        try:
            summary = harness.run()
        finally:
            harness.close()

        [result] = summary.results
        receipt = result.native_episode_receipt
        acquisition_index = [v["stage"] for v in receipt["role_visits"]].index("acquisition")
        record = receipt["role_visits"][acquisition_index]["acquisition_receipt"]
        assert record["kind"] == "knowledge-requery"
        assert record["contacts_used"] == 0
        assert record["item_count"] > 0
        assert set(record["provenance_ids"]) <= {"kb:v9", "kb:v10"}
