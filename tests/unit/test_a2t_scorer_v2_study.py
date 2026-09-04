"""``analysis.a2t_scorer_v2_study``: the slice-S1 zero-contact re-scoring study.

Every case here is hand-authored and synthetic (no real Audio2Tool data, no
data root, no umbrella lock) -- this module never touches ``SPEECHRL_DATA_DIR``
or the committed sealed-summary JSON files; that real-data path is exercised
only by the actual one-shot study run, not by this test suite.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_scorer_v2_study import (
    ArmInput,
    RowClassification,
    ScorerV2StudyError,
    SourceInput,
    build_per_row_entries,
    build_registry_defaults,
    classify_row,
    identity_check,
    load_outputs_rows,
    main as study_main,
    paired_counts,
    parse_argument_defaults,
    per_tier_v1,
    rule_table,
    run_study,
    score_under_rule,
    taxonomy_counts,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import ToolCall


def _call(name: str, **arguments: object) -> ToolCall:
    return ToolCall(name=name, arguments=dict(arguments))


_NO_DEFAULTS: dict[str, dict[str, object]] = {}


# ---------------------------------------------------------------------------
# parse_argument_defaults / build_registry_defaults
# ---------------------------------------------------------------------------


class TestParseArgumentDefaults:
    def test_empty_text_returns_empty_dict(self):
        assert parse_argument_defaults("") == {}
        assert parse_argument_defaults("   ") == {}

    def test_quoted_string_and_float(self):
        assert parse_argument_defaults("zone='Driver', temperature=20.0") == {
            "zone": "Driver",
            "temperature": 20.0,
        }

    def test_bool_and_int(self):
        assert parse_argument_defaults("enabled=True, level=5") == {"enabled": True, "level": 5}

    def test_json_style_null_is_none(self):
        assert parse_argument_defaults("enabled=True, pin=null") == {"enabled": True, "pin": None}

    def test_empty_dict_literal(self):
        assert parse_argument_defaults("deviceId='thermostat_1', schedule={}") == {
            "deviceId": "thermostat_1",
            "schedule": {},
        }

    def test_comma_inside_quotes_is_not_a_split_point(self):
        assert parse_argument_defaults("label='Wake, Up', repeat=null") == {
            "label": "Wake, Up",
            "repeat": None,
        }

    def test_unparseable_segment_is_skipped_not_fatal(self):
        # "weird" has no '=' at all and must be skipped without raising.
        assert parse_argument_defaults("temperature=20.0, weird") == {"temperature": 20.0}

    def test_build_registry_defaults_keys_by_tool_name(self):
        rows = [
            {"tool_name": "setZoneTemperature", "argument_defaults": "zone='Driver', temperature=20.0"},
            {"tool_name": "setFanSpeed", "argument_defaults": "level=5"},
            {"tool_name": "noDefaults", "argument_defaults": ""},
        ]
        defaults = build_registry_defaults(rows)
        assert defaults["setZoneTemperature"] == {"zone": "Driver", "temperature": 20.0}
        assert defaults["setFanSpeed"] == {"level": 5}
        assert defaults["noDefaults"] == {}


# ---------------------------------------------------------------------------
# classify_row -- one case per category, in priority order.
# ---------------------------------------------------------------------------


class TestClassifyRow:
    def test_parse_fail(self):
        gold = (_call("setLighting", state="On"),)
        result = classify_row(gold, (), parsed=False, defaults_by_tool=_NO_DEFAULTS)
        assert result.category == "PARSE_FAIL"
        assert result.n_gold_calls == 1
        assert result.n_pred_calls == 0

    def test_empty_prediction(self):
        gold = (_call("setLighting", state="On"),)
        result = classify_row(gold, (), parsed=True, defaults_by_tool=_NO_DEFAULTS)
        assert result.category == "EMPTY"

    def test_tool_set_wrong(self):
        gold = (_call("setLighting", state="On"),)
        predicted = (_call("setFanSpeed", level=5),)
        result = classify_row(gold, predicted, parsed=True, defaults_by_tool=_NO_DEFAULTS)
        assert result.category == "TOOL_SET_WRONG"

    def test_tool_order_only_when_multiset_matches_but_order_differs(self):
        gold = (_call("setLighting", state="On"), _call("setFanSpeed", level=5))
        predicted = (_call("setFanSpeed", level=5), _call("setLighting", state="On"))
        result = classify_row(gold, predicted, parsed=True, defaults_by_tool=_NO_DEFAULTS)
        assert result.category == "TOOL_ORDER_ONLY"

    def test_extra_keys_default_only(self):
        gold = (_call("setZoneTemperature", temperature=22.0),)
        predicted = (_call("setZoneTemperature", temperature=22.0, zone="Driver"),)
        defaults = {"setZoneTemperature": {"zone": "Driver", "temperature": 20.0}}
        result = classify_row(gold, predicted, parsed=True, defaults_by_tool=defaults)
        assert result.category == "EXTRA_KEYS_DEFAULT_ONLY"
        assert result.keys_extra == ("zone",)
        assert result.keys_missing == ()

    def test_extra_keys_nondefault(self):
        gold = (_call("setZoneTemperature", temperature=22.0),)
        predicted = (_call("setZoneTemperature", temperature=22.0, zone="Passenger"),)
        defaults = {"setZoneTemperature": {"zone": "Driver", "temperature": 20.0}}
        result = classify_row(gold, predicted, parsed=True, defaults_by_tool=defaults)
        assert result.category == "EXTRA_KEYS_NONDEFAULT"
        assert result.keys_extra == ("zone",)

    def test_missing_keys_only(self):
        gold = (_call("setZoneTemperature", temperature=22.0, zone="Driver"),)
        predicted = (_call("setZoneTemperature", temperature=22.0),)
        result = classify_row(gold, predicted, parsed=True, defaults_by_tool=_NO_DEFAULTS)
        assert result.category == "MISSING_KEYS_ONLY"
        assert result.keys_missing == ("zone",)
        assert result.keys_extra == ()

    def test_case_or_type_only_numeric_string(self):
        gold = (_call("setFanSpeed", level=5),)
        predicted = (_call("setFanSpeed", level="5"),)
        result = classify_row(gold, predicted, parsed=True, defaults_by_tool=_NO_DEFAULTS)
        assert result.category == "CASE_OR_TYPE_ONLY"

    def test_case_or_type_only_boolean_string(self):
        gold = (_call("setSteeringWheelHeat", enabled=True),)
        predicted = (_call("setSteeringWheelHeat", enabled="true"),)
        result = classify_row(gold, predicted, parsed=True, defaults_by_tool=_NO_DEFAULTS)
        assert result.category == "CASE_OR_TYPE_ONLY"

    def test_value_wrong(self):
        gold = (_call("setZoneTemperature", temperature=22.0),)
        predicted = (_call("setZoneTemperature", temperature=25.0),)
        result = classify_row(gold, predicted, parsed=True, defaults_by_tool=_NO_DEFAULTS)
        assert result.category == "VALUE_WRONG"

    def test_mixed_extra_and_missing(self):
        gold = (_call("setZoneTemperature", temperature=22.0, zone="Driver"),)
        predicted = (_call("setZoneTemperature", level="high"),)
        result = classify_row(gold, predicted, parsed=True, defaults_by_tool=_NO_DEFAULTS)
        assert result.category == "MIXED"

    def test_mixed_extra_plus_shared_value_wrong(self):
        gold = (_call("setZoneTemperature", temperature=22.0),)
        predicted = (_call("setZoneTemperature", temperature=25.0, zone="Passenger"),)
        result = classify_row(gold, predicted, parsed=True, defaults_by_tool=_NO_DEFAULTS)
        assert result.category == "MIXED"

    def test_already_exact_row_raises(self):
        gold = (_call("setLighting", state="On"),)
        with pytest.raises(ScorerV2StudyError):
            classify_row(gold, gold, parsed=True, defaults_by_tool=_NO_DEFAULTS)

    def test_tool_names_never_carry_values(self):
        gold = (_call("setLighting", state="On"),)
        predicted = (_call("setFanSpeed", level=5),)
        result = classify_row(gold, predicted, parsed=True, defaults_by_tool=_NO_DEFAULTS)
        assert result.tool_names == ("setFanSpeed", "setLighting")
        assert isinstance(result, RowClassification)


# ---------------------------------------------------------------------------
# score_under_rule -- V1 .. V2e over the same classify_row-style fixtures.
# ---------------------------------------------------------------------------


class TestScoreUnderRule:
    def test_unknown_rule_raises(self):
        gold = (_call("setLighting", state="On"),)
        with pytest.raises(ScorerV2StudyError):
            score_under_rule("V9", gold, gold, _NO_DEFAULTS)

    def test_v1_matches_exact_row(self):
        gold = (_call("setLighting", state="On"),)
        tool_acc, em = score_under_rule("V1", gold, gold, _NO_DEFAULTS)
        assert (tool_acc, em) == (1.0, 1.0)

    def test_v2a_ordered_tool_accuracy_flips_on_order_only_mismatch(self):
        gold = (_call("setLighting", state="On"), _call("setFanSpeed", level=5))
        predicted = (_call("setFanSpeed", level=5), _call("setLighting", state="On"))
        v1_tool_acc, v1_em = score_under_rule("V1", gold, predicted, _NO_DEFAULTS)
        v2a_tool_acc, v2a_em = score_under_rule("V2a", gold, predicted, _NO_DEFAULTS)
        assert v1_tool_acc == 1.0  # multiset match
        assert v2a_tool_acc == 0.0  # ordered sequence differs
        assert v1_em == v2a_em  # V2a does not change EM

    def test_v2b_default_extra_key_becomes_exact(self):
        gold = (_call("setZoneTemperature", temperature=22.0),)
        predicted = (_call("setZoneTemperature", temperature=22.0, zone="Driver"),)
        defaults = {"setZoneTemperature": {"zone": "Driver", "temperature": 20.0}}
        v1_tool_acc, v1_em = score_under_rule("V1", gold, predicted, defaults)
        v2b_tool_acc, v2b_em = score_under_rule("V2b", gold, predicted, defaults)
        assert v1_em == 0.0
        assert v2b_em == 1.0
        assert v1_tool_acc == v2b_tool_acc == 1.0  # tool accuracy never moves for b/c/d

    def test_v2b_nondefault_extra_key_stays_wrong(self):
        gold = (_call("setZoneTemperature", temperature=22.0),)
        predicted = (_call("setZoneTemperature", temperature=22.0, zone="Passenger"),)
        defaults = {"setZoneTemperature": {"zone": "Driver", "temperature": 20.0}}
        _, v2b_em = score_under_rule("V2b", gold, predicted, defaults)
        assert v2b_em == 0.0

    def test_v2c_forgives_any_extra_key_even_nondefault(self):
        gold = (_call("setZoneTemperature", temperature=22.0),)
        predicted = (_call("setZoneTemperature", temperature=22.0, zone="Passenger"),)
        defaults = {"setZoneTemperature": {"zone": "Driver", "temperature": 20.0}}
        _, v2b_em = score_under_rule("V2b", gold, predicted, defaults)
        _, v2c_em = score_under_rule("V2c", gold, predicted, defaults)
        assert v2b_em == 0.0
        assert v2c_em == 1.0  # lenient: any extra key absent from gold is dropped

    def test_v2d_type_coercion_fixes_numeric_string(self):
        gold = (_call("setFanSpeed", level=5),)
        predicted = (_call("setFanSpeed", level="5"),)
        _, v1_em = score_under_rule("V1", gold, predicted, _NO_DEFAULTS)
        _, v2d_em = score_under_rule("V2d", gold, predicted, _NO_DEFAULTS)
        assert v1_em == 0.0
        assert v2d_em == 1.0

    def test_v2d_type_coercion_fixes_boolean_string(self):
        gold = (_call("setSteeringWheelHeat", enabled=True),)
        predicted = (_call("setSteeringWheelHeat", enabled="true"),)
        _, v1_em = score_under_rule("V1", gold, predicted, _NO_DEFAULTS)
        _, v2d_em = score_under_rule("V2d", gold, predicted, _NO_DEFAULTS)
        assert v1_em == 0.0
        assert v2d_em == 1.0

    def test_v2d_does_not_fix_a_genuine_value_error(self):
        gold = (_call("setZoneTemperature", temperature=22.0),)
        predicted = (_call("setZoneTemperature", temperature=25.0),)
        _, v2d_em = score_under_rule("V2d", gold, predicted, _NO_DEFAULTS)
        assert v2d_em == 0.0

    def test_v2e_combines_order_default_and_coercion(self):
        gold = (_call("setZoneTemperature", temperature=22.0), _call("setFanSpeed", level=5))
        # order flipped, one default-valued extra key, one numeric-string value.
        predicted = (
            _call("setFanSpeed", level="5"),
            _call("setZoneTemperature", temperature=22.0, zone="Driver"),
        )
        defaults = {"setZoneTemperature": {"zone": "Driver"}}
        v1_tool_acc, v1_em = score_under_rule("V1", gold, predicted, defaults)
        v2e_tool_acc, v2e_em = score_under_rule("V2e", gold, predicted, defaults)
        assert v1_tool_acc == 1.0
        assert v2e_tool_acc == 0.0  # order still wrong under V2e's ordered tool accuracy
        assert v1_em == 0.0
        assert v2e_em == 1.0  # EM cured by default-key strip + type coercion

    def test_all_rules_agree_on_an_already_exact_row(self):
        gold = (_call("setLighting", state="On"),)
        for rule in ("V1", "V2a", "V2b", "V2c", "V2d", "V2e"):
            tool_acc, em = score_under_rule(rule, gold, gold, _NO_DEFAULTS)
            assert (tool_acc, em) == (1.0, 1.0), rule


# ---------------------------------------------------------------------------
# load_outputs_rows / aggregation helpers / taxonomy_counts / rule_table.
# ---------------------------------------------------------------------------


_GOLD_MAP = {
    "tier1_direct:000001": (_call("setLighting", state="On"),),
    "tier1_direct:000002": (_call("setZoneTemperature", temperature=22.0, zone="Driver"),),
    "tier2_parametric:000003": (_call("setFanSpeed", level=5),),
}


def _write_outputs(tmp_path, rows, filename="outputs.jsonl"):
    path = tmp_path / filename
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    return path


class TestLoadOutputsRows:
    def test_reads_text_field_and_pairs_gold(self, tmp_path):
        path = _write_outputs(
            tmp_path,
            [
                {"sample_id": "tier1_direct:000001", "text": json.dumps([{"name": "setLighting", "arguments": {"state": "On"}}])},
            ],
        )
        rows = load_outputs_rows(path, _GOLD_MAP, text_field="text")
        assert len(rows) == 1
        assert rows[0].sample_id == "tier1_direct:000001"
        assert rows[0].tier == "tier1_direct"
        assert rows[0].parsed is True

    def test_reads_response_text_field(self, tmp_path):
        path = _write_outputs(
            tmp_path,
            [
                {
                    "sample_id": "tier1_direct:000001",
                    "response_text": json.dumps([{"name": "setLighting", "arguments": {"state": "On"}}]),
                },
            ],
        )
        rows = load_outputs_rows(path, _GOLD_MAP, text_field="response_text")
        assert rows[0].parsed is True

    def test_missing_gold_raises(self, tmp_path):
        path = _write_outputs(tmp_path, [{"sample_id": "unknown:000099", "text": "[]"}])
        with pytest.raises(ScorerV2StudyError):
            load_outputs_rows(path, _GOLD_MAP, text_field="text")

    def test_duplicate_sample_id_raises(self, tmp_path):
        row = {"sample_id": "tier1_direct:000001", "text": "[]"}
        path = _write_outputs(tmp_path, [row, row])
        with pytest.raises(ScorerV2StudyError):
            load_outputs_rows(path, _GOLD_MAP, text_field="text")

    def test_missing_text_field_raises(self, tmp_path):
        path = _write_outputs(tmp_path, [{"sample_id": "tier1_direct:000001"}])
        with pytest.raises(ScorerV2StudyError):
            load_outputs_rows(path, _GOLD_MAP, text_field="text")


def _rows_for_taxonomy(tmp_path):
    rows = [
        {"sample_id": "tier1_direct:000001", "text": json.dumps([{"name": "setLighting", "arguments": {"state": "On"}}])},
        {
            "sample_id": "tier1_direct:000002",
            "text": json.dumps(
                [{"name": "setZoneTemperature", "arguments": {"temperature": 22.0, "zone": "Driver"}}]
            ),
        },
        {"sample_id": "tier2_parametric:000003", "text": "not json at all"},
    ]
    path = _write_outputs(tmp_path, rows)
    return load_outputs_rows(path, _GOLD_MAP, text_field="text")


class TestTaxonomyAndRuleTable:
    def test_taxonomy_counts_skips_exact_rows_and_counts_failures(self, tmp_path):
        rows = _rows_for_taxonomy(tmp_path)
        counts = taxonomy_counts(rows, _NO_DEFAULTS)
        # row 1 is exact -> not counted; row 3 (tier2) failed to parse.
        assert "tier1_direct" not in counts or "PARSE_FAIL" not in counts.get("tier1_direct", {})
        assert counts["tier2_parametric"]["PARSE_FAIL"] == 1

    def test_rule_table_has_every_rule_and_overall_scope(self, tmp_path):
        rows = _rows_for_taxonomy(tmp_path)
        table = rule_table(rows, _NO_DEFAULTS)
        assert set(table) == {"V1", "V2a", "V2b", "V2c", "V2d", "V2e"}
        assert table["V1"]["overall"]["n"] == 3
        assert table["V1"]["tier1_direct"]["n"] == 2
        assert table["V1"]["tier2_parametric"]["n"] == 1
        assert table["V1"]["tier2_parametric"]["exact_match"] == 0.0

    def test_per_tier_v1_matches_rule_table_v1(self, tmp_path):
        rows = _rows_for_taxonomy(tmp_path)
        per_tier = per_tier_v1(rows)
        table = rule_table(rows, _NO_DEFAULTS)
        assert per_tier["tier1_direct"]["exact_match"] == table["V1"]["tier1_direct"]["exact_match"]

    def test_build_per_row_entries_never_carries_argument_values(self, tmp_path):
        rows = _rows_for_taxonomy(tmp_path)
        entries = build_per_row_entries("unit", "arm0", rows, _NO_DEFAULTS)
        assert len(entries) == 3
        payload = json.dumps(entries)
        # the gold/predicted argument values used in these fixtures must never
        # leak into the per-row record -- only counts, categories, and names.
        assert "Driver" not in payload
        assert "22.0" not in payload
        exact_row = next(e for e in entries if e["sample_id"] == "tier1_direct:000001")
        assert exact_row["category"] == "EXACT_MATCH"


class TestIdentityCheck:
    def test_matching_target_reports_match_true(self, tmp_path):
        rows = _rows_for_taxonomy(tmp_path)
        overall = per_tier_v1(rows)
        agg = {
            "tool_accuracy": sum(v["tool_accuracy"] * v["n"] for v in overall.values()) / 3,
            "exact_match": sum(v["exact_match"] * v["n"] for v in overall.values()) / 3,
        }
        result = identity_check(rows, agg, {tier: vals for tier, vals in overall.items()})
        assert result["match"] is True
        assert result["mismatches"] == []

    def test_mismatched_target_is_reported(self, tmp_path):
        rows = _rows_for_taxonomy(tmp_path)
        result = identity_check(rows, {"tool_accuracy": 0.999, "exact_match": 0.999}, None)
        assert result["match"] is False
        assert len(result["mismatches"]) == 2


class TestPairedCounts:
    def test_save_harm_tie_counts(self, tmp_path):
        baseline_rows = load_outputs_rows(
            _write_outputs(
                tmp_path,
                [
                    {"sample_id": "tier1_direct:000001", "text": "[]"},  # baseline wrong (EMPTY)
                    {
                        "sample_id": "tier1_direct:000002",
                        "text": json.dumps(
                            [{"name": "setZoneTemperature", "arguments": {"temperature": 22.0, "zone": "Driver"}}]
                        ),
                    },  # baseline correct
                    {"sample_id": "tier2_parametric:000003", "text": json.dumps([{"name": "setFanSpeed", "arguments": {"level": 5}}])},  # baseline correct
                ],
                filename="baseline.jsonl",
            ),
            _GOLD_MAP,
            text_field="text",
        )
        treatment_rows = load_outputs_rows(
            _write_outputs(
                tmp_path,
                [
                    {
                        "sample_id": "tier1_direct:000001",
                        "text": json.dumps([{"name": "setLighting", "arguments": {"state": "On"}}]),
                    },  # treatment saves it
                    {"sample_id": "tier1_direct:000002", "text": "[]"},  # treatment harms it
                    {"sample_id": "tier2_parametric:000003", "text": json.dumps([{"name": "setFanSpeed", "arguments": {"level": 5}}])},  # tie (both correct)
                ],
                filename="treatment.jsonl",
            ),
            _GOLD_MAP,
            text_field="text",
        )
        baseline_by_id = {r.sample_id: r for r in baseline_rows}
        treatment_by_id = {r.sample_id: r for r in treatment_rows}
        counts = paired_counts(baseline_by_id, treatment_by_id, "V1", _NO_DEFAULTS)
        assert counts == {"n": 3, "saves": 1, "harms": 1, "ties": 1}


# ---------------------------------------------------------------------------
# run_study integration (synthetic files, synthetic gold, no data root).
# ---------------------------------------------------------------------------


class TestRunStudy:
    def test_single_source_no_baseline(self, tmp_path):
        path = _write_outputs(
            tmp_path,
            [
                {"sample_id": "tier1_direct:000001", "text": json.dumps([{"name": "setLighting", "arguments": {"state": "On"}}])},
                {"sample_id": "tier1_direct:000002", "text": "[]"},
            ],
        )
        source = SourceInput(
            source="synthetic",
            baseline_arm=None,
            arms=(
                ArmInput(
                    arm="only_arm",
                    outputs_path=path,
                    text_field="text",
                    target_overall={"tool_accuracy": 0.5, "exact_match": 0.5},
                    target_per_tier=None,
                ),
            ),
        )
        report = run_study(sources=[source], gold_by_sample_id=_GOLD_MAP, registry_rows=[])
        assert report["schema"] == "saea-a2t-scorer-v2-study-v1"
        arm_report = report["sources"]["synthetic"]["arms"]["only_arm"]
        assert arm_report["n_rows"] == 2
        assert arm_report["identity_check"]["match"] is True
        assert len(report["per_row"]) == 2
        assert report["residuals"] == []

    def test_baseline_arm_produces_paired_contrasts(self, tmp_path):
        baseline_path = _write_outputs(
            tmp_path,
            [{"sample_id": "tier1_direct:000001", "text": "[]"}],
            filename="baseline.jsonl",
        )
        treatment_path = _write_outputs(
            tmp_path,
            [
                {
                    "sample_id": "tier1_direct:000001",
                    "text": json.dumps([{"name": "setLighting", "arguments": {"state": "On"}}]),
                }
            ],
            filename="treatment.jsonl",
        )
        source = SourceInput(
            source="synthetic",
            baseline_arm="baseline",
            arms=(
                ArmInput(arm="baseline", outputs_path=baseline_path, text_field="text"),
                ArmInput(arm="treatment", outputs_path=treatment_path, text_field="text"),
            ),
        )
        report = run_study(sources=[source], gold_by_sample_id=_GOLD_MAP, registry_rows=[])
        paired = report["sources"]["synthetic"]["paired_vs_baseline"]["treatment"]
        assert paired["V1"] == {"n": 1, "saves": 1, "harms": 0, "ties": 0}
        assert paired["V2e"] == {"n": 1, "saves": 1, "harms": 0, "ties": 0}

    def test_missing_outputs_file_is_skipped_and_recorded(self, tmp_path):
        source = SourceInput(
            source="synthetic",
            baseline_arm=None,
            arms=(
                ArmInput(arm="missing_arm", outputs_path=tmp_path / "does-not-exist.jsonl", text_field="text"),
            ),
        )
        report = run_study(sources=[source], gold_by_sample_id=_GOLD_MAP, registry_rows=[])
        assert report["sources"]["synthetic"]["arms"]["missing_arm"]["skipped"] is True
        assert len(report["residuals"]) == 1
        assert "missing_arm" in report["residuals"][0]


# ---------------------------------------------------------------------------
# main() -- refuse-to-overwrite discipline (no data root needed: the check
# happens before any lock/data-root resolution).
# ---------------------------------------------------------------------------


class TestMainRefusesOverwrite:
    def test_refuses_when_summary_already_exists(self, tmp_path, capsys):
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        (output_dir / "summary.json").write_text("{}", encoding="utf-8")
        exit_code = study_main(["--output-dir", str(output_dir)])
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "REFUSED" in captured.err
        assert "already exists" in captured.err
