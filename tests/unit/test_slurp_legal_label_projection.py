"""The SLURP legal-label projection (owner ruling 2026-09-06, preregistration
``docs/readiness/2026-09-06-slurp-legal-label-projection-relock-v1-preregistration.md``).

Two layers are covered here and kept apart on purpose:

* the PURE rule -- ``reproduction.slurp_scoring.project_slu_label`` and its
  inventory -- which takes its label space and its TRAIN prior as arguments
  and touches no corpus at all;
* the REGISTERED scorers ``slurp-slu-projected`` /
  ``slurp-slu-official-projected``, which must be the same function object,
  must not be the unprojected pair, and must leave the official parse and
  every entity-side metric exactly where they were.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pytest

from speech_aware_evidence_acquisition.core import scorers  # noqa: F401 (registration)
from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.data.slurp import SlurpRecord
from speech_aware_evidence_acquisition.reproduction import slurp_official_eval as soe
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
    OfficialSluResult,
    score_slurp_outputs_official,
    score_slurp_outputs_official_projected,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
    SLURP_LABEL_PROJECTION_ID,
    SlotEntity,
    legal_intent_inventory,
    project_slu_label,
)

# A miniature but structurally faithful inventory: three legal scenarios, a
# scenario with two actions whose edit distances to a probe tie, and a prior
# that separates them.
_PAIRING = {
    "alarm": ("set", "remove", "query"),
    "email": ("query", "sendemail"),
    "recommendation": ("events", "locations", "movies"),
}
_PRIOR = {
    "alarm_set": 300,
    "alarm_remove": 100,
    "alarm_query": 200,
    "email_query": 250,
    "email_sendemail": 400,
    "recommendation_events": 90,
    "recommendation_locations": 90,
    "recommendation_movies": 10,
}


def _inventory():
    return legal_intent_inventory(_PAIRING, _PRIOR)


# ---------------------------------------------------------------------------
# 1. The pure rule
# ---------------------------------------------------------------------------


def test_a_legal_pair_is_returned_untouched():
    outcome = project_slu_label("alarm", "set", _inventory())
    assert (outcome.scenario, outcome.action) == ("alarm", "set")
    assert outcome.changed is False
    assert outcome.eligible is True


def test_every_legal_pair_of_the_inventory_is_a_fixed_point():
    inventory = _inventory()
    for scenario, actions in _PAIRING.items():
        for action in actions:
            outcome = project_slu_label(scenario, action, inventory)
            assert (outcome.scenario, outcome.action) == (scenario, action)
            assert outcome.changed is False


def test_an_illegal_action_under_a_legal_scenario_keeps_the_scenario():
    """Rule 4a: the scenario is legal, so it is kept and only the action
    moves -- to the nearest action of THAT scenario."""

    outcome = project_slu_label("alarm", "sett", _inventory())
    assert (outcome.scenario, outcome.action) == ("alarm", "set")
    assert outcome.changed is True
    assert outcome.source_intent == "alarm_sett"
    assert outcome.projected_intent == "alarm_set"


def test_an_illegal_scenario_moves_to_the_nearest_legal_scenario_then_its_nearest_action():
    """Rule 4b: ``emails`` is one edit from ``email`` and far from the other
    two, so the scenario resolves first; the action then resolves inside the
    chosen scenario, not across the whole action vocabulary."""

    outcome = project_slu_label("emails", "querry", _inventory())
    assert (outcome.scenario, outcome.action) == ("email", "query")
    assert outcome.changed is True


def test_the_action_is_chosen_inside_the_chosen_scenario_only():
    """``recommendation`` is legal and does not carry ``set``; the nearest
    action among ITS OWN three is picked, never ``alarm``'s ``set``."""

    outcome = project_slu_label("recommendation", "set", _inventory())
    assert outcome.scenario == "recommendation"
    assert outcome.action in _PAIRING["recommendation"]


