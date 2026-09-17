"""USE-axis projection v3 (module M3, E4, SLURP v2 base program).

Decided by ``docs/results/2026-09-17-slurp-a1-use-projection-audit-v1.md``
and specified by ``docs/superpowers/specs/2026-09-16-slurp-v2-base-program-
design.md`` section 3 (row M3) / section 4 (item E4). Four layers, kept
apart on purpose, mirroring ``test_slurp_legal_label_projection_v2.py``'s own
structure:

1. the P2 filler-normalisation RUNGS, ported verbatim from the A1 driver;
2. the PURE label rule (``rails.slurp_projection_v3.project_slu_label_v3``)
   -- ``R_action`` then the unmodified v2 fallback;
3. the REGISTERED scorers ``slurp-slu-projected-v3`` /
   ``slurp-slu-official-projected-v3[-train]``, end to end against a fake
   official evaluator;
4. the RUNTIME delivery transform and its one config switch.
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
from speech_aware_evidence_acquisition.rails.config_tables import (
    RUN_LEVEL_SWITCH_KEYS,
    ConfigTableError,
    is_run_null_arm,
    resolve_run_switch_key,
)
from speech_aware_evidence_acquisition.rails.slurp_projection_v3 import (
    P2_FULL_RULES,
    P2_RUNGS,
    PROJECTION_BRANCH_R_ACTION,
    RUNG_0_CASE_WHITESPACE,
    RUNG_1_PUNCTUATION,
    RUNG_2_MERIDIEM,
    RUNG_3_NUMERIC,
    SLURP_PROJECTION_V3_DELIVERY_KEY,
    apply_projection_v3,
    apply_slurp_projection_v3_delivery,
    normalize_entities_p2,
    normalize_filler_p2,
    normalize_filler_p2_full,
    normalize_filler_p2_rung0_case_whitespace,
    normalize_filler_p2_rung1_punctuation,
    normalize_filler_p2_rung2_meridiem,
    normalize_filler_p2_rung3_numeric,
    project_slu_label_v3,
    render_slurp_answer,
)
from speech_aware_evidence_acquisition.reproduction import slurp_official_eval as soe
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
    OfficialSluResult,
    score_slurp_outputs_official,
    score_slurp_outputs_official_projected_v3,
    score_slurp_outputs_official_projected_v3_train,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
    SlotEntity,
    legal_intent_inventory,
    project_slu_label_v2,
)

# ---------------------------------------------------------------------------
# 1. P2 filler normalisation rungs -- byte-for-byte the A1 driver's own
#    ``normalize_filler_p2`` / ``P2_RULE_SETS`` (docs/results/
#    2026-09-17-slurp-a1-use-projection-audit-v1.md; driver read from
#    SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-A1-USE-PROJECTION-AUDIT-V1/driver/
#    a1_use_projection_audit.py at port time).
# ---------------------------------------------------------------------------


def test_rung_rule_sets_match_the_a1_ladder():
    assert RUNG_0_CASE_WHITESPACE == ("U", "L", "W")
    assert RUNG_1_PUNCTUATION == ("U", "L", "P", "W")
    assert RUNG_2_MERIDIEM == ("U", "L", "M", "P", "W")
    assert RUNG_3_NUMERIC == ("U", "L", "M", "N", "P", "W")
    assert P2_FULL_RULES == RUNG_3_NUMERIC
    assert [name for name, _rules in P2_RUNGS] == [
        "rung0_case_whitespace",
        "rung1_punctuation",
        "rung2_meridiem",
        "rung3_numeric",
    ]


def test_rung0_is_case_and_whitespace_only():
    assert normalize_filler_p2_rung0_case_whitespace("  Five   PM ") == "five pm"
    # No punctuation strip yet at rung 0.
    assert normalize_filler_p2_rung0_case_whitespace("O'Brien's!!") == "o'brien's!!"


def test_rung1_adds_punctuation_strip_but_not_meridiem():
    # "p.m." survives rung 1's own regex-free path (M not yet applied), but
    # the punctuation strip removes the dots: "p.m." -> "p m" -> collapsed.
    assert normalize_filler_p2_rung1_punctuation("5 p.m.") == "5 p m"
    assert normalize_filler_p2_rung1_punctuation("mother-in-law -- ok") == "mother-in-law ok"


def test_rung2_adds_meridiem_canonicalisation():
    assert normalize_filler_p2_rung2_meridiem("5 P.M.") == "5 pm"
    assert normalize_filler_p2_rung2_meridiem("5 a m") == "5 am"
    # Numeric words not yet applied at rung 2: the leading digit stays a digit.
    assert normalize_filler_p2_rung2_meridiem("5") == "5"


def test_rung3_is_the_full_rule_and_equals_the_default():
    assert normalize_filler_p2_rung3_numeric("5:00 P.M.") == normalize_filler_p2("5:00 P.M.")
    assert normalize_filler_p2_full is normalize_filler_p2_rung3_numeric


@pytest.mark.parametrize(
    ("filler", "expected"),
    [
        ("5:00 p.m.", "five pm"),
        ("5:05 am", "five oh five am"),
        ("50%", "fifty percent"),
        ("3rd", "third"),
        ("21st", "twenty first"),
        ("3.5", "three point five"),
        ("9am", "nine am"),
        ("42", "forty two"),
        ("seventeen", "seventeen"),
    ],
)
def test_full_p2_numeric_token_forms(filler, expected):
    assert normalize_filler_p2(filler) == expected


def test_documented_limitation_a_four_digit_year_becomes_a_cardinal():
    """Module docstring's first documented limitation: no calendar-year
    special case, so a year renders as a (long) cardinal."""

    assert normalize_filler_p2("2019") == "two thousand nineteen"


def test_documented_limitation_a_leading_currency_symbol_is_lost_not_converted():
    """The numeric rung (N) runs BEFORE the punctuation rung (P) in the fixed
    U/L/M/N/P/W order, so ``"$5"`` does not match the bare-integer rule while
    the ``$`` is still attached; only the LATER punctuation rung removes the
    symbol, by which point the numeric rung has already passed the token by.
    The digit therefore survives as a digit, not a word."""

    assert normalize_filler_p2("$5") == "5"


def test_punctuation_keeps_apostrophes_and_internal_hyphens_only():
    assert normalize_filler_p2("O'Brien's") == "o'brien's"
    assert normalize_filler_p2("mother-in-law") == "mother-in-law"
    # A leading/trailing/isolated hyphen is dropped, not kept.
    assert normalize_filler_p2("-leading") == "leading"
    assert normalize_filler_p2("trailing-") == "trailing"
    assert normalize_filler_p2("free -- standing") == "free standing"


def test_typographic_apostrophes_and_dashes_fold_to_ascii():
    assert normalize_filler_p2("O’Brien’s") == "o'brien's"
    assert normalize_filler_p2("mother‐in‐law") == "mother-in-law"


def test_a_rule_that_would_empty_a_nonempty_filler_is_refused():
    # Punctuation-only fillers strip to nothing under P; the ORIGINAL text
    # (not an empty string) must be returned.
    assert normalize_filler_p2("---") == "---"
    assert normalize_filler_p2("!!!") == "!!!"


def test_empty_and_whitespace_fillers_pass_through_unchanged():
    assert normalize_filler_p2("") == ""
    assert normalize_filler_p2("   ") == "   "


def test_normalize_entities_p2_reports_the_changed_count_asymmetrically():
    entities = (
        SlotEntity("time", "5:00 PM"),
        SlotEntity("place_name", "berlin"),
        SlotEntity("date", "2019"),
    )
    new_entities, changed = normalize_entities_p2(entities)
    assert changed == 2
    assert new_entities[0] == SlotEntity("time", "five pm")
    assert new_entities[1] == SlotEntity("place_name", "berlin")
    assert new_entities[2] == SlotEntity("date", "two thousand nineteen")
    # No support filter of any kind: every entity is kept, never dropped.
    assert len(new_entities) == len(entities)


# ---------------------------------------------------------------------------
# 2. The pure label rule: R_action, then the unmodified v2 fallback.
# ---------------------------------------------------------------------------

_INVENTORY = legal_intent_inventory(
    {
        "music": ("likeness", "dislikeness", "play", "query", "settings"),
        "play": ("audiobook", "game", "music", "podcasts", "radio"),
        "recommendation": ("events", "locations", "movies"),
    }
)


def test_a_legal_pair_is_untouched_by_r_action():
    outcome = project_slu_label_v3("music", "play", _INVENTORY)
    assert (outcome.scenario, outcome.action) == ("music", "play")
    assert outcome.changed is False
    assert outcome.branch == "already-legal"


def test_r_action_music_play_music_adopts_the_play_music_split():
    """A1's own headroom class ``music|play_music`` (docs/results/
    2026-09-17-slurp-a1-use-projection-audit-v1.md section "Two findings",
    finding 2): the delivered pair (scenario="music", action="play_music")
    is illegal, but the action string "play_music" is itself the legal
    composed id for (scenario="play", action="music"), which v2's own
    edit-distance fallback mis-repairs to ``music_likeness``."""

    outcome = project_slu_label_v3("music", "play_music", _INVENTORY)
    assert (outcome.scenario, outcome.action) == ("play", "music")
    assert outcome.branch == PROJECTION_BRANCH_R_ACTION
    assert outcome.changed is True
    assert outcome.eligible is True
    assert outcome.source_scenario == "music"
    assert outcome.source_action == "play_music"

    v2_only = project_slu_label_v2("music", "play_music", _INVENTORY)
    assert (v2_only.scenario, v2_only.action) != (outcome.scenario, outcome.action)


def test_r_action_play_play_radio_adopts_the_play_radio_split():
    """The second worked example: delivered (scenario="play",
    action="play_radio") is illegal (``play`` has no ``play_radio`` action),
    but "play_radio" is itself the legal id for (scenario="play",
    action="radio")."""

    outcome = project_slu_label_v3("play", "play_radio", _INVENTORY)
    assert (outcome.scenario, outcome.action) == ("play", "radio")
    assert outcome.branch == PROJECTION_BRANCH_R_ACTION
    assert outcome.changed is True


def test_an_illegal_action_string_that_is_not_a_composed_id_falls_to_v2():
    outcome = project_slu_label_v3("music", "zzz_not_an_id", _INVENTORY)
    v2_only = project_slu_label_v2("music", "zzz_not_an_id", _INVENTORY)
    assert (outcome.scenario, outcome.action) == (v2_only.scenario, v2_only.action)
    assert outcome.branch == v2_only.branch
    assert outcome.branch != PROJECTION_BRANCH_R_ACTION


def test_v2_promote_still_fires_when_r_action_does_not_apply():
    """v2's own PROMOTE class (an action-named scenario) is untouched by
    R_action, because R_action keys on the ACTION string, not the scenario
    one -- exactly the ``recommendation_locations`` residual class v2 itself
    was built for."""

    outcome = project_slu_label_v3("locations", "query", _INVENTORY)
    v2_only = project_slu_label_v2("locations", "query", _INVENTORY)
    assert (outcome.scenario, outcome.action) == (v2_only.scenario, v2_only.action)
    assert outcome.branch == v2_only.branch == "promote"


def test_r_action_never_fires_on_an_already_legal_pair_even_if_the_action_looks_composed():
    """Guard order: R_action's precondition is "pair is illegal" FIRST. A
    legal pair whose action string happens to equal some OTHER legal id must
    never be re-routed."""

    inventory = legal_intent_inventory(
        {"play": ("music",), "play_music": ("x",)},
        None,
    )
    outcome = project_slu_label_v3("play", "music", inventory)
    assert (outcome.scenario, outcome.action) == ("play", "music")
    assert outcome.branch == "already-legal"


def test_r_action_requires_both_halves_and_a_parsed_response():
    unparsed = project_slu_label_v3(None, None, _INVENTORY, parsed=False)
    assert unparsed.branch == "unparsed" and unparsed.changed is False
    half = project_slu_label_v3("music", None, _INVENTORY)
    assert half.branch == "no-label" and half.changed is False


def test_entities_are_never_an_argument_to_the_label_rule():
    """Task instruction 3: intent accuracy moves only through the label
    rule; :func:`project_slu_label_v3` takes no entities parameter at all,
    so this is enforced by the function's own signature, not by convention."""

    import inspect

    parameters = inspect.signature(project_slu_label_v3).parameters
    assert "entities" not in parameters


