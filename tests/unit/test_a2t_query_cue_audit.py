"""MF-1, the Audio2Tool query-cue audit: text reduction, the block-grouped
separability ceiling, the two cue-coverage statistics, the preregistered
decision, pair discovery from a miss table, and disjoint target assembly.

Every test is MODEL-FREE, network-free and filesystem-free: the corpus is a
synthetic construction pool built in-process and the registry is a synthetic
``tools_registry.csv`` row map, so nothing here opens a socket, a manifest or
a run directory.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_query_cue_audit import (
    DOMAIN_CUE_WORDS,
    INSUFFICIENT_DATA,
    LABEL_NOISE,
    TARGET,
    UNCERTAIN,
    PairSpec,
    QueryRow,
    _assert_disjoint,
    assemble_pairs,
    audit_pair,
    audit_population,
    build_targets,
    camel_split,
    class_mass,
    content_tokens,
    decide,
    description_cue,
    discovered_pairs,
    domain_cue,
    fold_of_block,
    lighting_family,
    pair_directions,
    separability,
    signature_argument_names,
    tokenize,
    tool_description_tokens,
)


def _tool(name, domain, category, signature, description):
    return {
        "tool_name": name,
        "domain": domain,
        "category": category,
        "signature": signature,
        "description": description,
    }


REGISTRY = {
    "setLighting": _tool(
        "setLighting",
        "smart_home",
        "core_control",
        "setLighting(deviceId: String, state: OnOff, level: Int?)",
        "Controls the power and brightness of a light.",
    ),
    "setAmbientLighting": _tool(
        "setAmbientLighting",
        "smart_car",
        "media_cabin",
        "setAmbientLighting(color: HexCode, brightness: Int)",
        "Sets the interior ambient lighting of the cabin.",
    ),
    "setBrightness": _tool(
        "setBrightness",
        "smart_home",
        "lighting",
        "setBrightness(deviceId: String, level: Int)",
        "Sets the brightness level for a dimmable light.",
    ),
    "startWorkout": _tool(
        "startWorkout",
        "wearables",
        "health_activity",
        "startWorkout(kind: String)",
        "Begins a tracked workout session.",
    ),
    "getHRV": _tool(
        "getHRV",
        "wearables",
        "health_activity",
        "getHRV(period: TimeFrame)",
        "Retrieves heart rate variability for a period.",
    ),
}


def _rows(tool, texts, first_block):
    return [QueryRow(tool, first_block + index, text) for index, text in enumerate(texts)]


HOME_TEXTS = [
    f"turn on the kitchen light number {index} in the house" for index in range(20)
]
CAR_TEXTS = [f"set the cabin ambient lighting of my car to blue {index}" for index in range(20)]


class TestTextReduction:
    def test_tokenize_is_lowercase_alphanumeric(self):
        assert tokenize("Turn ON the Light, please!") == (
            "turn",
            "on",
            "the",
            "light",
            "please",
        )

    def test_content_tokens_drop_function_words_but_keep_on_and_off(self):
        tokens = content_tokens("please turn the light on and off for me")
        assert "on" in tokens and "off" in tokens
        assert "the" not in tokens and "please" not in tokens

    def test_camel_split_handles_underscore_suffixes(self):
        assert camel_split("setColorTemperature") == ("set", "color", "temperature")
        assert camel_split("controlPlayback_home") == ("control", "playback", "home")
        assert camel_split("getAirQuality_diag") == ("get", "air", "quality", "diag")

    def test_signature_argument_names_drops_types_and_nested_generics(self):
        assert signature_argument_names(
            "startCleaning(deviceId: String, zones: List<String, Int>?)"
        ) == ("deviceId", "zones")
        assert signature_argument_names("runNetworkSpeedTest()") == ()
        assert signature_argument_names("not a signature") == ()

    def test_description_tokens_drop_type_noise(self):
        tokens = tool_description_tokens(REGISTRY["setBrightness"])
        assert "brightness" in tokens and "dimmable" in tokens
        assert "string" not in tokens and "int" not in tokens

    def test_lighting_family_is_derived_not_asserted(self):
        family = lighting_family(REGISTRY)
        assert family == frozenset({"setLighting", "setAmbientLighting", "setBrightness"})

    def test_domain_cue_lists_are_disjoint(self):
        _assert_disjoint(DOMAIN_CUE_WORDS)
        with pytest.raises(ValueError, match="appears in both"):
            _assert_disjoint(
                {"a": frozenset({"shared"}), "b": frozenset({"shared"})}
            )


class TestSeparability:
    def test_perfectly_separable_pool_reaches_one(self):
        left = _rows("setLighting", HOME_TEXTS, 1000)
        right = _rows("setAmbientLighting", CAR_TEXTS, 2000)
        result = separability(left, right)
        assert result.accuracy == pytest.approx(1.0)
        assert result.balanced_accuracy == pytest.approx(1.0)
        assert result.folds_used == 5
        assert result.scored_left + result.scored_right == 40

    def test_identical_pools_are_label_noise(self):
        shared = [f"do the thing number {index}" for index in range(24)]
        left = _rows("setLighting", shared, 1000)
        right = _rows("setBrightness", shared, 2000)
        result = separability(left, right)
        assert result.accuracy < 0.65

    def test_folds_are_grouped_by_block(self):
        assert fold_of_block(4242) == fold_of_block(4242)
        assigned = {fold_of_block(block) for block in range(200)}
        assert assigned == {0, 1, 2, 3, 4}

    def test_imbalance_flag_fires_when_accuracy_cannot_beat_the_majority(self):
        shared = [f"do the thing number {index}" for index in range(40)]
        left = _rows("setLighting", shared, 1000)
        right = _rows("setBrightness", shared[:5], 2000)
        result = separability(left, right)
        assert result.imbalance_flag is True

    def test_log_odds_lists_are_capped_and_ordered(self):
        left = _rows("setLighting", HOME_TEXTS, 1000)
        right = _rows("setAmbientLighting", CAR_TEXTS, 2000)
        result = separability(left, right)
        assert len(result.top_tokens_left) <= 15
        values = [value for _token, value in result.top_tokens_left]
        assert values == sorted(values, reverse=True)
        assert result.top_tokens_left[0][1] > 0 > result.top_tokens_right[0][1]

    def test_empty_input_raises(self):
        with pytest.raises(ValueError):
            separability([], [])


class TestCueCoverage:
    def test_description_gap_is_the_mean_of_the_two_sides(self):
        left = _rows("setLighting", ["turn on the light"] * 4, 1000)
        right = _rows("startWorkout", ["begin my workout"] * 4, 2000)
        result = description_cue(
            left,
            right,
            tool_description_tokens(REGISTRY["setLighting"]),
            tool_description_tokens(REGISTRY["startWorkout"]),
        )
        assert result["own_share_left"] == 1.0
        assert result["twin_share_left"] == 0.0
        assert result["gap_points"] == pytest.approx(100.0)
        assert result["gap_points_min_side"] == pytest.approx(100.0)

    def test_shared_description_tokens_cancel_in_the_gap(self):
        left = _rows("setLighting", ["adjust the light"] * 4, 1000)
        right = _rows("setBrightness", ["adjust the light"] * 4, 2000)
        result = description_cue(
            left,
            right,
            tool_description_tokens(REGISTRY["setLighting"]),
            tool_description_tokens(REGISTRY["setBrightness"]),
        )
        assert result["gap_points"] == pytest.approx(0.0)
        assert "light" in result["shared_tokens"]

    def test_domain_cue_is_not_applicable_within_one_domain(self):
        rows = _rows("setLighting", ["turn on the light"] * 3, 1000)
        assert domain_cue(rows, rows, "smart_home", "smart_home")["applicable"] is False

    def test_domain_cue_counts_only_its_own_domain_words(self):
        left = _rows("setLighting", HOME_TEXTS, 1000)
        right = _rows("setAmbientLighting", CAR_TEXTS, 2000)
        result = domain_cue(left, right, "smart_home", "smart_car")
        assert result["coverage_left"] == pytest.approx(1.0)
        assert result["coverage_right"] == pytest.approx(1.0)
        assert result["coverage"] == pytest.approx(1.0)


class TestDecision:
    BASE = dict(
        units_left=40,
        units_right=40,
        blocks_left=40,
        blocks_right=40,
        cross_domain=False,
        domain_coverage=None,
    )

    def test_target_needs_both_clauses(self):
        assert decide(**self.BASE, accuracy=0.9, description_gap_points=25.0) == TARGET
        assert decide(**self.BASE, accuracy=0.9, description_gap_points=5.0) == UNCERTAIN

    def test_label_noise_below_the_floor(self):
        assert decide(**self.BASE, accuracy=0.6, description_gap_points=90.0) == LABEL_NOISE

    def test_domain_only_needs_a_cross_domain_pair(self):
        cross = dict(self.BASE)
        cross.update(cross_domain=True, domain_coverage=0.7)
        assert decide(**cross, accuracy=0.9, description_gap_points=5.0) == "DOMAIN-ONLY"
        cross.update(domain_coverage=0.4)
        assert decide(**cross, accuracy=0.9, description_gap_points=5.0) == UNCERTAIN

    def test_insufficient_data_outranks_every_verdict(self):
        thin = dict(self.BASE)
        thin.update(units_right=3)
        assert (
            decide(**thin, accuracy=1.0, description_gap_points=99.0) == INSUFFICIENT_DATA
        )
        thin = dict(self.BASE)
        thin.update(blocks_left=2)
        assert (
            decide(**thin, accuracy=1.0, description_gap_points=99.0) == INSUFFICIENT_DATA
        )


class TestPairAssembly:
    MISSES = {
        ("setLighting", "setAmbientLighting"): 30,
        ("setAmbientLighting", "setLighting"): 4,
        ("setBrightness", "setLighting"): 6,
        ("startWorkout", "getHRV"): 2,
        ("setLighting", "notATool"): 12,
        ("setLighting", ""): 9,
    }

    def test_discovery_needs_the_threshold_and_a_registry_valid_name(self):
        found = discovered_pairs(self.MISSES, REGISTRY, minimum=5)
        assert found == (
            ("setAmbientLighting", "setLighting"),
            ("setBrightness", "setLighting"),
        )
        assert discovered_pairs(self.MISSES, REGISTRY, minimum=40) == ()

    def test_named_pairs_come_first_and_deduplicate_discovered_ones(self):
        specs = assemble_pairs(self.MISSES, REGISTRY, minimum=5)
        assert specs[0].origin == "named"
        ids = [spec.pair_id for spec in specs]
        assert len(ids) == len(set(ids))
        assert "setBrightness|setLighting" in ids

    def test_audit_pair_refuses_an_unregistered_tool(self):
        spec = PairSpec("x|y", ("setLighting",), ("notATool",), "named")
        with pytest.raises(ValueError, match="not in tools_registry"):
            audit_pair(spec, {}, REGISTRY, {})

    def test_audit_pair_reports_both_directions_and_refuses_a_thin_side(self):
        rows = {
            "setLighting": _rows("setLighting", HOME_TEXTS, 1000),
            "setAmbientLighting": _rows("setAmbientLighting", CAR_TEXTS[:3], 2000),
        }
        spec = PairSpec(
            "setAmbientLighting|setLighting",
            ("setAmbientLighting",),
            ("setLighting",),
            "named",
        )
        row = audit_pair(spec, rows, REGISTRY, self.MISSES)
        assert row["decision"] == INSUFFICIENT_DATA
        assert row["separability"] is None
        assert row["sealed_misses_left_to_right"] == 4
        assert row["sealed_misses_right_to_left"] == 30
        assert row["sealed_miss_mass"] == 34
        assert row["class"] == "cross_domain"


class TestTargets:
    def test_cluster_and_individual_pairs_do_not_double_count(self):
        misses = {("setLighting", "setAmbientLighting"): 30}
        cluster = {
            "pair_id": "setBrightness+setLighting|setAmbientLighting",
            "decision": TARGET,
            "left_tools": ["setBrightness", "setLighting"],
            "right_tools": ["setAmbientLighting"],
            "sealed_miss_mass": 30,
        }
        single = {
            "pair_id": "setAmbientLighting|setLighting",
            "decision": TARGET,
            "left_tools": ["setAmbientLighting"],
            "right_tools": ["setLighting"],
            "sealed_miss_mass": 30,
        }
        assert pair_directions(single) == {
            ("setAmbientLighting", "setLighting"),
            ("setLighting", "setAmbientLighting"),
        }
        result = build_targets(
            [cluster, single], misses, lighting_family(REGISTRY), maximum=12
        )
        assert result["strict_mass_total"] == 30
        assert class_mass([cluster, single], TARGET, misses) == 30

    def test_lighting_family_becomes_one_target_and_targets_stay_disjoint(self):
        misses = {
            ("setLighting", "setAmbientLighting"): 10,
            ("setBrightness", "setLighting"): 6,
            ("startWorkout", "getHRV"): 7,
        }
        audited = [
            {
                "pair_id": "setAmbientLighting|setLighting",
                "decision": TARGET,
                "left_tools": ["setAmbientLighting"],
                "right_tools": ["setLighting"],
                "sealed_miss_mass": 10,
            },
            {
                "pair_id": "setBrightness|setLighting",
                "decision": TARGET,
                "left_tools": ["setBrightness"],
                "right_tools": ["setLighting"],
                "sealed_miss_mass": 6,
            },
            {
                "pair_id": "getHRV|startWorkout",
                "decision": TARGET,
                "left_tools": ["getHRV"],
                "right_tools": ["startWorkout"],
                "sealed_miss_mass": 7,
            },
        ]
        result = build_targets(audited, misses, lighting_family(REGISTRY))
        ids = [row["target_id"] for row in result["targets"]]
        assert "lighting" in ids
        seen = [tool for row in result["targets"] for tool in row["tools"]]
        assert len(seen) == len(set(seen))
        lighting_row = next(row for row in result["targets"] if row["target_id"] == "lighting")
        assert set(lighting_row["tools"]) == {
            "setAmbientLighting",
            "setBrightness",
            "setLighting",
        }
        assert result["strict_mass_total"] == 23

    def test_the_cap_drops_the_smallest_targets(self):
        misses = {
            ("setLighting", "setAmbientLighting"): 10,
            ("startWorkout", "getHRV"): 1,
        }
        audited = [
            {
                "pair_id": "setAmbientLighting|setLighting",
                "decision": TARGET,
                "left_tools": ["setAmbientLighting"],
                "right_tools": ["setLighting"],
                "sealed_miss_mass": 10,
            },
            {
                "pair_id": "getHRV|startWorkout",
                "decision": TARGET,
                "left_tools": ["getHRV"],
                "right_tools": ["startWorkout"],
                "sealed_miss_mass": 1,
            },
        ]
        result = build_targets(audited, misses, lighting_family(REGISTRY), maximum=1)
        assert len(result["targets"]) == 1
        assert result["targets"][0]["target_id"] == "lighting"
        assert len(result["dropped_over_cap"]) == 1


class TestPopulationRun:
    def test_end_to_end_on_a_synthetic_pool(self):
        rows = (
            _rows("setLighting", HOME_TEXTS, 1000)
            + _rows("setAmbientLighting", CAR_TEXTS, 2000)
            + _rows("startWorkout", [f"start my workout {i}" for i in range(20)], 3000)
            + _rows("getHRV", [f"show my hrv for today {i}" for i in range(20)], 4000)
        )
        misses = {
            ("setLighting", "setAmbientLighting"): 30,
            ("startWorkout", "getHRV"): 9,
        }
        specs = (
            PairSpec(
                "setAmbientLighting|setLighting",
                ("setAmbientLighting",),
                ("setLighting",),
                "named",
            ),
            PairSpec("getHRV|startWorkout", ("getHRV",), ("startWorkout",), "named"),
        )
        result = audit_population(rows, REGISTRY, misses, specs)
        assert result["construction_units"] == 80
        assert result["construction_blocks"] == 80
        assert result["pair_count"] == 2
        assert result["decision_counts"] == {TARGET: 2}
        assert result["mass_by_decision"][TARGET] == 39
        assert result["targets"]["strict_mass_total"] == 39
        assert result["sealed_miss_total"] == 39
        by_id = {row["pair_id"]: row for row in result["pairs"]}
        assert by_id["setAmbientLighting|setLighting"]["separability"]["accuracy"] == 1.0
