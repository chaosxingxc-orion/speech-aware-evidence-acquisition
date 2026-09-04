"""``analysis.a2t_v2_rescore``: Part D step 2 offline re-scoring of sealed
September Audio2Tool outputs under ``a2t-scorer-v2``.

Every case here is hand-authored and synthetic (no real Audio2Tool data, no
data root, no umbrella lock) -- this module never touches ``SPEECHRL_DATA_DIR``
or the committed sealed-summary JSON files; that real-data path is exercised
only by the actual one-shot ``run()``/``main()`` invocation, not by this test
suite.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_v2_rescore import (
    PAIRINGS,
    ArmResult,
    ArmSpec,
    RescoreError,
    _resolve_gold,
    locate_arms,
    main as rescore_main,
    paired_contrasts,
    rescore_arm,
    run,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import ToolCall


def _call(name: str, **arguments: object) -> ToolCall:
    return ToolCall(name=name, arguments=dict(arguments))


# score_item_v2 is fail-closed: every GOLD tool name must have an entry in
# registry_defaults (even an empty one) or it raises RegistryDriftError, so
# this cannot be a bare {} -- it must name every tool these fixtures use.
_NO_DEFAULTS: dict[str, dict[str, object]] = {
    "setLighting": {},
    "setZoneTemperature": {},
    "setFanSpeed": {},
}

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


def _spec(tmp_path, rows, *, source="unit", arm="only_arm", text_field="text", target_overall=None, filename="outputs.jsonl"):
    path = _write_outputs(tmp_path, rows, filename=filename)
    return ArmSpec(
        source=source,
        arm=arm,
        run_id=f"UNIT-{source}-{arm}",
        outputs_path=path,
        text_field=text_field,
        roster_receipt="synthetic",
        target_overall=target_overall,
        target_per_tier=None,
    )


# ---------------------------------------------------------------------------
# _resolve_gold -- standard map hit, tier-manifest fallback, and both misses.
# ---------------------------------------------------------------------------


class TestResolveGold:
    def test_standard_map_hit_short_circuits_fallback(self, tmp_path):
        # public_dir does not even exist -- if the fallback were consulted this would raise.
        result = _resolve_gold(
            "tier1_direct:000001", _GOLD_MAP, manifest_cache={}, public_dir=tmp_path / "does-not-exist"
        )
        assert result == _GOLD_MAP["tier1_direct:000001"]

    def test_tier_manifest_fallback_resolves_a_sample_id_outside_the_standard_map(self, tmp_path):
        public_dir = tmp_path / "public"
        manifest_dir = public_dir / "tier9_fresh_data"
        manifest_dir.mkdir(parents=True)
        entry = {
            "id": 42,
            "tier": "tier9_fresh",
            "tool_name": "setFanSpeed",
            "expected_tool_call": "setFanSpeed(level=5)",
            "extracted_params": {"level": "5"},
            "additional_tool_calls": None,
        }
        (manifest_dir / "tier9_fresh.json").write_text(json.dumps([entry]), encoding="utf-8")

        cache: dict = {}
        result = _resolve_gold("tier9_fresh:000042", {}, manifest_cache=cache, public_dir=public_dir)
        assert result == (_call("setFanSpeed", level=5),)
        # second lookup of the same tier must reuse the cache, not re-read the manifest.
        (manifest_dir / "tier9_fresh.json").unlink()
        result_again = _resolve_gold("tier9_fresh:000042", {}, manifest_cache=cache, public_dir=public_dir)
        assert result_again == (_call("setFanSpeed", level=5),)

    def test_unknown_sample_id_and_missing_manifest_return_none(self, tmp_path):
        assert _resolve_gold("nope:000001", {}, manifest_cache={}, public_dir=tmp_path) is None
        assert _resolve_gold("malformed-no-colon", {}, manifest_cache={}, public_dir=tmp_path) is None

    def test_manifest_present_but_id_absent_returns_none(self, tmp_path):
        public_dir = tmp_path / "public"
        manifest_dir = public_dir / "tier9_fresh_data"
        manifest_dir.mkdir(parents=True)
        entry = {
            "id": 1,
            "tier": "tier9_fresh",
            "tool_name": "setFanSpeed",
            "expected_tool_call": "setFanSpeed(level=5)",
            "extracted_params": {},
            "additional_tool_calls": None,
        }
        (manifest_dir / "tier9_fresh.json").write_text(json.dumps([entry]), encoding="utf-8")
        result = _resolve_gold("tier9_fresh:000099", {}, manifest_cache={}, public_dir=public_dir)
        assert result is None


# ---------------------------------------------------------------------------
# rescore_arm -- v1/v2 scoring, identity check, skip logic.
# ---------------------------------------------------------------------------


class TestRescoreArm:
    def _run(self, spec, **kwargs):
        return rescore_arm(
            spec,
            lock={},
            root=None,
            standard_gold=kwargs.pop("standard_gold", _GOLD_MAP),
            registry_defaults=kwargs.pop("registry_defaults", _NO_DEFAULTS),
            manifest_cache=kwargs.pop("manifest_cache", {}),
            public_dir=kwargs.pop("public_dir", None),
        )

    def test_v1_and_v2_exact_computed_and_identity_matches(self, tmp_path):
        rows = [
            {
                "sample_id": "tier1_direct:000001",
                "text": json.dumps([{"name": "setLighting", "arguments": {"state": "On"}}]),
            },
            {"sample_id": "tier1_direct:000002", "text": "[]"},
        ]
        spec = _spec(tmp_path, rows, target_overall={"tool_accuracy": 0.5, "exact_match": 0.5})
        result = self._run(spec)
        assert result.skipped is False
        assert result.n_rows == 2
        assert result.identity["match"] is True
        assert result.v1_overall["exact_match"] == pytest.approx(0.5)
        assert result.v2_overall["exact_match"] == pytest.approx(0.5)
        assert set(result.per_sample) == {"tier1_direct:000001", "tier1_direct:000002"}
        assert len(result.per_row) == 2

    def test_v2_extra_default_key_becomes_exact_while_v1_stays_wrong(self, tmp_path):
        rows = [
            {
                "sample_id": "tier1_direct:000002",
                "text": json.dumps(
                    [{"name": "setZoneTemperature", "arguments": {"temperature": 22.0, "zone": "Driver"}}]
                ),
            }
        ]
        # gold omits "zone"; registry says "zone" defaults to "Driver" for this tool.
        gold = {"tier1_direct:000002": (_call("setZoneTemperature", temperature=22.0),)}
        registry_rows = [{"tool_name": "setZoneTemperature", "argument_defaults": "zone='Driver'"}]
        from speech_aware_evidence_acquisition.reproduction.toolcall_scoring_v2 import build_registry_defaults

        spec = _spec(tmp_path, rows)
        result = self._run(spec, standard_gold=gold, registry_defaults=build_registry_defaults(registry_rows))
        assert result.skipped is False
        assert result.v1_overall["exact_match"] == 0.0
        assert result.v2_overall["exact_match"] == 1.0

    def test_text_field_remapping_response_text(self, tmp_path):
        rows = [
            {
                "sample_id": "tier1_direct:000001",
                "response_text": json.dumps([{"name": "setLighting", "arguments": {"state": "On"}}]),
            }
        ]
        spec = _spec(tmp_path, rows, text_field="response_text")
        result = self._run(spec)
        assert result.skipped is False
        assert result.per_row[0]["v1_exact"] == 1.0

    def test_text_field_remapping_final_response_text(self, tmp_path):
        rows = [
            {
                "sample_id": "tier1_direct:000001",
                "final_response_text": json.dumps([{"name": "setLighting", "arguments": {"state": "On"}}]),
            }
        ]
        spec = _spec(tmp_path, rows, text_field="final_response_text")
        result = self._run(spec)
        assert result.skipped is False
        assert result.per_row[0]["v1_exact"] == 1.0

    def test_missing_outputs_file_is_skipped(self, tmp_path):
        spec = ArmSpec(
            source="unit",
            arm="missing",
            run_id="UNIT",
            outputs_path=tmp_path / "does-not-exist.jsonl",
            text_field="text",
            roster_receipt="synthetic",
        )
        result = self._run(spec)
        assert result.skipped is True
        assert "cannot read outputs" in result.skip_reason

    def test_missing_text_field_is_skipped(self, tmp_path):
        rows = [{"sample_id": "tier1_direct:000001"}]
        spec = _spec(tmp_path, rows)
        result = self._run(spec)
        assert result.skipped is True
        assert "text" in result.skip_reason

    def test_duplicate_sample_id_is_skipped(self, tmp_path):
        row = {"sample_id": "tier1_direct:000001", "text": "[]"}
        spec = _spec(tmp_path, [row, row])
        result = self._run(spec)
        assert result.skipped is True
        assert "duplicate" in result.skip_reason

    def test_unresolvable_gold_is_skipped(self, tmp_path):
        rows = [{"sample_id": "unknown:000099", "text": "[]"}]
        spec = _spec(tmp_path, rows)
        result = self._run(spec)
        assert result.skipped is True
        assert "no gold resolvable" in result.skip_reason

    def test_identity_mismatch_is_skipped(self, tmp_path):
        rows = [
            {
                "sample_id": "tier1_direct:000001",
                "text": json.dumps([{"name": "setLighting", "arguments": {"state": "On"}}]),
            }
        ]
        spec = _spec(tmp_path, rows, target_overall={"tool_accuracy": 0.0, "exact_match": 0.0})
        result = self._run(spec)
        assert result.skipped is True
        assert "identity mismatch" in result.skip_reason

    def test_malformed_json_line_is_skipped(self, tmp_path):
        path = tmp_path / "outputs.jsonl"
        path.write_text("not json\n", encoding="utf-8")
        spec = ArmSpec(
            source="unit", arm="bad", run_id="UNIT", outputs_path=path,
            text_field="text", roster_receipt="synthetic",
        )
        result = self._run(spec)
        assert result.skipped is True
        assert "malformed" in result.skip_reason


# ---------------------------------------------------------------------------
# locate_arms -- shape and a couple of spot checks.
# ---------------------------------------------------------------------------


class TestLocateArms:
    def test_every_spec_has_the_documented_fields(self, tmp_path):
        specs = locate_arms(tmp_path)
        assert specs, "locate_arms must return at least one ArmSpec"
        for spec in specs:
            assert isinstance(spec, ArmSpec)
            assert spec.run_id
            assert spec.arm
            assert spec.source
            assert spec.text_field
            assert spec.roster_receipt
            assert str(spec.outputs_path).startswith(str(tmp_path))
            assert spec.target_overall is not None
            assert 0.0 <= spec.target_overall["tool_accuracy"] <= 1.0
            assert 0.0 <= spec.target_overall["exact_match"] <= 1.0

    def test_a0_carries_per_tier_targets_and_eight_tiers(self, tmp_path):
        specs = {(s.source, s.arm): s for s in locate_arms(tmp_path)}
        a0 = specs[("a0", "zero_supply")]
        assert a0.target_per_tier is not None
        assert len(a0.target_per_tier) == 8

    def test_source_arm_pairs_are_unique(self, tmp_path):
        specs = locate_arms(tmp_path)
        keys = [(s.source, s.arm) for s in specs]
        assert len(keys) == len(set(keys))

    def test_every_pairing_arm_is_actually_located(self, tmp_path):
        located = {(s.source, s.arm) for s in locate_arms(tmp_path)}
        for baseline_source, baseline_arm, treat_source, treat_arm in PAIRINGS:
            assert (baseline_source, baseline_arm) in located
            assert (treat_source, treat_arm) in located


# ---------------------------------------------------------------------------
# paired_contrasts -- synthetic ArmResult fixtures, no rescore_arm involved.
# ---------------------------------------------------------------------------


def _result(source, arm, per_sample, *, skipped=False, skip_reason=None):
    return ArmResult(
        source=source,
        arm=arm,
        run_id=f"UNIT-{source}",
        outputs_path="unit-test",
        text_field="text",
        skipped=skipped,
        skip_reason=skip_reason,
        n_rows=len(per_sample),
        identity={"checked": True, "match": True, "mismatches": []},
        v1_overall={},
        v2_overall={},
        v1_per_tier={},
        v2_per_tier={},
        per_sample=per_sample,
        per_row=(),
    )


_METRIC_ROW_BASELINE_WRONG = {
    "v1_exact": 0.0, "v1_tool": 0.0, "v2_exact": 0.0, "v2_tool_ordered": 0.0, "v2_tool_multiset": 0.0,
}
_METRIC_ROW_TREATMENT_RIGHT = {
    "v1_exact": 1.0, "v1_tool": 1.0, "v2_exact": 1.0, "v2_tool_ordered": 1.0, "v2_tool_multiset": 1.0,
}


class TestPairedContrasts:
    def test_known_pairing_produces_a_contrast(self):
        baseline = _result(
            "semantic104", "direct_m0",
            {"tier1_direct:000001": _METRIC_ROW_BASELINE_WRONG, "tier2_parametric:000002": _METRIC_ROW_TREATMENT_RIGHT},
        )
        treatment = _result(
            "semantic104", "transcript_top16_use",
            {"tier1_direct:000001": _METRIC_ROW_TREATMENT_RIGHT, "tier2_parametric:000002": _METRIC_ROW_TREATMENT_RIGHT},
        )
        out = paired_contrasts([baseline, treatment], n_replicates=200)
        key = "semantic104/transcript_top16_use_vs_semantic104/direct_m0"
        assert key in out
        assert out[key]["skipped"] is False
        contrast = out[key]["contrasts"]["v1_exact"]
        assert contrast.n == 2
        assert contrast.saves == 1
        assert contrast.harms == 0

    def test_missing_arm_is_skipped_with_reason(self):
        baseline = _result("semantic104", "direct_m0", {"tier1_direct:000001": _METRIC_ROW_BASELINE_WRONG})
        out = paired_contrasts([baseline], n_replicates=200)
        key = "semantic104/transcript_top16_use_vs_semantic104/direct_m0"
        assert out[key]["skipped"] is True
        assert "never scored" in out[key]["reason"]

    def test_skipped_baseline_propagates_as_skip(self):
        baseline = _result(
            "semantic104", "direct_m0", {}, skipped=True, skip_reason="identity mismatch"
        )
        treatment = _result(
            "semantic104", "transcript_top16_use", {"tier1_direct:000001": _METRIC_ROW_TREATMENT_RIGHT}
        )
        out = paired_contrasts([baseline, treatment], n_replicates=200)
        key = "semantic104/transcript_top16_use_vs_semantic104/direct_m0"
        assert out[key]["skipped"] is True
        assert "baseline skipped" in out[key]["reason"]

    def test_treatment_ids_not_in_baseline_are_skipped(self):
        baseline = _result("semantic104", "direct_m0", {"tier1_direct:000001": _METRIC_ROW_BASELINE_WRONG})
        treatment = _result(
            "semantic104", "transcript_top16_use", {"tier9_other:000009": _METRIC_ROW_TREATMENT_RIGHT}
        )
        out = paired_contrasts([baseline, treatment], n_replicates=200)
        key = "semantic104/transcript_top16_use_vs_semantic104/direct_m0"
        assert out[key]["skipped"] is True
        assert "absent from baseline" in out[key]["reason"]

    def test_cross_source_baseline_pairing_g5_vs_shared_m0(self):
        baseline = _result(
            "g1_m0_shared", "M0",
            {
                "tier1_direct:000074": _METRIC_ROW_BASELINE_WRONG,
                "tier1_direct:000077": _METRIC_ROW_TREATMENT_RIGHT,
                # extra id not used by g5 -- must not break the subset pairing.
                "tier1_direct:999999": _METRIC_ROW_BASELINE_WRONG,
            },
        )
        treatment = _result(
            "g5", "g5",
            {"tier1_direct:000074": _METRIC_ROW_TREATMENT_RIGHT, "tier1_direct:000077": _METRIC_ROW_TREATMENT_RIGHT},
        )
        out = paired_contrasts([baseline, treatment], n_replicates=200)
        key = "g5/g5_vs_g1_m0_shared/M0"
        assert out[key]["skipped"] is False
        assert out[key]["contrasts"]["v1_exact"].n == 2


# ---------------------------------------------------------------------------
# run() -- refuse-overwrite discipline (no real data root needed: the check
# happens before any lock/data-root resolution).
# ---------------------------------------------------------------------------


class TestRunRefusesOverwrite:
    def test_refuses_when_summary_already_exists(self, tmp_path):
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        (output_dir / "summary.json").write_text("{}", encoding="utf-8")
        with pytest.raises(RescoreError, match="already exists"):
            run(output_dir=output_dir)


class TestMainRefusesOverwrite:
    def test_refuses_when_summary_already_exists(self, tmp_path, capsys):
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        (output_dir / "summary.json").write_text("{}", encoding="utf-8")
        exit_code = rescore_main(["--output-dir", str(output_dir)])
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "REFUSED" in captured.err
        assert "already exists" in captured.err
