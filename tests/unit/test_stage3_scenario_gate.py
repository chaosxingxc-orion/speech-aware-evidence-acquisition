"""Stage-3 iteration 3: the row-level SCENARIO GATE on a stage3-deltas route.

Why the mechanism exists (``docs/results/2026-09-24-slurp-general-scenario-
diagnostic.md``): on the strata the delta store has no reach into, the
DERANGEMENT TWIN loses as much as the arm does, so the loss there is a FORM
cost of carrying a supply and not the content of any delta. The answer is not
a better delta; it is not applying the store where it should not apply.

What is proved here:

* the majority rule, including its first-listed tie-break, as a pure function;
* a CLOSED gate takes no supply step at all and receipts the majority scenario
  LABEL on the route's own skip audit;
* an OPEN gate is byte-identical to the ungated route -- same selection, same
  rank result, same fusion decision;
* the spec is fail-closed: an unknown policy id, an empty or repeated or
  non-catalog ``scenarios`` list (including an intent id written where a
  scenario belongs) is refused at config load, before a contact is spent;
* the Perception route -- the node that PRODUCES the candidates -- refuses a
  gate outright.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.core.base import STAGE3_SUPPLY_GATE_POLICIES
from speech_aware_evidence_acquisition.analysis.native_episode_dry_run import (
    _scenario_gate_decisions,
)
from speech_aware_evidence_acquisition.rails.knowledge_provider import (
    resolve_scenario_gate,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    KnowledgeStoreError,
    build_knowledge_store_supply,
    load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.stage3_delta_supply import (
    STAGE3_DELTA_SCENARIO_GATE_POLICY_ID,
    STAGE3_DELTA_SCENARIO_GATE_SKIP_REASON,
    ScenarioGate,
    Stage3DeltaSupplyError,
    catalog_scenarios,
    majority_candidate_scenario,
    parse_scenario_gate,
    scenario_of_intent,
)

from test_stage3_delta_node_routes import (
    _candidate_spec,
    _config,
    _context,
    _delta_row,
    _perception_state,
    _program,
    _selected,
    _unconditional_spec,
)

#: SLURP-SHAPED, unlike the four-letter inventory the sibling route tests use:
#: this whole mechanism is about the ``<scenario>_<action>`` composition, so an
#: inventory without it would prove nothing.
INVENTORY = (
    "general_quirky",
    "general_joke",
    "qa_factoid",
    "qa_definition",
    "iot_hue_lighton",
    "audio_volume_up",
    "news_query",
)
#: The seven strata of the real fragment, narrowed to the two this inventory
#: can express.
GATED = ["general", "iot"]

ROWS = (
    _delta_row("aaaaaaaaaaaa", "qa_factoid", 0.90, "solver"),
    _delta_row("bbbbbbbbbbbb", "general_quirky", 0.80, "solver"),
    _delta_row("cccccccccccc", "iot_hue_lighton", 0.70, "solver"),
    _delta_row("dddddddddddd", "qa_factoid", 0.60, "reviewer", kind="reviewer-criterion"),
    _delta_row("eeeeeeeeeeee", "general_quirky", 0.55, "perception", kind="perception-hint"),
)


def _gate(scenarios=GATED, policy=STAGE3_DELTA_SCENARIO_GATE_POLICY_ID):
    return {"policy": policy, "scenarios": list(scenarios)}


def _gated_spec(phase, cap, **gate):
    spec = _candidate_spec(phase, cap)
    spec["scenario_gate"] = _gate(**gate)
    return spec


def _bound(tmp_path, context_supply, *, rows=ROWS, inventory=INVENTORY):
    document = _config(tmp_path, context_supply=context_supply, rows=rows)
    binding = load_knowledge_store_binding(document, data_root=tmp_path)
    return binding, build_knowledge_store_supply(
        binding,
        program=_program(),
        data_root=tmp_path,
        legal_candidate_ids=inventory,
    )


# ---------------------------------------------------------------------------
# The pure rule
# ---------------------------------------------------------------------------


def test_the_scenario_is_the_part_before_the_first_underscore() -> None:
    assert scenario_of_intent("general_quirky") == "general"
    assert scenario_of_intent("qa_factoid") == "qa"
    # Two underscores: the FIRST one splits, so an action may carry its own.
    assert scenario_of_intent("iot_hue_lighton") == "iot"
    # No underscore at all reads as itself rather than raising: the catalog,
    # not this function, decides which names exist.
    assert scenario_of_intent("general") == "general"


@pytest.mark.parametrize("bad", ["", None, 3, ("qa_factoid",)])
def test_a_malformed_intent_id_is_refused_rather_than_coerced(bad) -> None:
    with pytest.raises(Stage3DeltaSupplyError):
        scenario_of_intent(bad)


def test_the_majority_is_most_frequent_not_more_than_half() -> None:
    assert majority_candidate_scenario(
        ("qa_factoid", "qa_definition", "general_quirky")
    ) == "qa"
    # Two of five, and still the majority.
    assert majority_candidate_scenario(
        ("qa_factoid", "qa_definition", "general_quirky", "iot_hue_lighton",
         "audio_volume_up")
    ) == "qa"


def test_a_tie_is_broken_by_the_first_listed_candidate() -> None:
    assert majority_candidate_scenario(("general_quirky", "qa_factoid")) == "general"
    assert majority_candidate_scenario(("qa_factoid", "general_quirky")) == "qa"


def test_a_tie_the_first_candidate_is_not_in_is_still_deterministic() -> None:
    # a:1, b:2, c:2 -- the first-listed candidate's scenario cannot win a tie
    # it is not in, so the earliest-occurring tied maximum wins instead.
    assert majority_candidate_scenario(
        ("audio_volume_up", "qa_factoid", "qa_definition", "general_quirky",
         "general_joke")
    ) == "qa"


def test_an_empty_candidate_list_has_no_majority() -> None:
    assert majority_candidate_scenario(()) is None
    gate = ScenarioGate(
        policy_id=STAGE3_DELTA_SCENARIO_GATE_POLICY_ID, scenarios=("general",)
    ).validate()
    decision = gate.decide(())
    assert (decision.closed, decision.majority_scenario, decision.candidate_count) == (
        False, None, 0,
    )


def test_the_catalog_is_derived_from_the_authoritative_inventory() -> None:
    assert catalog_scenarios(INVENTORY) == ("audio", "general", "iot", "news", "qa")
    with pytest.raises(Stage3DeltaSupplyError):
        catalog_scenarios(())


# ---------------------------------------------------------------------------
# The spec, fail-closed
# ---------------------------------------------------------------------------


def test_the_gate_policy_resolves_in_the_core_registry() -> None:
    assert STAGE3_DELTA_SCENARIO_GATE_POLICY_ID in STAGE3_SUPPLY_GATE_POLICIES.names()
    gate = resolve_scenario_gate(_gate(), legal_intent_ids=INVENTORY)
    assert isinstance(gate, ScenarioGate)
    assert gate.scenarios == ("general", "iot")


def test_an_unknown_gate_policy_is_refused() -> None:
    with pytest.raises(Stage3DeltaSupplyError):
        parse_scenario_gate(
            _gate(policy="majority-candidate-scenario-in-v1"), legal_intent_ids=INVENTORY
        )


@pytest.mark.parametrize(
    "raw",
    [
        # an intent id written where a scenario belongs -- the category error
        {"policy": STAGE3_DELTA_SCENARIO_GATE_POLICY_ID, "scenarios": ["qa_factoid"]},
        # a scenario this carrier does not have
        {"policy": STAGE3_DELTA_SCENARIO_GATE_POLICY_ID, "scenarios": ["generl"]},
        {"policy": STAGE3_DELTA_SCENARIO_GATE_POLICY_ID, "scenarios": ["calendar"]},
        # empty, repeated, blank, non-string, a bare string, a mapping
        {"policy": STAGE3_DELTA_SCENARIO_GATE_POLICY_ID, "scenarios": []},
        {"policy": STAGE3_DELTA_SCENARIO_GATE_POLICY_ID,
         "scenarios": ["general", "general"]},
        {"policy": STAGE3_DELTA_SCENARIO_GATE_POLICY_ID, "scenarios": ["general", ""]},
        {"policy": STAGE3_DELTA_SCENARIO_GATE_POLICY_ID, "scenarios": ["general", 3]},
        {"policy": STAGE3_DELTA_SCENARIO_GATE_POLICY_ID, "scenarios": "general"},
        {"policy": STAGE3_DELTA_SCENARIO_GATE_POLICY_ID, "scenarios": {"general": 1}},
        # missing and extra keys
        {"policy": STAGE3_DELTA_SCENARIO_GATE_POLICY_ID},
        {"scenarios": ["general"]},
        {"policy": STAGE3_DELTA_SCENARIO_GATE_POLICY_ID, "scenarios": ["general"],
         "mode": "strict"},
        None,
        "general",
    ],
)
def test_a_malformed_scenario_gate_spec_is_refused(raw) -> None:
    with pytest.raises(Stage3DeltaSupplyError):
        parse_scenario_gate(raw, legal_intent_ids=INVENTORY)


def test_a_malformed_gate_is_refused_at_config_load_not_on_row_75(tmp_path) -> None:
    with pytest.raises(KnowledgeStoreError):
        _bound(
            tmp_path,
            {"solver": _gated_spec("solver", 8, scenarios=["qa_factoid"])},
        )


def test_the_perception_route_refuses_a_scenario_gate(tmp_path) -> None:
    spec = dict(_unconditional_spec())
    spec["scenario_gate"] = _gate()
    with pytest.raises(KnowledgeStoreError):
        _bound(tmp_path, {"perception": spec})


def test_an_explicit_null_gate_is_refused(tmp_path) -> None:
    spec = _candidate_spec("solver", 8)
    spec["scenario_gate"] = None
    with pytest.raises(KnowledgeStoreError):
        _bound(tmp_path, {"solver": spec})


# ---------------------------------------------------------------------------
# The route
# ---------------------------------------------------------------------------


def test_a_closed_gate_takes_no_supply_step_and_receipts_the_label(tmp_path) -> None:
    binding, router = _bound(tmp_path, {"solver": _gated_spec("solver", 8)})
    # general, general, qa -> majority "general", which the gate names.
    context = _context(
        binding,
        _perception_state("s1", ("general_quirky", "general_joke", "qa_factoid")),
    )
    assert router.automatic_for_phase("solver", context) is None

    skip = next(iter(router.receipt["delta_supply"].values()))
    assert skip["node"] == "solver"
    assert skip["selected"] == 0
    assert skip["already_acquired"] == 0
    assert skip["reason"] == STAGE3_DELTA_SCENARIO_GATE_SKIP_REASON
    assert skip["majority_scenario"] == "general"

    decision = next(iter(router.receipt["delta_scenario_gate"].values()))
    assert decision["closed"] is True
    assert decision["majority_scenario"] == "general"
    assert decision["candidate_count"] == 3
    assert decision["policy_id"] == STAGE3_DELTA_SCENARIO_GATE_POLICY_ID
    assert decision["gated_scenarios"] == GATED
    # Labels only: no candidate text, no statement, no utterance anywhere.
    assert set(decision) == {
        "node", "phase", "sample_id", "store_id", "policy_id", "gated_scenarios",
        "majority_scenario", "candidate_count", "closed",
    }


def test_an_open_gate_is_byte_identical_to_the_ungated_route(tmp_path) -> None:
    # qa, qa, general -> majority "qa", which the gate does NOT name.
    intents = ("qa_factoid", "qa_definition", "general_quirky")

    ungated_binding, ungated = _bound(
        tmp_path / "ungated", {"solver": _candidate_spec("solver", 8)}
    )
    gated_binding, gated = _bound(
        tmp_path / "gated", {"solver": _gated_spec("solver", 8)}
    )
    ungated_supply = ungated.automatic_for_phase(
        "solver", _context(ungated_binding, _perception_state("s1", intents))
    )
    gated_supply = gated.automatic_for_phase(
        "solver", _context(gated_binding, _perception_state("s1", intents))
    )
    assert ungated_supply is not None
    assert _selected(gated_supply) == _selected(ungated_supply)
    assert (
        gated_supply.rank_result.content_hash()
        == ungated_supply.rank_result.content_hash()
    )
    assert (
        gated_supply.fusion_decision.content_hash()
        == ungated_supply.fusion_decision.content_hash()
    )
    assert gated_supply.action_target_ref == ungated_supply.action_target_ref
    # An OPEN gate is not a skip.
    assert gated.receipt["delta_supply"] == {}


def test_the_gate_receipt_records_open_and_closed_alike(tmp_path) -> None:
    binding, router = _bound(
        tmp_path,
        {"solver": _gated_spec("solver", 8), "reviewer": _gated_spec("reviewer", 4)},
    )
    closed = _context(
        binding, _perception_state("s1", ("iot_hue_lighton", "general_quirky"))
    )
    open_row = _context(
        binding, _perception_state("s2", ("qa_factoid", "qa_definition")), sample_id="s2"
    )
    assert router.automatic_for_phase("solver", closed) is None
    assert router.automatic_for_phase("solver", open_row) is not None

    decisions = {
        (entry["sample_id"], entry["node"]): entry
        for entry in router.receipt["delta_scenario_gate"].values()
    }
    assert decisions[("s1", "solver")]["closed"] is True
    assert decisions[("s1", "solver")]["majority_scenario"] == "iot"
    assert decisions[("s2", "solver")]["closed"] is False
    assert decisions[("s2", "solver")]["majority_scenario"] == "qa"


def test_an_ungated_router_publishes_no_gate_receipt(tmp_path) -> None:
    _binding, router = _bound(tmp_path, {"solver": _candidate_spec("solver", 8)})
    assert "delta_supply" in router.receipt
    assert "delta_scenario_gate" not in router.receipt


def test_the_dry_run_reads_the_gate_decisions_off_the_router_receipt() -> None:
    class _Router:
        receipt = {
            "delta_scenario_gate": {
                "solver:s1:hash": {
                    "node": "solver", "phase": "solver", "sample_id": "s1",
                    "store_id": "stage3-deltas",
                    "policy_id": STAGE3_DELTA_SCENARIO_GATE_POLICY_ID,
                    "gated_scenarios": GATED, "majority_scenario": "iot",
                    "candidate_count": 3, "closed": True,
                },
                "reviewer:s1:hash": {
                    "node": "reviewer", "phase": "reviewer", "sample_id": "s1",
                    "store_id": "stage3-deltas",
                    "policy_id": STAGE3_DELTA_SCENARIO_GATE_POLICY_ID,
                    "gated_scenarios": GATED, "majority_scenario": "iot",
                    "candidate_count": 3, "closed": False,
                },
                "solver:s2:hash": {
                    "node": "solver", "phase": "solver", "sample_id": "s2",
                    "store_id": "stage3-deltas",
                    "policy_id": STAGE3_DELTA_SCENARIO_GATE_POLICY_ID,
                    "gated_scenarios": GATED, "majority_scenario": "qa",
                    "candidate_count": 2, "closed": False,
                },
            }
        }

    decisions = _scenario_gate_decisions({"supply_for_store": _Router()}, "s1")
    assert [item.node for item in decisions] == ["reviewer", "solver"]
    assert {item.node: item.closed for item in decisions} == {
        "reviewer": False, "solver": True,
    }
    # A cell whose routes declare no gate reports nothing rather than failing.
    assert _scenario_gate_decisions({}, "s1") == ()