def test_the_train_prior_breaks_an_edit_distance_tie():
    """``recommendation``'s ``events`` and ``locations`` are each 6 and 9
    edits from the probe respectively, so the probe is built to tie: an equal
    distance to two candidates is resolved by the LARGER TRAIN prior."""

    inventory = legal_intent_inventory(
        {"s": ("aa", "bb")},
        {"s_aa": 1, "s_bb": 999},
    )
    outcome = project_slu_label("s", "cc", inventory)
    assert outcome.action == "bb"


def test_an_equal_prior_tie_falls_back_to_alphabetical_order():
    inventory = legal_intent_inventory({"s": ("aa", "bb")}, {"s_aa": 7, "s_bb": 7})
    outcome = project_slu_label("s", "cc", inventory)
    assert outcome.action == "aa"


def test_a_scenario_tie_is_broken_by_the_scenario_prior_then_alphabetically():
    equal = legal_intent_inventory(
        {"aa": ("x",), "bb": ("x",)}, {"aa_x": 5, "bb_x": 5}
    )
    assert project_slu_label("cc", "x", equal).scenario == "aa"
    weighted = legal_intent_inventory(
        {"aa": ("x",), "bb": ("x",)}, {"aa_x": 5, "bb_x": 6}
    )
    assert project_slu_label("cc", "x", weighted).scenario == "bb"


def test_an_unparsable_response_stays_unparsable():
    outcome = project_slu_label(None, None, _inventory(), parsed=False)
    assert (outcome.scenario, outcome.action) == (None, None)
    assert outcome.changed is False
    assert outcome.eligible is False


def test_a_parsed_but_label_free_response_is_ineligible_and_untouched():
    """The ``{"entities": [...]}`` shape a slot-only arm (KC-S1a / KC-S1b)
    answers with: there is no ``scenario_action`` to project."""

    outcome = project_slu_label(None, None, _inventory(), parsed=True)
    assert (outcome.scenario, outcome.action) == (None, None)
    assert outcome.eligible is False
    assert outcome.changed is False


def test_a_half_labelled_response_is_ineligible():
    for scenario, action in (("alarm", None), (None, "set")):
        outcome = project_slu_label(scenario, action, _inventory())
        assert (outcome.scenario, outcome.action) == (scenario, action)
        assert outcome.eligible is False
        assert outcome.changed is False


def test_an_empty_string_label_is_projected_not_treated_as_absent():
    outcome = project_slu_label("", "", _inventory())
    assert outcome.eligible is True
    assert outcome.changed is True
    assert (outcome.scenario, outcome.action) in _inventory().pairs


def test_the_projection_is_deterministic_and_idempotent():
    inventory = _inventory()
    first = project_slu_label("locations", "query", inventory)
    again = project_slu_label("locations", "query", inventory)
    assert (first.scenario, first.action) == (again.scenario, again.action)
    settled = project_slu_label(first.scenario, first.action, inventory)
    assert settled.changed is False


def test_the_inventory_exposes_the_pairs_and_the_priors_it_was_built_from():
    inventory = _inventory()
    assert len(inventory.pairs) == 8
    assert inventory.scenarios == ("alarm", "email", "recommendation")
    assert inventory.prior("email", "sendemail") == 400
    assert inventory.prior("email", "nosuchaction") == 0
    assert inventory.scenario_prior("alarm") == 600


def test_the_inventory_fails_closed_on_a_malformed_pairing():
    with pytest.raises(ValueError):
        legal_intent_inventory({})
    with pytest.raises(ValueError):
        legal_intent_inventory({"s": ()})
    with pytest.raises(ValueError):
        legal_intent_inventory({"s": "notalist"})
    with pytest.raises(ValueError):
        legal_intent_inventory({"s": ("a",)}, {"s_a": -1})


# ---------------------------------------------------------------------------
# 2. The registered scorers
# ---------------------------------------------------------------------------


def test_both_projected_scorer_ids_are_registered():
    names = SCORERS.names()
    assert "slurp-slu-projected" in names
    assert "slurp-slu-official-projected" in names


def test_both_projected_ids_resolve_the_same_function_and_it_is_not_the_unprojected_one():
    short = SCORERS.resolve("slurp-slu-projected")
    explicit = SCORERS.resolve("slurp-slu-official-projected")
    assert short is explicit
    assert short is score_slurp_outputs_official_projected
    assert short is not SCORERS.resolve("slurp-slu")
    assert short is not score_slurp_outputs_official