def test_apply_projection_v3_changes_labels_only_through_the_label_half():
    entities = (SlotEntity("time", "5 PM"),)
    outcome = apply_projection_v3("music", "play_music", entities, _INVENTORY)
    assert (outcome.scenario, outcome.action) == ("play", "music")
    assert outcome.label.branch == PROJECTION_BRANCH_R_ACTION
    assert outcome.fillers_changed == 1
    assert outcome.any_filler_changed is True
    assert outcome.entities[0].filler == "five pm"
    # The entity TYPE is never touched by either half.
    assert outcome.entities[0].type == "time"


# ---------------------------------------------------------------------------
# 3. The registered scorers, end to end against a fake official evaluator
#    (mirrors test_slurp_legal_label_projection_v2.py's own "wired" fixture).
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


_PAIRING = {
    "music": ("likeness", "dislikeness", "play", "query", "settings"),
    "play": ("audiobook", "game", "music", "podcasts", "radio"),
    "recommendation": ("events", "locations", "movies"),
}
_PRIOR = {f"{scenario}_{action}": 10 for scenario, actions in _PAIRING.items() for action in actions}


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
            "scenario", "action", "intent", "entities",
            "entities_distance_word", "entities_distance_char", "slu_f1",
        )
    }
    return OfficialSluResult(
        scenario_accuracy=0.0, action_accuracy=0.0, intent_accuracy=0.0,
        slu_f1=1.0, span_f1=1.0, raw=raw, stdout="fake",
        command=("python", "evaluate.py"),
    )


