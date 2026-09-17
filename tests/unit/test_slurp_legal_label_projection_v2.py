"""The SUCCESSOR SLURP legal-label projection, ``slurp-legal-label-projection-v2``
(preregistration
``docs/readiness/2026-09-06-slurp-legal-label-projection-v2-preregistration.md``).

The rule promotes an illegal SCENARIO slot that happens to hold a legal ACTION
name back to the scenario that owns it, and otherwise falls through to v1
unchanged. Three layers are covered and kept apart on purpose:

* the PURE rule -- ``reproduction.slurp_scoring.project_slu_label_v2`` -- over
  the same corpus-free miniature inventory v1's suite uses;
* the RELATIONSHIP to v1: every row v1 leaves alone, v2 leaves alone, and every
  row v2 does not promote is v1's own answer, byte for byte;
* the REGISTERED scorers ``slurp-slu-projected-v2`` /
  ``slurp-slu-official-projected-v2``, which must be one function object,
  must not be v1's or the unprojected pair, and must leave the parse and every
  entity-side metric exactly where they were.
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
    SlurpOfficialEvalError,
    score_slurp_outputs_official,
    score_slurp_outputs_official_projected,
    score_slurp_outputs_official_projected_v2,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
    SLURP_LABEL_PROJECTION_ID,
    SLURP_LABEL_PROJECTION_V2_ID,
    SlotEntity,
    legal_intent_inventory,
    project_slu_label,
    project_slu_label_v2,
)

# The same miniature inventory v1's suite uses, so the two suites describe one
# label space. ``recommendation`` owns the three action names the real corpus's
# residual class is spelled with (``events``, ``locations``, ``movies``), and
# ``query`` is owned by TWO scenarios so the multi-owner tie is reachable.
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
# 1. The promotion branch, on the three shapes the real residual class takes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("scenario", "action", "expected"),
    [
        ("locations", "query", ("recommendation", "locations")),
        ("events", "query", ("recommendation", "events")),
        ("movies", "query", ("recommendation", "movies")),
    ],
)
def test_an_action_named_scenario_is_promoted_to_its_owning_scenario(
    scenario, action, expected
):
    """The class v1's verdict named and priced: the model wrote the ACTION of
    ``recommendation_locations`` in the scenario slot and a generic ``query``
    beside it. v2 sends the name back to the scenario that owns it."""

    outcome = project_slu_label_v2(scenario, action, _inventory())
    assert (outcome.scenario, outcome.action) == expected
    assert outcome.changed is True
    assert outcome.eligible is True
    assert outcome.branch == "promote"
    assert outcome.source_intent == f"{scenario}_{action}"
    assert outcome.projected_intent == f"{expected[0]}_{expected[1]}"


def test_the_promotion_discards_the_action_half_whatever_it_says():
    """``a0`` is not an input to the promotion: the action name in the scenario
    slot is the signal, and the generic action beside it is noise."""

    for action in ("query", "set", "nonsense", ""):
        outcome = project_slu_label_v2("locations", action, _inventory())
        assert (outcome.scenario, outcome.action) == ("recommendation", "locations")
        assert outcome.branch == "promote"


def test_v2_beats_v1_on_exactly_this_class():
    """v1 is blind to it by construction -- it measures spelling, so
    ``locations`` goes wherever ``locations`` looks like it belongs."""

    inventory = _inventory()
    v1 = project_slu_label("locations", "query", inventory)
    v2 = project_slu_label_v2("locations", "query", inventory)
    assert (v2.scenario, v2.action) == ("recommendation", "locations")
    assert (v1.scenario, v1.action) != (v2.scenario, v2.action)
    assert v1.branch == "edit-distance"


# ---------------------------------------------------------------------------
# 2. Owner selection
# ---------------------------------------------------------------------------


def test_a_single_owner_action_resolves_without_a_tie_break():
    inventory = _inventory()
    assert inventory.owners_of("locations") == ("recommendation",)
    assert project_slu_label_v2("locations", "x", inventory).scenario == "recommendation"


def test_a_multi_owner_action_picks_the_larger_train_prior():
    """``query`` is owned by ``alarm`` (200) and ``email`` (250), so the larger
    OWNING-PAIR prior takes it -- and it is the pair's prior that decides, not
    alphabetical order, which would have said ``alarm``."""

    inventory = _inventory()
    assert inventory.owners_of("query") == ("alarm", "email")
    assert inventory.prior("email", "query") > inventory.prior("alarm", "query")
    outcome = project_slu_label_v2("query", "nonsense", inventory)
    assert (outcome.scenario, outcome.action) == ("email", "query")
    assert outcome.branch == "promote"


def test_an_equal_owner_prior_falls_back_to_alphabetical_order():
    inventory = legal_intent_inventory(
        {"bb": ("x", "y"), "aa": ("x", "y")}, {"aa_x": 7, "bb_x": 7, "aa_y": 1, "bb_y": 1}
    )
    outcome = project_slu_label_v2("x", "zzz", inventory)
    assert (outcome.scenario, outcome.action) == ("aa", "x")


def test_the_owner_key_is_the_pair_prior_not_the_scenario_prior():
    """``bb`` carries far more TRAIN mass overall, but ``aa`` owns the pair
    ``(aa, x)`` more heavily, and the pair is what the rule reads."""

    inventory = legal_intent_inventory(
        {"aa": ("x",), "bb": ("x", "y")}, {"aa_x": 50, "bb_x": 10, "bb_y": 9000}
    )
    assert inventory.scenario_prior("bb") > inventory.scenario_prior("aa")
    assert project_slu_label_v2("x", "zzz", inventory).scenario == "aa"


# ---------------------------------------------------------------------------
# 3. The v1 fallback, and everything v2 must NOT touch
# ---------------------------------------------------------------------------


def test_an_illegal_scenario_that_is_no_action_name_falls_back_to_v1():
    inventory = _inventory()
    outcome = project_slu_label_v2("emails", "querry", inventory)
    v1 = project_slu_label("emails", "querry", inventory)
    assert (outcome.scenario, outcome.action) == (v1.scenario, v1.action) == ("email", "query")
    assert outcome.branch == "edit-distance"


def test_a_legal_scenario_is_never_promoted_even_when_it_is_also_an_action_name():
    """``query`` is a legal ACTION name; if it were also a legal SCENARIO the
    promotion must not fire, because a legal scenario slot may well be right.
    v1's rule 4a keeps it and moves only the action."""

    inventory = legal_intent_inventory(
        {"query": ("run", "stop"), "email": ("query", "sendemail")},
        {"query_run": 5, "query_stop": 4, "email_query": 300, "email_sendemail": 20},
    )
    outcome = project_slu_label_v2("query", "nonsense", inventory)
    assert outcome.scenario == "query"
    assert outcome.action in ("run", "stop")
    assert outcome.branch == "edit-distance"


