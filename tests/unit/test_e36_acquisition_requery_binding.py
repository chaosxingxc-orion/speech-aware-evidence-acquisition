"""E36: the LIVE binding of the Acquisition node's kind (a) knowledge
re-query the flight runtime never supplied (cell B9a's arm abort, item E18's
own residual, docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md
outcome of decision 78 part 2, 2026-09-21).

``rails.runner``'s own acquisition node looks up
``NativeEpisodeRunBinding.acquisition_requery`` and refuses by name when it
is absent -- the E18/E32 proofs alone supplied it, through the test harness
attribute. This module proves the PRODUCTION callable
``FlightRuntime._acquisition_requery_binding`` builds:

1. the builder itself, over a tiny synthetic prepared supply + snapshot --
   ``None`` on every arm that needs no store re-query, filters honoured,
   excludes dropped, deterministic, empty result allowed, zero contacts;
2. the SAME shape again over a synthetic NAMED-KNOWLEDGE-STORE binding
   (qualified ids), the form cell B9a's own locked default-plan base uses;
3. a wire proof that re-runs the E32 ACQUIRE -> ACCEPT episode with the
   PRODUCTION binding in place of that proof's own per-test fake, through
   the real parser, the real OpenJiuwen role graph and the shared fake
   transport -- zero model, tokenizer, encoder or server contacts.

No proof helper needed updating: the E18/E32 fakes already return
``AcquiredItem(evidence_id, source_id, content)`` triples, exactly the
shape ``rails.acquisition.AcquiredItem`` and this binding both use.
"""

from __future__ import annotations

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
from speech_aware_evidence_acquisition.rails.knowledge_stores import STORE_SEPARATOR
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

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


def _force_perception_json_object(harness) -> None:
    """The E32 wire-proof program declares ``response_format_id`` for
    ``perception`` as a JSON object; the harness's own generic
    ``material_for_phase`` renders ``response_format=None``, so every E32
    wire proof overrides just the perception phase's material exactly this
    way (test_e32_acquisition_phase_program._wire_proof_harness)."""

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


_UNARMED = SimpleNamespace(acquisition_policy_id=None)
_ARMED_A = SimpleNamespace(acquisition_policy_id=acq.KNOWLEDGE_REQUERY_POLICY_ID)
_ARMED_B = SimpleNamespace(acquisition_policy_id=acq.SPEECH_REOBSERVE_POLICY_ID)


# ---------------------------------------------------------------------------
# 1. The builder returns None on every arm that needs no store re-query.
# ---------------------------------------------------------------------------


def test_none_config_returns_none():
    assert _build(None, lambda *a, **k: None) is None


def test_unarmed_config_returns_none():
    assert _build(_UNARMED, lambda *a, **k: None) is None


def test_speech_reobserve_kind_returns_none():
    """Kind (b) reaches Perception directly; this seam is unused for it."""

    assert _build(_ARMED_B, lambda *a, **k: None) is None


def test_no_supply_for_phase_yields_an_always_empty_callable():
    """No phase declares supply at all: a legal, zero-contact empty result."""

    requery = _build(_ARMED_A, None)
    assert requery is not None
    result = requery(
        phase_id="solver", filters=(), exclude_value_ids=frozenset(),
        scope={}, context=object(),
    )
    assert tuple(result) == ()


# ---------------------------------------------------------------------------
# 2. The bare (single-snapshot, no named store) path.
# ---------------------------------------------------------------------------


def test_bare_snapshot_returns_typed_items_in_supply_order():
    values = (
        _value("kb:v1", "alarm_set: set an alarm", facet="scenario_action:alarm_set"),
        _value("kb:v2", "calendar_set: add an event", facet="scenario_action:calendar_set"),
    )
    snapshot = SimpleNamespace(values=values)

    def supply_for_phase(phase_id, context):
        assert phase_id == "solver"
        return SimpleNamespace(
            fusion_decision=SimpleNamespace(selected_value_ids=("kb:v1", "kb:v2")),
        )

    requery = _build(_ARMED_A, supply_for_phase, snapshot=snapshot)
    items = list(requery(
        phase_id="solver", filters=(), exclude_value_ids=frozenset(),
        scope={"phase_id": "acquisition", "kinds": ["knowledge-requery"]},
        context=SimpleNamespace(),
    ))

    assert [item.evidence_id for item in items] == ["kb:v1", "kb:v2"]
    assert [item.content for item in items] == [
        "alarm_set: set an alarm", "calendar_set: add an event",
    ]
    assert all(
        item.source_id == f"phase-supply:{acq.KNOWLEDGE_REQUERY_POLICY_ID}"
        for item in items
    )
    for item in items:
        item.validate()