# ---------------------------------------------------------------------------
# 3. End to end through the registered scorer, against a fake official
#    evaluator (this suite never spawns the pinned evaluator venv).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _FakeIntentProfile:
    n: int


@dataclass(frozen=True)
class _FakeOntology:
    actions_by_scenario: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True)
class _FakeSchema:
    intents: Mapping[str, _FakeIntentProfile]


def _gold(sample_id: str, scenario: str, action: str, entities) -> SlurpRecord:
    return SlurpRecord(
        sample_id=sample_id,
        utterance_id=sample_id.split(":")[2],
        split="devel",
        media_relpath=f"slurp_real/{sample_id}.flac",
        audio_seconds=1.5,
        scenario=scenario,
        action=action,
        intent=f"{scenario}_{action}",
        entities=entities,
    )


def _official_result() -> OfficialSluResult:
    raw = {
        key: {
            "official_label": key,
            "precision": 0.0,
            "recall": 0.0,
            "f_measure": 0.0,
            "tp": 0.0,
            "fp": 0.0,
            "fn": 0.0,
        }
        for key in (
            "scenario",
            "action",
            "intent",
            "entities",
            "entities_distance_word",
            "entities_distance_char",
            "slu_f1",
        )
    }
    return OfficialSluResult(
        scenario_accuracy=0.0,
        action_accuracy=0.0,
        intent_accuracy=0.0,
        slu_f1=1.0,
        span_f1=1.0,
        raw=raw,
        stdout="fake",
        command=("python", "evaluate.py"),
    )


@pytest.fixture()
def wired(monkeypatch, tmp_path):
    """One gold row (``alarm_set``) and the fake evaluator, with the TRAIN
    inventory replaced by :data:`_PAIRING` / :data:`_PRIOR`."""

    record = _gold(
        "slurp:devel:000001:rec-a", "alarm", "set", (SlotEntity("time", "seven am"),)
    )
    monkeypatch.setattr(
        soe,
        "load_slurp_split",
        lambda lock, root, split_id, *, allow_heldout=False, allow_synthetic=False: [record],
    )
    monkeypatch.setattr(
        soe, "load_slurp_ontology", lambda lock, root: _FakeOntology(_PAIRING)
    )
    monkeypatch.setattr(
        soe,
        "load_slurp_intent_slot_schema",
        lambda lock, root: _FakeSchema(
            {intent: _FakeIntentProfile(n) for intent, n in _PRIOR.items()}
        ),
    )
    monkeypatch.setattr(soe, "official_evaluator_root", lambda root: Path("unused"))
    captured: dict[str, object] = {}

    def _fake_run(gold_path, pred_path, *, evaluator_root, python_executable=None, average="micro"):
        captured["predictions"] = [
            json.loads(line)
            for line in Path(pred_path).read_text(encoding="utf-8").split("\n")
            if line.strip()
        ]
        return _official_result()

    monkeypatch.setattr(soe, "run_official_evaluate", _fake_run)
    return record, captured, tmp_path


def _write(tmp_path: Path, text: str) -> Path:
    outputs = tmp_path / "x.outputs.jsonl"
    outputs.write_text(
        json.dumps({"sample_id": "slurp:devel:000001:rec-a", "text": text}) + "\n",
        encoding="utf-8",
    )
    return outputs


def test_the_projected_scorer_rewrites_an_illegal_pair_before_the_official_file(wired):
    _record, captured, tmp_path = wired
    outputs = _write(
        tmp_path,
        json.dumps(
            {
                "scenario": "alarms",
                "action": "sett",
                "entities": [{"type": "time", "filler": "seven am"}],
            }
        ),
    )

    result = SCORERS.resolve("slurp-slu-official-projected")(outputs, {}, tmp_path)

    prediction = captured["predictions"][0]
    assert (prediction["scenario"], prediction["action"]) == ("alarm", "set")
    # Entities reach the official file untouched.
    assert prediction["entities"] == [{"type": "time", "filler": "seven am"}]

    row = result["per_sample"][0]
    assert row["projected"] is True
    assert row["projected_from"] == "alarms_sett"
    assert row["projected_to"] == "alarm_set"
    assert row["scenario_action_exact"] == 1.0

    projection = result["aggregate"]["projection"]
    assert projection["applied"] is True
    assert projection["projection_id"] == SLURP_LABEL_PROJECTION_ID
    assert projection["counts"] == {
        "eligible": 1,
        "changed": 1,
        "unchanged": 0,
        "ineligible": 0,
    }
    assert projection["map"] == {"alarms_sett -> alarm_set": 1}
    assert projection["legal_intents"] == 8