def test_a_legal_pair_is_returned_untouched():
    for scenario, actions in _PAIRING.items():
        for action in actions:
            outcome = project_slu_label_v2(scenario, action, _inventory())
            assert (outcome.scenario, outcome.action) == (scenario, action)
            assert outcome.changed is False
            assert outcome.branch == "already-legal"


def test_an_unparsable_response_stays_unparsable():
    outcome = project_slu_label_v2(None, None, _inventory(), parsed=False)
    assert (outcome.scenario, outcome.action) == (None, None)
    assert outcome.changed is False
    assert outcome.eligible is False
    assert outcome.branch == "unparsed"


def test_a_label_free_or_half_labelled_response_is_ineligible_and_untouched():
    inventory = _inventory()
    for scenario, action in ((None, None), ("locations", None), (None, "query")):
        outcome = project_slu_label_v2(scenario, action, inventory)
        assert (outcome.scenario, outcome.action) == (scenario, action)
        assert outcome.eligible is False
        assert outcome.changed is False
        assert outcome.branch == "no-label"


def test_an_empty_string_scenario_falls_back_to_v1_because_it_owns_nothing():
    inventory = _inventory()
    assert inventory.owners_of("") == ()
    outcome = project_slu_label_v2("", "", inventory)
    v1 = project_slu_label("", "", inventory)
    assert (outcome.scenario, outcome.action) == (v1.scenario, v1.action)
    assert outcome.branch == "edit-distance"
    assert (outcome.scenario, outcome.action) in inventory.pairs


def test_v2_agrees_with_v1_on_every_row_it_does_not_promote():
    """The relationship the preregistration states: v2 is v1 plus one branch,
    so it can only differ where that branch fires."""

    inventory = _inventory()
    probes = [
        ("alarm", "set"),
        ("alarm", "sett"),
        ("emails", "querry"),
        ("recommendation", "set"),
        ("nosuchthing", "nosuchaction"),
        ("", "x"),
        ("locations", "query"),
        ("query", "x"),
    ]
    promoted = 0
    for scenario, action in probes:
        v1 = project_slu_label(scenario, action, inventory)
        v2 = project_slu_label_v2(scenario, action, inventory)
        if v2.branch == "promote":
            promoted += 1
            continue
        assert (v2.scenario, v2.action, v2.changed, v2.eligible, v2.branch) == (
            v1.scenario,
            v1.action,
            v1.changed,
            v1.eligible,
            v1.branch,
        )
    assert promoted == 2