@pytest.fixture()
def wired(monkeypatch, tmp_path):
    """One gold row whose intent is ``play_music`` -- the class A1's own
    ``music_play_music -> play_music`` finding names -- and the fake
    evaluator, TRAIN inventory replaced by :data:`_PAIRING` / :data:`_PRIOR`.
    """

    record = _gold(
        "slurp:devel:000001:rec-a", "play", "music",
        (SlotEntity("time", "5:00 PM"),),
    )
    monkeypatch.setattr(
        soe, "load_slurp_split",
        lambda lock, root, split_id, *, allow_heldout=False, allow_synthetic=False: [record],
    )
    monkeypatch.setattr(soe, "load_slurp_ontology", lambda lock, root: _FakeOntology(_PAIRING))
    monkeypatch.setattr(
        soe, "load_slurp_intent_slot_schema",
        lambda lock, root: _FakeSchema({intent: _FakeIntentProfile(n) for intent, n in _PRIOR.items()}),
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


_ILLEGAL_ROW_WITH_TIME_FILLER = json.dumps(
    {
        "scenario": "music",
        "action": "play_music",
        "entities": [{"type": "time", "filler": "5:00 PM"}],
    }
)


def test_both_v3_scorer_ids_are_registered_beside_v1_and_v2():
    names = SCORERS.names()
    for name in (
        "slurp-slu-projected-v3",
        "slurp-slu-official-projected-v3",
        "slurp-slu-official-projected-v3-train",
        "slurp-slu-projected-v2",
        "slurp-slu-official-projected-v2",
    ):
        assert name in names


def test_both_v3_ids_resolve_one_function_distinct_from_v1_v2_and_unprojected():
    short = SCORERS.resolve("slurp-slu-projected-v3")
    explicit = SCORERS.resolve("slurp-slu-official-projected-v3")
    assert short is explicit
    assert short is score_slurp_outputs_official_projected_v3
    assert short is not SCORERS.resolve("slurp-slu-official-projected-v2")
    assert short is not SCORERS.resolve("slurp-slu-official-projected")
    assert short is not SCORERS.resolve("slurp-slu-official")


def test_the_v3_scorer_applies_r_action_and_p2_together(wired):
    _record, captured, tmp_path = wired
    outputs = _write(tmp_path, _ILLEGAL_ROW_WITH_TIME_FILLER)

    result = SCORERS.resolve("slurp-slu-official-projected-v3")(outputs, {}, tmp_path)
    prediction = captured["predictions"][0]
    assert (prediction["scenario"], prediction["action"]) == ("play", "music")
    assert prediction["entities"] == [{"type": "time", "filler": "five pm"}]

    row = result["per_sample"][0]
    assert row["projected"] is True
    assert row["projected_from"] == "music_play_music"
    assert row["projected_to"] == "play_music"
    assert row["projected_branch"] == PROJECTION_BRANCH_R_ACTION
    assert row["fillers_changed"] == 1
    # The gold intent IS play_music, so R_action turns a miss into a hit.
    assert row["scenario_action_exact"] == 1.0

    projection = result["aggregate"]["projection"]
    assert projection["projection_version"] == "v3"
    assert projection["branch_counts"][PROJECTION_BRANCH_R_ACTION] == 1
    assert projection["map"] == {"music_play_music -> play_music": 1}

    filler_normalization = result["aggregate"]["filler_normalization"]
    assert filler_normalization["applied"] is True
    assert filler_normalization["changed_count"] == 1


def test_the_v3_scorer_never_drops_an_entity_unlike_the_rejected_support_filter(wired):
    """A1 rejected P1a/P1b; v3 carries no support filter at all, so an entity
    whose type has zero TRAIN support under the delivered intent is still
    scored, merely with its filler normalised."""

    _record, captured, tmp_path = wired
    outputs = _write(
        tmp_path,
        json.dumps(
            {
                "scenario": "music",
                "action": "play_music",
                "entities": [{"type": "unsupported_type", "filler": "5:00 PM"}],
            }
        ),
    )
    SCORERS.resolve("slurp-slu-official-projected-v3")(outputs, {}, tmp_path)
    prediction = captured["predictions"][0]
    assert len(prediction["entities"]) == 1
    assert prediction["entities"][0] == {"type": "unsupported_type", "filler": "five pm"}


def test_v3_train_scorer_scores_against_train_split(wired, monkeypatch):
    _record, _captured, tmp_path = wired
    seen_split = {}

    real_split_loader = soe.load_slurp_split

    def _capture_split(lock, root, split_id, **kwargs):
        seen_split["split_id"] = split_id
        return real_split_loader(lock, root, split_id, **kwargs)

    monkeypatch.setattr(soe, "load_slurp_split", _capture_split)
    outputs = _write(tmp_path, _ILLEGAL_ROW_WITH_TIME_FILLER)
    score_slurp_outputs_official_projected_v3_train(outputs, {}, tmp_path)
    assert seen_split["split_id"] == "train"


def test_an_unparsable_response_stays_unparsable_through_the_v3_scorer(wired):
    _record, captured, tmp_path = wired
    outputs = _write(tmp_path, "not json at all")

    result = SCORERS.resolve("slurp-slu-official-projected-v3")(outputs, {}, tmp_path)
    prediction = captured["predictions"][0]
    assert prediction["scenario"] is None
    assert prediction["action"] is None
    assert prediction["entities"] == []
    row = result["per_sample"][0]
    assert row["parsed"] is False
    assert row["projected"] is False
    assert row["projected_branch"] == "unparsed"
    assert row["fillers_changed"] == 0


def test_an_unknown_projection_version_still_fails_closed(wired):
    _record, _captured, tmp_path = wired
    outputs = _write(tmp_path, _ILLEGAL_ROW_WITH_TIME_FILLER)
    with pytest.raises(soe.SlurpOfficialEvalError, match="unknown projection_version"):
        score_slurp_outputs_official(
            outputs, {}, tmp_path, project_labels=True, projection_version="vNotReal"
        )


def test_project_fillers_alone_does_not_require_project_labels(wired):
    """The two knobs are independent in the general function, even though
    module M3's own scorers always turn both on together."""

    _record, captured, tmp_path = wired
    outputs = _write(
        tmp_path,
        json.dumps(
            {
                "scenario": "play",
                "action": "music",
                "entities": [{"type": "time", "filler": "5:00 PM"}],
            }
        ),
    )
    result = score_slurp_outputs_official(
        outputs, {}, tmp_path, project_labels=False, project_fillers=True
    )
    prediction = captured["predictions"][0]
    assert (prediction["scenario"], prediction["action"]) == ("play", "music")
    assert prediction["entities"] == [{"type": "time", "filler": "five pm"}]
    assert result["aggregate"]["projection"] == {"applied": False, "projection_id": None}
    assert result["aggregate"]["filler_normalization"]["applied"] is True


# ---------------------------------------------------------------------------
# 4. The runtime delivery transform.
# ---------------------------------------------------------------------------


def test_render_slurp_answer_matches_the_canonical_shape_parse_round_trips():
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

    text = render_slurp_answer("play", "music", (SlotEntity("time", "five pm"),))
    scenario, action, entities, parsed = parse_slu_response(text)
    assert parsed is True
    assert (scenario, action) == ("play", "music")
    assert entities == [SlotEntity("time", "five pm")]


def test_delivery_transform_refuses_a_non_slurp_carrier():
    with pytest.raises(ValueError, match="only defined for the 'slurp' carrier"):
        apply_slurp_projection_v3_delivery(
            "{}", carrier_lock_key="earnings21-original", inventory=_INVENTORY
        )


def test_delivery_transform_is_byte_identical_on_an_unparsed_response():
    raw = "I did not answer in JSON."
    result = apply_slurp_projection_v3_delivery(raw, carrier_lock_key="slurp", inventory=_INVENTORY)
    assert result.text == raw
    assert result.changed is False
    assert result.metadata["applied"] is False


def test_delivery_transform_projects_an_illegal_label_and_normalises_fillers():
    raw = render_slurp_answer("music", "play_music", (SlotEntity("time", "5:00 PM"),))
    result = apply_slurp_projection_v3_delivery(raw, carrier_lock_key="slurp", inventory=_INVENTORY)
    assert result.changed is True
    delivered_scenario, delivered_action, delivered_entities, parsed = _parse(result.text)
    assert (delivered_scenario, delivered_action) == ("play", "music")
    assert delivered_entities == [SlotEntity("time", "five pm")]
    assert result.metadata["label_branch"] == PROJECTION_BRANCH_R_ACTION
    assert result.metadata["label_changed"] is True
    assert result.metadata["fillers_changed"] == 1
    # The RAW text is never overwritten in place -- the caller (the runtime
    # seal point) is responsible for custody; this function's own contract
    # is simply that ``raw`` (the argument) is untouched, which the type
    # system already guarantees (str is immutable) and this assertion pins.
    assert raw != result.text


def test_delivery_transform_is_a_no_op_on_an_already_legal_normalised_answer():
    """The property the program design cites: once a cell delivers through
    this transform, the scorer-side v3 projection becomes a no-op on it."""

    raw = render_slurp_answer("play", "music", (SlotEntity("time", "five pm"),))
    result = apply_slurp_projection_v3_delivery(raw, carrier_lock_key="slurp", inventory=_INVENTORY)
    assert result.changed is False
    assert result.text == raw


def _parse(text):
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

    return parse_slu_response(text)


# ---------------------------------------------------------------------------
# 5. The one config switch: the "run" class, mirroring
#    test_config_table_module_switches.py's own ``obs_prefetch_depth`` proof.
# ---------------------------------------------------------------------------


def test_the_delivery_switch_is_a_flat_run_level_key_on_the_closed_allowlist():
    assert SLURP_PROJECTION_V3_DELIVERY_KEY == "slurp_projection_v3_delivery"
    assert SLURP_PROJECTION_V3_DELIVERY_KEY in RUN_LEVEL_SWITCH_KEYS
    assert resolve_run_switch_key(SLURP_PROJECTION_V3_DELIVERY_KEY) == SLURP_PROJECTION_V3_DELIVERY_KEY
    with pytest.raises(ConfigTableError, match="is dotted"):
        resolve_run_switch_key(f"run.{SLURP_PROJECTION_V3_DELIVERY_KEY}")


def test_the_delivery_switch_null_arm_is_absent_or_zero_never_true():
    assert is_run_null_arm(None) is True
    assert is_run_null_arm(0) is True
    assert is_run_null_arm(1) is False
    # A bool is deliberately never treated as this class's null arm (module
    # docstring of ``rails.config_tables.is_run_null_arm``); the fragments
    # this study authors always spell the switch as the INTEGER 0 or 1, not
    # a JSON boolean, for exactly this reason.
    assert is_run_null_arm(True) is False
    assert is_run_null_arm(False) is False


def test_the_held_baseline_fragments_declare_the_switch_and_resolve_every_scorer(
    monkeypatch,
):
    """Deliverable 3's own closed-loop proof: both held fragments carry the
    flat switch and name only registered scorer ids -- the same "every
    registry value must resolve" discipline
    ``scripts/checks/engineering_base_check.py`` enforces at the repository
    level, checked here without spawning that whole script."""

    repo_root = Path(__file__).resolve().parents[2]
    for name in (
        "slurp-native-dual-store-train-fold-a-review-off-projected-v3-v1",
        "slurp-native-dual-store-train-fold-a-anchor-projected-v3-v1",
    ):
        path = repo_root / "configs" / "baseline" / f"{name}.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        assert document[SLURP_PROJECTION_V3_DELIVERY_KEY] == 1
        for scorer_name in document["scorers"]:
            assert scorer_name in SCORERS.names(), (name, scorer_name)
        assert "slurp-slu-official-projected-v3-train" in document["scorers"]
        assert "slurp-slu-official-train" in document["scorers"]