def test_the_projected_scorer_leaves_a_legal_pair_exactly_where_it_was(wired):
    _record, captured, tmp_path = wired
    outputs = _write(
        tmp_path,
        json.dumps(
            {
                "scenario": "alarm",
                "action": "query",
                "entities": [{"type": "time", "filler": "seven am"}],
            }
        ),
    )

    result = SCORERS.resolve("slurp-slu-projected")(outputs, {}, tmp_path)

    prediction = captured["predictions"][0]
    assert (prediction["scenario"], prediction["action"]) == ("alarm", "query")
    assert result["per_sample"][0]["projected"] is False
    assert result["aggregate"]["projection"]["counts"] == {
        "eligible": 1,
        "changed": 0,
        "unchanged": 1,
        "ineligible": 0,
    }


def test_an_unparsable_response_stays_unparsable_through_the_scorer(wired):
    _record, captured, tmp_path = wired
    outputs = _write(tmp_path, "I am not JSON at all.")

    result = SCORERS.resolve("slurp-slu-official-projected")(outputs, {}, tmp_path)

    prediction = captured["predictions"][0]
    assert prediction["scenario"] is None
    assert prediction["action"] is None
    assert prediction["entities"] == []
    row = result["per_sample"][0]
    assert row["parsed"] is False
    assert row["projected"] is False
    assert result["aggregate"]["projection"]["counts"]["ineligible"] == 1


def test_an_entity_only_response_is_untouched_by_the_projection(wired):
    """KC-S1a / KC-S1b answer ``{"entities": [...]}``; the projection must
    change nothing, so their entity-side numbers are provably identical
    projected and unprojected."""

    _record, captured, tmp_path = wired
    payload = json.dumps({"entities": [{"type": "time", "filler": "seven am"}]})
    outputs = _write(tmp_path, payload)

    projected = SCORERS.resolve("slurp-slu-official-projected")(outputs, {}, tmp_path)
    prediction = captured["predictions"][0]
    assert prediction["scenario"] is None and prediction["action"] is None
    assert prediction["entities"] == [{"type": "time", "filler": "seven am"}]

    unprojected = SCORERS.resolve("slurp-slu-official")(outputs, {}, tmp_path)
    for field in (
        "slot_f1_exact_f1",
        "slu_f1_f1",
        "slu_f1_word_f1",
        "slu_f1_char_f1",
        "scenario_action_exact",
    ):
        assert projected["per_sample"][0][field] == unprojected["per_sample"][0][field]
    assert projected["aggregate"]["projection"]["counts"]["ineligible"] == 1


def test_the_unprojected_scorer_reports_no_projection_and_loads_no_inventory(
    wired, monkeypatch
):
    _record, _captured, tmp_path = wired

    def _explode(lock, root):  # pragma: no cover - must never be reached
        raise AssertionError("the unprojected path must not read the TRAIN inventory")

    monkeypatch.setattr(soe, "load_slurp_ontology", _explode)
    monkeypatch.setattr(soe, "load_slurp_intent_slot_schema", _explode)
    outputs = _write(
        tmp_path,
        json.dumps({"scenario": "alarms", "action": "sett", "entities": []}),
    )

    result = SCORERS.resolve("slurp-slu-official")(outputs, {}, tmp_path)

    assert result["aggregate"]["projection"] == {"applied": False, "projection_id": None}
    assert "projected" not in result["per_sample"][0]
    assert result["per_sample"][0]["scenario_action_exact"] == 0.0