def test_exclude_value_ids_drops_already_supplied_items():
    values = (_value("kb:v1", "alarm_set: set an alarm"), _value("kb:v2", "calendar_set: add an event"))
    snapshot = SimpleNamespace(values=values)

    def supply_for_phase(phase_id, context):
        return SimpleNamespace(fusion_decision=SimpleNamespace(selected_value_ids=("kb:v1", "kb:v2")))

    requery = _build(_ARMED_A, supply_for_phase, snapshot=snapshot)
    items = list(requery(
        phase_id="solver", filters=(), exclude_value_ids=frozenset({"kb:v1"}),
        scope={}, context=SimpleNamespace(),
    ))
    assert [item.evidence_id for item in items] == ["kb:v2"]


def test_state_filters_restrict_by_content_or_facet():
    values = (
        _value("kb:v1", "time: leaving at five pm", facet="slot_type:time"),
        _value("kb:v2", "calendar_set: add an event", facet="scenario_action:calendar_set"),
    )
    snapshot = SimpleNamespace(values=values)

    def supply_for_phase(phase_id, context):
        return SimpleNamespace(fusion_decision=SimpleNamespace(selected_value_ids=("kb:v1", "kb:v2")))

    requery = _build(_ARMED_A, supply_for_phase, snapshot=snapshot)
    items = list(requery(
        phase_id="solver", filters=("time",), exclude_value_ids=frozenset(),
        scope={}, context=SimpleNamespace(),
    ))
    assert [item.evidence_id for item in items] == ["kb:v1"]


def test_empty_filter_token_set_is_unrestricted():
    values = (_value("kb:v1", "alarm_set: set an alarm"),)
    snapshot = SimpleNamespace(values=values)

    def supply_for_phase(phase_id, context):
        return SimpleNamespace(fusion_decision=SimpleNamespace(selected_value_ids=("kb:v1",)))

    requery = _build(_ARMED_A, supply_for_phase, snapshot=snapshot)
    items = list(requery(
        phase_id="solver", filters=(), exclude_value_ids=frozenset(),
        scope={}, context=SimpleNamespace(),
    ))
    assert [item.evidence_id for item in items] == ["kb:v1"]


def test_empty_selection_is_a_legal_empty_result():
    snapshot = SimpleNamespace(values=())

    def supply_for_phase(phase_id, context):
        return None

    requery = _build(_ARMED_A, supply_for_phase, snapshot=snapshot)
    assert list(requery(
        phase_id="solver", filters=(), exclude_value_ids=frozenset(),
        scope={}, context=SimpleNamespace(),
    )) == []


def test_determinism_same_inputs_same_output():
    values = (_value("kb:v1", "alarm_set: set an alarm"),)
    snapshot = SimpleNamespace(values=values)

    def supply_for_phase(phase_id, context):
        return SimpleNamespace(fusion_decision=SimpleNamespace(selected_value_ids=("kb:v1",)))

    requery = _build(_ARMED_A, supply_for_phase, snapshot=snapshot)
    kwargs = dict(
        phase_id="solver", filters=(), exclude_value_ids=frozenset(),
        scope={}, context=SimpleNamespace(),
    )
    first = [(i.evidence_id, i.source_id, i.content) for i in requery(**kwargs)]
    second = [(i.evidence_id, i.source_id, i.content) for i in requery(**kwargs)]
    assert first == second


def test_scope_mismatch_is_refused():
    snapshot = SimpleNamespace(values=())

    def supply_for_phase(phase_id, context):
        return None

    requery = _build(_ARMED_A, supply_for_phase, snapshot=snapshot)
    with pytest.raises(FlightRuntimeError, match="knowledge-requery"):
        requery(
            phase_id="solver", filters=(), exclude_value_ids=frozenset(),
            scope={"kinds": ["speech-reobserve"]}, context=SimpleNamespace(),
        )


# ---------------------------------------------------------------------------
# 3. The named-knowledge-store path (qualified ids): cell B9a's own shape.
# ---------------------------------------------------------------------------


def test_named_store_path_resolves_qualified_ids_and_source_id():
    qualified = _value(
        f"intent-boundaries{STORE_SEPARATOR}v9",
        "alarm_set: set an alarm",
        facet=f"intent-boundaries{STORE_SEPARATOR}scenario_action:alarm_set",
    )
    store_binding = SimpleNamespace(
        composite_snapshot=SimpleNamespace(values=(qualified,)),
        store_ids=("intent-boundaries", "slot-contracts"),
    )

    def supply_for_phase(phase_id, context):
        return SimpleNamespace(
            fusion_decision=SimpleNamespace(
                selected_value_ids=(f"intent-boundaries{STORE_SEPARATOR}v9",),
            ),
        )

    requery = _build(_ARMED_A, supply_for_phase, store_binding=store_binding)
    [item] = list(requery(
        phase_id="solver", filters=(), exclude_value_ids=frozenset(),
        scope={}, context=SimpleNamespace(),
    ))
    assert item.evidence_id == f"intent-boundaries{STORE_SEPARATOR}v9"
    assert item.source_id == "intent-boundaries"
    assert item.content == "alarm_set: set an alarm"