def test_the_projection_is_deterministic_and_idempotent():
    inventory = _inventory()
    first = project_slu_label_v2("locations", "query", inventory)
    again = project_slu_label_v2("locations", "query", inventory)
    assert (first.scenario, first.action) == (again.scenario, again.action)
    settled = project_slu_label_v2(first.scenario, first.action, inventory)
    assert settled.changed is False


def test_the_two_rule_identities_are_distinct():
    assert SLURP_LABEL_PROJECTION_V2_ID == "slurp-legal-label-projection-v2"
    assert SLURP_LABEL_PROJECTION_V2_ID != SLURP_LABEL_PROJECTION_ID


# ---------------------------------------------------------------------------
# 4. The registered scorers
# ---------------------------------------------------------------------------


def test_both_v2_scorer_ids_are_registered_and_v1_still_is():
    names = SCORERS.names()
    for name in (
        "slurp-slu",
        "slurp-slu-official",
        "slurp-slu-projected",
        "slurp-slu-official-projected",
        "slurp-slu-projected-v2",
        "slurp-slu-official-projected-v2",
    ):
        assert name in names


def test_both_v2_ids_resolve_one_function_that_is_neither_v1_nor_the_unprojected_one():
    short = SCORERS.resolve("slurp-slu-projected-v2")
    explicit = SCORERS.resolve("slurp-slu-official-projected-v2")
    assert short is explicit
    assert short is score_slurp_outputs_official_projected_v2
    assert short is not score_slurp_outputs_official_projected
    assert short is not score_slurp_outputs_official
    assert short is not SCORERS.resolve("slurp-slu-official-projected")


