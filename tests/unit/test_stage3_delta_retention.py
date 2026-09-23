"""Stage-3 S3-6: the delta-store RETENTION rule (owner decision 83).

Five obligations:

1. The scenario mapping is the intent id's prefix, and a facet that names no
   scenario of the read is recorded as unmapped rather than guessed at.
2. The per-scenario null band is derived from the plan's OWN-NULL
   (PLAN vs PLANr) per-scenario deltas, floored at the registered pooled
   own-null half-width, because the registered own-null table carries no
   per-scenario band.
3. The scenario rule: RETIRE when every targeted scenario is harmed beyond
   its own band, KEEP when any targeted scenario gains beyond it.
4. The tie rule (the frontier-slope weighting): everything else is decided
   by the value's own per-delta paired SLU mean against a CLI threshold
   whose default is 0.0 pp.
5. The CLI writes ids, counts and percentages only -- never a statement.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "build_slurp_stage3_delta_retention",
    REPO_ROOT / "scripts" / "build_slurp_stage3_delta_retention.py",
)
cli = importlib.util.module_from_spec(_spec)
sys.modules.setdefault(_spec.name, cli)
_spec.loader.exec_module(cli)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# 1. The scenario mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("facet", "scenario"),
    [
        ("alarm_set", "alarm"),
        ("qa_factoid", "qa"),
        ("datetime_query", "datetime"),
        ("recommendation_events", "recommendation"),
        ("general", "general"),
    ],
)
def test_the_scenario_is_the_intent_id_prefix(facet, scenario) -> None:
    assert cli.scenario_of(facet) == scenario


# ---------------------------------------------------------------------------
# 2. The derived per-scenario null band
# ---------------------------------------------------------------------------


def test_the_band_is_the_own_null_magnitude_floored() -> None:
    band = cli.derive_null_band(
        {"alarm": 0.63, "audio": 12.17, "news": -1.5961}, floor_pp=1.2485
    )
    # A scenario whose replicate barely moved cannot be declared noiseless:
    # the registered pooled half-width is the floor.
    assert band["alarm"] == pytest.approx(1.2485)
    # A scenario whose replicate moved a lot keeps its own, wider band.
    assert band["audio"] == pytest.approx(12.17)
    # The band is a MAGNITUDE: the sign of the replicate movement is not it.
    assert band["news"] == pytest.approx(1.5961)


def test_a_non_positive_floor_is_refused() -> None:
    with pytest.raises(cli.Stage3DeltaRetentionError):
        cli.derive_null_band({"alarm": 1.0}, floor_pp=0.0)


@pytest.mark.parametrize(
    ("delta", "signal"),
    [
        (-6.7822, cli.SIGNAL_HARM),
        (4.1496, cli.SIGNAL_GAIN),
        (0.2394, cli.SIGNAL_BAND),
        (-1.2485, cli.SIGNAL_BAND),  # exactly on the band edge is INSIDE it
        (1.2485, cli.SIGNAL_BAND),
    ],
)
def test_the_signal_is_the_delta_against_that_scenarios_band(delta, signal) -> None:
    assert cli.scenario_signal(delta, 1.2485) == signal


# ---------------------------------------------------------------------------
# 3 and 4. The decision itself
# ---------------------------------------------------------------------------


def _outcome(mean, *, rows=10):
    return {
        "rows_reached": rows, "rows_joined": rows, "nodes": ["solver"],
        "mean_delta_pp": mean, "saves": 1, "harms": 1, "neutral": rows - 2,
    }


def _decide(signals, outcome, **kwargs):
    kwargs.setdefault("tie_threshold_pp", 0.0)
    kwargs.setdefault("unreached_policy", cli.UNREACHED_KEEP)
    return cli.decide_row(signals=signals, outcome=outcome, **kwargs)


def test_every_targeted_scenario_harmed_beyond_the_band_retires() -> None:
    decision, rule, _ = _decide(
        {"alarm": cli.SIGNAL_HARM, "news": cli.SIGNAL_HARM}, _outcome(5.0)
    )
    # The per-delta mean is strongly positive and does NOT save it: the
    # scenario rule decides first, exactly as decision 83 words it.
    assert (decision, rule) == (cli.DECISION_RETIRE, cli.RULE_SCENARIO)


def test_one_gaining_scenario_keeps_the_delta_even_beside_a_harmed_one() -> None:
    decision, rule, _ = _decide(
        {"general": cli.SIGNAL_HARM, "datetime": cli.SIGNAL_GAIN}, _outcome(-9.0)
    )
    assert (decision, rule) == (cli.DECISION_KEEP, cli.RULE_SCENARIO)


def test_a_within_band_delta_is_kept_by_a_positive_per_delta_mean() -> None:
    decision, rule, _ = _decide({"calendar": cli.SIGNAL_BAND}, _outcome(0.9))
    assert (decision, rule) == (cli.DECISION_KEEP, cli.RULE_TIE)


def test_a_within_band_delta_is_retired_by_a_non_positive_per_delta_mean() -> None:
    for mean in (0.0, -0.4):
        decision, rule, _ = _decide({"calendar": cli.SIGNAL_BAND}, _outcome(mean))
        assert (decision, rule) == (cli.DECISION_RETIRE, cli.RULE_TIE)


def test_the_tie_threshold_is_a_parameter_not_a_constant() -> None:
    signals = {"calendar": cli.SIGNAL_BAND}
    assert _decide(signals, _outcome(0.5))[0] == cli.DECISION_KEEP
    assert (
        _decide(signals, _outcome(0.5), tie_threshold_pp=1.0)[0]
        == cli.DECISION_RETIRE
    )


def test_harm_mixed_with_in_band_and_no_gain_falls_to_the_tie_rule() -> None:
    signals = {"alarm": cli.SIGNAL_HARM, "calendar": cli.SIGNAL_BAND}
    # NOT every targeted scenario is harmed beyond the band, and none gains,
    # so the cost weight -- not the scenario rule -- decides.
    assert _decide(signals, _outcome(1.5))[:2] == (cli.DECISION_KEEP, cli.RULE_TIE)
    assert _decide(signals, _outcome(-1.5))[:2] == (
        cli.DECISION_RETIRE, cli.RULE_TIE
    )


def test_a_value_resolving_no_scenario_falls_to_the_tie_rule() -> None:
    assert _decide({}, _outcome(2.0))[:2] == (cli.DECISION_KEEP, cli.RULE_TIE)


def test_a_value_the_flight_never_supplied_follows_the_unreached_policy() -> None:
    assert _decide({"calendar": cli.SIGNAL_BAND}, None)[0] == cli.DECISION_KEEP
    assert _decide({"calendar": cli.SIGNAL_BAND}, _outcome(0.0, rows=0))[0] == (
        cli.DECISION_KEEP
    )
    assert (
        _decide(
            {"calendar": cli.SIGNAL_BAND}, None,
            unreached_policy=cli.UNREACHED_RETIRE,
        )[0]
        == cli.DECISION_RETIRE
    )


# ---------------------------------------------------------------------------
# 5. The CLI end to end
# ---------------------------------------------------------------------------

STATEMENT = "Keep the time slot whenever the speech states a clock time."
#: scenario -> (CELL-1 delta, own-null delta). alarm is harmed beyond its
#: floored band, datetime gains beyond its own, calendar and email sit
#: inside theirs.
SCENARIOS = {
    "alarm": (-6.7822, 0.6313),
    "datetime": (4.1496, 3.7738),
    "calendar": (0.2394, -1.1285),
    "email": (2.1595, 5.2555),
}


def _per_scenario_tables(path, index):
    path.write_text(
        json.dumps({
            "recipe_id": "test",
            "natural_mixture_and_equal_scenario": {
                "arm_vs_comparator": {
                    "pooled_slu_f1_per_scenario": {
                        scenario: {
                            "delta_pp": values[index], "n": 60,
                            "left_pct": 50.0, "right_pct": 50.0 + values[index],
                        }
                        for scenario, values in SCENARIOS.items()
                    }
                }
            },
        }),
        encoding="utf-8", newline="\n",
    )
    return path


def _fixture(tmp_path):
    authored = tmp_path / "authored.json"
    authored.write_text(
        json.dumps({
            "schema": "saea-stage3-authored-deltas-v2",
            "iteration": 1,
            "facet_rule": "source-intent",
            "rows": [
                {
                    "value_id": "delta:1:aaaaaaaaaaaa", "content": STATEMENT,
                    "associated_facet_ids": ["alarm_set"], "node_target": "solver",
                    "source_sample_ids": ["train-1"], "provenance_refs": ["r"],
                    "task_target": "solver:slot-contract:alarm_set",
                    "prior_score": 0.6,
                },
                {
                    "value_id": "delta:1:bbbbbbbbbbbb", "content": STATEMENT,
                    "associated_facet_ids": ["datetime_query"],
                    "node_target": "perception",
                    "source_sample_ids": ["train-2"], "provenance_refs": ["r"],
                    "task_target": "perception:perception-hint:datetime_query",
                    "prior_score": 0.6,
                },
                {
                    "value_id": "delta:1:cccccccccccc", "content": STATEMENT,
                    "associated_facet_ids": ["calendar_set"],
                    "node_target": "reviewer",
                    "source_sample_ids": ["train-3"], "provenance_refs": ["r"],
                    "task_target": "reviewer:reviewer-criterion:calendar_set",
                    "prior_score": 0.6,
                },
                {
                    "value_id": "delta:1:dddddddddddd", "content": STATEMENT,
                    "associated_facet_ids": ["email_query"], "node_target": "planner",
                    "source_sample_ids": ["train-4"], "provenance_refs": ["r"],
                    "task_target": "planner:planner-rule:email_query",
                    "prior_score": 0.6,
                },
            ],
        }),
        encoding="utf-8", newline="\n",
    )
    consumption = tmp_path / "delta-consumption.json"
    consumption.write_text(
        json.dumps({
            "schema": "saea-stage3-delta-consumption-v1",
            "consumption": {
                "per_value_id": {
                    "stage3-deltas::delta:1:aaaaaaaaaaaa": {
                        "rows_reached": 10, "nodes": ["solver"],
                        "outcome": {
                            "rows_joined": 10,
                            "slu_f1": {
                                "mean_delta_pp": 4.0, "saves": 3, "harms": 1,
                                "neutral": 6,
                            },
                            "intent": {
                                "mean_delta_pp": 0.0, "saves": 0, "harms": 0,
                                "neutral": 10,
                            },
                        },
                    },
                    "stage3-deltas::delta:1:cccccccccccc": {
                        "rows_reached": 20, "nodes": ["reviewer"],
                        "outcome": {
                            "rows_joined": 20,
                            "slu_f1": {
                                "mean_delta_pp": 1.5, "saves": 4, "harms": 1,
                                "neutral": 15,
                            },
                            "intent": {
                                "mean_delta_pp": 0.0, "saves": 0, "harms": 0,
                                "neutral": 20,
                            },
                        },
                    },
                    "stage3-deltas::delta:1:dddddddddddd": {
                        "rows_reached": 8, "nodes": ["planner"],
                        "outcome": {
                            "rows_joined": 8,
                            "slu_f1": {
                                "mean_delta_pp": -2.5, "saves": 0, "harms": 3,
                                "neutral": 5,
                            },
                            "intent": {
                                "mean_delta_pp": 0.0, "saves": 0, "harms": 0,
                                "neutral": 8,
                            },
                        },
                    },
                }
            },
        }),
        encoding="utf-8", newline="\n",
    )
    facts = tmp_path / "registered-facts.json"
    facts.write_text(
        json.dumps({
            "own_null_table": {
                "pooled_micro": {"slu_f1_micro": {"ci95_half_width": 1.2485}}
            }
        }),
        encoding="utf-8", newline="\n",
    )
    return (
        authored,
        _per_scenario_tables(tmp_path / "cell.json", 0),
        _per_scenario_tables(tmp_path / "null.json", 1),
        consumption,
        facts,
    )


def _run(tmp_path, *extra):
    authored, cell, null, consumption, facts = _fixture(tmp_path)
    out_json = tmp_path / "retention-v2.json"
    out_markdown = tmp_path / "retention-v2.md"
    argv = [
        "--authored", str(authored),
        "--cell-per-scenario", str(cell),
        "--own-null-per-scenario", str(null),
        "--delta-consumption", str(consumption),
        "--registered-facts", str(facts),
        "--out-json", str(out_json),
        "--out-markdown", str(out_markdown),
        *extra,
    ]
    assert cli.main(argv) == 0
    return json.loads(out_json.read_text(encoding="utf-8")), out_markdown


def test_the_cli_decides_every_row_and_names_the_retired_ids(tmp_path, capsys) -> None:
    document, _ = _run(tmp_path)
    by_id = {entry["value_id"]: entry for entry in document["decisions"]}
    # alarm is harmed beyond its floored band -> the scenario rule retires it
    # although its own per-delta mean is +4.0 pp.
    assert by_id["delta:1:aaaaaaaaaaaa"]["decision"] == cli.DECISION_RETIRE
    assert by_id["delta:1:aaaaaaaaaaaa"]["rule"] == cli.RULE_SCENARIO
    # datetime gains beyond its own band; the value was never supplied and
    # does not need to be, because the scenario rule decides first.
    assert by_id["delta:1:bbbbbbbbbbbb"]["decision"] == cli.DECISION_KEEP
    assert by_id["delta:1:bbbbbbbbbbbb"]["rule"] == cli.RULE_SCENARIO
    assert by_id["delta:1:bbbbbbbbbbbb"]["per_delta"] is None
    # calendar is inside its band and the value paid for itself.
    assert by_id["delta:1:cccccccccccc"]["decision"] == cli.DECISION_KEEP
    assert by_id["delta:1:cccccccccccc"]["rule"] == cli.RULE_TIE
    # email is inside its band and the value did not.
    assert by_id["delta:1:dddddddddddd"]["decision"] == cli.DECISION_RETIRE
    assert by_id["delta:1:dddddddddddd"]["rule"] == cli.RULE_TIE

    assert document["retired_value_ids"] == [
        "delta:1:aaaaaaaaaaaa", "delta:1:dddddddddddd"
    ]
    assert document["summary"]["kept"] == 2
    assert document["summary"]["retired"] == 2
    assert document["summary"]["per_node"]["solver"] == {"KEEP": 0, "RETIRE": 1}
    assert document["summary"]["per_rule"][cli.RULE_TIE] == {"KEEP": 1, "RETIRE": 1}
    assert document["summary"]["values_never_supplied"] == 1
    assert document["summary"]["unmapped_facet_ids"] == {}
    assert document["null_band"]["floor_pp"] == pytest.approx(1.2485)
    assert document["per_scenario"]["alarm"]["band_bound_by"] == "floor"
    assert document["per_scenario"]["email"]["band_bound_by"] == "own-null"
    # The console report carries ids, counts and digests -- never a statement.
    assert STATEMENT not in capsys.readouterr().out


def test_neither_output_carries_statement_text(tmp_path) -> None:
    document, out_markdown = _run(tmp_path)
    assert STATEMENT not in json.dumps(document)
    assert STATEMENT not in out_markdown.read_text(encoding="utf-8")


def test_the_markdown_summary_carries_the_counts_and_the_scenario_table(
    tmp_path,
) -> None:
    _, out_markdown = _run(tmp_path)
    text = out_markdown.read_text(encoding="utf-8")
    assert "kept: **2**, retired: **2**" in text
    for scenario in SCENARIOS:
        assert f"| {scenario} |" in text
    assert "harm-beyond-band" in text and "gain-beyond-band" in text


def test_the_unreached_policy_reaches_the_cli(tmp_path) -> None:
    document, _ = _run(tmp_path, "--unreached-policy", "retire")
    by_id = {entry["value_id"]: entry for entry in document["decisions"]}
    # Still KEPT: its scenario gains beyond the band, so the tie rule -- and
    # with it the unreached policy -- is never reached.
    assert by_id["delta:1:bbbbbbbbbbbb"]["decision"] == cli.DECISION_KEEP
    assert document["unreached_policy"] == "retire"


def test_a_scenario_the_own_null_read_does_not_carry_is_refused(tmp_path) -> None:
    authored, cell, null, consumption, facts = _fixture(tmp_path)
    document = json.loads(null.read_text(encoding="utf-8"))
    table = document["natural_mixture_and_equal_scenario"]["arm_vs_comparator"]
    table["pooled_slu_f1_per_scenario"].pop("alarm")
    null.write_text(json.dumps(document), encoding="utf-8", newline="\n")
    with pytest.raises(cli.Stage3DeltaRetentionError, match="refusing to invent"):
        cli.main([
            "--authored", str(authored),
            "--cell-per-scenario", str(cell),
            "--own-null-per-scenario", str(null),
            "--delta-consumption", str(consumption),
            "--registered-facts", str(facts),
            "--out-json", str(tmp_path / "out.json"),
            "--out-markdown", str(tmp_path / "out.md"),
        ])


def test_a_band_floor_is_required_one_way_or_the_other(tmp_path) -> None:
    authored, cell, null, consumption, _ = _fixture(tmp_path)
    with pytest.raises(cli.Stage3DeltaRetentionError):
        cli.main([
            "--authored", str(authored),
            "--cell-per-scenario", str(cell),
            "--own-null-per-scenario", str(null),
            "--delta-consumption", str(consumption),
            "--out-json", str(tmp_path / "out.json"),
            "--out-markdown", str(tmp_path / "out.md"),
        ])