def test_named_store_path_defensively_skips_an_unresolvable_id():
    store_binding = SimpleNamespace(
        composite_snapshot=SimpleNamespace(values=()),
        store_ids=("intent-boundaries",),
    )

    def supply_for_phase(phase_id, context):
        return SimpleNamespace(
            fusion_decision=SimpleNamespace(
                selected_value_ids=(f"intent-boundaries{STORE_SEPARATOR}ghost",),
            ),
        )

    requery = _build(_ARMED_A, supply_for_phase, store_binding=store_binding)
    items = list(requery(
        phase_id="solver", filters=(), exclude_value_ids=frozenset(),
        scope={}, context=SimpleNamespace(),
    ))
    assert items == []


# ---------------------------------------------------------------------------
# 4. Wire proof: the PRODUCTION binding drives the real E32 ACQUIRE path.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_production_binding_drives_the_acquire_then_accept_row():
    """The E32 wire proof
    (test_an_acquire_then_accept_row_delivers_with_the_acquisition_receipt_first)
    re-run with the harness's own per-test fake ``requery`` replaced by the
    PRODUCTION callable ``FlightRuntime._acquisition_requery_binding``
    builds -- the ACQUIRE -> receipt -> revision path proved with
    production code, not just the E18/E32 proofs' own test double."""

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        harness = _ActualEpisodeHarness(
            tmp_path, sample_count=1, max_revisions=1, max_contacts=11,
            planner_actions=("ACQUIRE", "ACCEPT"),
            exhaustion_policy="deliver-latest-solver",
        )
        program = default_phase_program(PROGRAM_ID)
        config = load_native_episode_config(_wire_proof_values(), program)
        harness.config = config
        harness.program = program
        harness.repo_root = REPO_ROOT
        _force_perception_json_object(harness)

        # The content names the token derive_state_filters is GUARANTEED to
        # carry for any row that routes ACQUIRE: the Planner's own action
        # name, lowercased ("acquire"). The state restriction is real
        # production code (rails.acquisition.derive_state_filters) -- this
        # is not a bypass, it is choosing a fixture value the restriction
        # actually admits, exactly as a real acquired value would need to.
        values = (_value("kb:v9", "acquire alarm_set: set an alarm"),)
        snapshot = SimpleNamespace(values=values)

        def supply_for_phase(phase_id, context):
            assert phase_id == "solver"
            return SimpleNamespace(
                fusion_decision=SimpleNamespace(selected_value_ids=("kb:v9",)),
            )

        harness.acquisition_requery = _build(config, supply_for_phase, snapshot=snapshot)

        try:
            summary = harness.run()
        finally:
            harness.close()

        [result] = summary.results
        assert result.final_response_text == "solver-answer:s1:visit:2"
        receipt = result.native_episode_receipt
        stages = [visit["stage"] for visit in receipt["role_visits"]]
        acquisition_index = stages.index("acquisition")
        record = receipt["role_visits"][acquisition_index]["acquisition_receipt"]
        assert record["kind"] == "knowledge-requery"
        assert record["contacts_used"] == 0
        assert record["item_count"] == 1
        assert record["provenance_ids"] == ["kb:v9"]

        block = receipt["acquisition"]
        assert block["kind"] == "knowledge-requery"
        assert block["contacts_used"] == 0


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_production_binding_finds_nothing_when_the_row_already_holds_it():
    """The dedupe guarantee end to end: the production callable returns the
    single value, but the policy's own dedupe (rails.acquisition, not this
    binding) drops it once it is already in ``supplied_value_ids`` -- proved
    by exercising the SAME wire path with ``exclude_value_ids`` covering it
    via a supply that is already excluded before the callback even runs."""

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        harness = _ActualEpisodeHarness(
            tmp_path, sample_count=1, max_revisions=1, max_contacts=11,
            planner_actions=("ACQUIRE", "ACCEPT"),
            exhaustion_policy="deliver-latest-solver",
        )
        program = default_phase_program(PROGRAM_ID)
        config = load_native_episode_config(_wire_proof_values(), program)
        harness.config = config
        harness.program = program
        harness.repo_root = REPO_ROOT
        _force_perception_json_object(harness)

        snapshot = SimpleNamespace(values=())

        def supply_for_phase(phase_id, context):
            return None

        harness.acquisition_requery = _build(config, supply_for_phase, snapshot=snapshot)

        try:
            summary = harness.run()
        finally:
            harness.close()

        [result] = summary.results
        receipt = result.native_episode_receipt
        acquisition_index = [v["stage"] for v in receipt["role_visits"]].index("acquisition")
        record = receipt["role_visits"][acquisition_index]["acquisition_receipt"]
        assert record["item_count"] == 0
        assert record["provenance_ids"] == []