# ---------------------------------------------------------------------------
# 5. End to end through the registered scorer, against a fake official
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
    """One gold row whose intent is ``recommendation_locations`` -- the real
    residual class -- and the fake evaluator, with the TRAIN inventory replaced
    by :data:`_PAIRING` / :data:`_PRIOR`."""

    record = _gold(
        "slurp:devel:000001:rec-a",
        "recommendation",
        "locations",
        (SlotEntity("place_name", "berlin"),),
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


_RESIDUAL_ROW = json.dumps(
    {
        "scenario": "locations",
        "action": "query",
        "entities": [{"type": "place_name", "filler": "berlin"}],
    }
)


def test_the_v2_scorer_promotes_before_the_official_file_and_v1_does_not(wired):
    _record, captured, tmp_path = wired
    outputs = _write(tmp_path, _RESIDUAL_ROW)

    result = SCORERS.resolve("slurp-slu-official-projected-v2")(outputs, {}, tmp_path)
    prediction = captured["predictions"][0]
    assert (prediction["scenario"], prediction["action"]) == ("recommendation", "locations")
    # Entities reach the official file untouched.
    assert prediction["entities"] == [{"type": "place_name", "filler": "berlin"}]

    row = result["per_sample"][0]
    assert row["projected"] is True
    assert row["projected_from"] == "locations_query"
    assert row["projected_to"] == "recommendation_locations"
    assert row["projected_branch"] == "promote"
    # The gold row IS recommendation_locations, so v2 turns a miss into a hit.
    assert row["scenario_action_exact"] == 1.0

    projection = result["aggregate"]["projection"]
    assert projection["applied"] is True
    assert projection["projection_id"] == SLURP_LABEL_PROJECTION_V2_ID
    assert projection["projection_version"] == "v2"
    assert projection["branch_counts"]["promote"] == 1
    assert projection["map"] == {"locations_query -> recommendation_locations": 1}
    assert projection["map_by_branch"] == {
        "promote": {"locations_query -> recommendation_locations": 1}
    }

    v1_result = SCORERS.resolve("slurp-slu-official-projected")(outputs, {}, tmp_path)
    v1_row = v1_result["per_sample"][0]
    assert v1_row["projected_to"] != "recommendation_locations"
    assert v1_row["projected_branch"] == "edit-distance"
    assert v1_row["scenario_action_exact"] == 0.0
    assert v1_result["aggregate"]["projection"]["projection_id"] == SLURP_LABEL_PROJECTION_ID
    assert v1_result["aggregate"]["projection"]["projection_version"] == "v1"


def test_the_v2_scorer_leaves_a_legal_pair_exactly_where_it_was(wired):
    _record, captured, tmp_path = wired
    outputs = _write(
        tmp_path,
        json.dumps(
            {
                "scenario": "alarm",
                "action": "query",
                "entities": [{"type": "place_name", "filler": "berlin"}],
            }
        ),
    )

    result = SCORERS.resolve("slurp-slu-projected-v2")(outputs, {}, tmp_path)

    prediction = captured["predictions"][0]
    assert (prediction["scenario"], prediction["action"]) == ("alarm", "query")
    assert result["per_sample"][0]["projected"] is False
    assert result["per_sample"][0]["projected_branch"] == "already-legal"
    assert result["aggregate"]["projection"]["counts"] == {
        "eligible": 1,
        "changed": 0,
        "unchanged": 1,
        "ineligible": 0,
    }
    assert result["aggregate"]["projection"]["branch_counts"]["promote"] == 0


def test_an_unparsable_response_stays_unparsable_through_the_v2_scorer(wired):
    _record, captured, tmp_path = wired
    outputs = _write(tmp_path, "I am not JSON at all.")

    result = SCORERS.resolve("slurp-slu-official-projected-v2")(outputs, {}, tmp_path)

    prediction = captured["predictions"][0]
    assert prediction["scenario"] is None
    assert prediction["action"] is None
    assert prediction["entities"] == []
    row = result["per_sample"][0]
    assert row["parsed"] is False
    assert row["projected"] is False
    assert row["projected_branch"] == "unparsed"
    assert result["aggregate"]["projection"]["counts"]["ineligible"] == 1


def test_an_entity_only_response_is_untouched_by_the_v2_projection(wired):
    """KC-S1a / KC-S1b answer ``{"entities": [...]}``; v2 must change nothing,
    so their entity-side numbers are provably identical in all three views."""

    _record, captured, tmp_path = wired
    outputs = _write(
        tmp_path, json.dumps({"entities": [{"type": "place_name", "filler": "berlin"}]})
    )

    projected = SCORERS.resolve("slurp-slu-official-projected-v2")(outputs, {}, tmp_path)
    prediction = captured["predictions"][0]
    assert prediction["scenario"] is None and prediction["action"] is None
    assert prediction["entities"] == [{"type": "place_name", "filler": "berlin"}]

    unprojected = SCORERS.resolve("slurp-slu-official")(outputs, {}, tmp_path)
    for field in (
        "slot_f1_exact_f1",
        "slu_f1_f1",
        "slu_f1_word_f1",
        "slu_f1_char_f1",
        "scenario_action_exact",
    ):
        assert projected["per_sample"][0][field] == unprojected["per_sample"][0][field]
    assert projected["aggregate"]["projection"]["branch_counts"]["no-label"] == 1


def test_the_entity_side_is_identical_across_all_three_views_on_a_promoted_row(wired):
    """The invariant the read asserts row by row on 5,000 arm-rows, in
    miniature: only ``scenario`` and ``action`` ever move."""

    _record, _captured, tmp_path = wired
    outputs = _write(tmp_path, _RESIDUAL_ROW)

    views = {
        "unprojected": SCORERS.resolve("slurp-slu-official")(outputs, {}, tmp_path),
        "v1": SCORERS.resolve("slurp-slu-official-projected")(outputs, {}, tmp_path),
        "v2": SCORERS.resolve("slurp-slu-official-projected-v2")(outputs, {}, tmp_path),
    }
    for field in ("slot_f1_exact_f1", "slu_f1_f1", "slu_f1_word_f1", "slu_f1_char_f1"):
        values = {name: view["per_sample"][0][field] for name, view in views.items()}
        assert len(set(values.values())) == 1, (field, values)
    assert views["unprojected"]["per_sample"][0]["scenario_action_exact"] == 0.0
    assert views["v1"]["per_sample"][0]["scenario_action_exact"] == 0.0
    assert views["v2"]["per_sample"][0]["scenario_action_exact"] == 1.0


def test_the_unprojected_scorer_still_reports_no_projection_and_loads_no_inventory(
    wired, monkeypatch
):
    _record, _captured, tmp_path = wired

    def _explode(lock, root):  # pragma: no cover - must never be reached
        raise AssertionError("the unprojected path must not read the TRAIN inventory")

    monkeypatch.setattr(soe, "load_slurp_ontology", _explode)
    monkeypatch.setattr(soe, "load_slurp_intent_slot_schema", _explode)
    outputs = _write(tmp_path, _RESIDUAL_ROW)

    result = SCORERS.resolve("slurp-slu-official")(outputs, {}, tmp_path)

    assert result["aggregate"]["projection"] == {"applied": False, "projection_id": None}
    assert "projected" not in result["per_sample"][0]
    assert "projected_branch" not in result["per_sample"][0]


def test_an_unknown_projection_version_fails_closed(wired):
    """``"v3"`` is no longer an unknown version (E4, module M3) -- probing
    with it here would exercise the real rule instead of the refusal this
    test targets, so the example moves to a version nothing registers."""

    _record, _captured, tmp_path = wired
    outputs = _write(tmp_path, _RESIDUAL_ROW)

    with pytest.raises(SlurpOfficialEvalError, match="unknown projection_version"):
        score_slurp_outputs_official(
            outputs, {}, tmp_path, project_labels=True, projection_version="v4"
        )
