"""Synthetic optional contrasts preserve pooled counts, paired draws and custody."""

import copy
import math
from collections import Counter

import pytest

from speech_aware_evidence_acquisition.analysis import system_text_update as shared
from speech_aware_evidence_acquisition.analysis import (
    system_architecture_read as manual,
)
from speech_aware_evidence_acquisition.analysis.null_calibration import pooled_f1
from speech_aware_evidence_acquisition.analysis.bootstrap import _percentile
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError,
    canonical,
)

LABELS = ["control", "control-aa", "solver-import", "reviewer-import", "joint-import"]
GROUPS = {"architecture": (LABELS[0], LABELS[1], LABELS[2:])}


def declaration():
    return {
        "schema": "saea-additional-pooled-contrasts-v1",
        "comparison_group": "architecture",
        "metric": "slu_f1",
        "contrasts": [
            {
                "id": "joint-minus-solver",
                "coefficients": {"joint-import": 1, "solver-import": -1},
            },
            {
                "id": "joint-minus-reviewer",
                "coefficients": {"joint-import": 1, "reviewer-import": -1},
            },
            {
                "id": "joint-interaction",
                "coefficients": {
                    "joint-import": 1,
                    "solver-import": -1,
                    "reviewer-import": -1,
                    "control": 1,
                },
            },
        ],
    }


def cohort(*, zero=False, identical=False):
    ids = [f"slurp:train:{i:06d}" for i in range(6)]
    # Cluster sizes 1, 2, 3 and highly unequal count volume.
    roster = {
        sid: {
            "sample_id": sid,
            "utterance_id": str((0, 1, 1, 2, 2, 2)[i]),
            "stratum": "a" if i < 3 else "b",
        }
        for i, sid in enumerate(ids)
    }
    triples = {
        "control": [(8, 2, 2), (0, 1, 1), (1, 1, 1), (2, 0, 0), (0, 0, 0), (0, 2, 2)],
        "control-aa": [
            (8, 2, 2),
            (0, 1, 1),
            (1, 1, 1),
            (2, 0, 0),
            (0, 0, 0),
            (0, 2, 2),
        ],
        "solver-import": [
            (9, 1, 1),
            (1, 0, 0),
            (1, 1, 1),
            (0, 2, 2),
            (0, 0, 0),
            (1, 1, 1),
        ],
        "reviewer-import": [
            (10, 0, 0),
            (0, 1, 1),
            (0, 2, 2),
            (1, 1, 1),
            (0, 0, 0),
            (2, 0, 0),
        ],
        "joint-import": [
            (7, 3, 3),
            (1, 0, 0),
            (2, 0, 0),
            (2, 0, 0),
            (0, 0, 0),
            (3, 0, 0),
        ],
    }
    counts = {}
    for label in LABELS:
        rows = [(0, 0, 0)] * 6 if zero else triples["control" if identical else label]
        counts[label] = {
            sid: {
                **{
                    f"slu_f1_{axis}_{kind}": v
                    for axis in ("word", "char")
                    for kind, v in zip(("tp", "fp", "fn"), triple)
                },
                "scenario_action_exact": 1,
            }
            for sid, triple in zip(ids, rows)
        }
    execution = {
        "model_calls": 1,
        "tool_calls": 0,
        "prompt_tokens": None,
        "completion_tokens": None,
        "delivery_kind": "accepted",
        "reliable_completion": True,
        "abstained": False,
    }
    summaries = {
        label: {
            "slu_f1": pooled_f1(rows, ids, shared.FIELDS),
            "intent": 1.0,
            "model_calls": 6,
            "tool_calls": 0,
            "reliable_completion_rate": 1.0,
        }
        for label, rows in counts.items()
    }
    bindings = {
        label: {
            "bundle_id": "same",
            "run_id": label,
            "attempt_id": "attempt",
            "config_hash": "synthetic",
        }
        for label in LABELS
    }
    d = {
        "family_id": "synthetic",
        "read_authority": {"read_run_id": "synthetic-read"},
        "summaries": summaries,
        "feedback": {
            "groups": [
                {
                    "sample_id": sid,
                    "members": [
                        {
                            "candidate_id": label,
                            "native_counts": counts[label][sid],
                            "execution": copy.deepcopy(execution),
                        }
                        for label in LABELS
                    ],
                }
                for sid in ids
            ],
            "sources": [{"candidate_id": label, **b} for label, b in bindings.items()],
        },
    }
    recipe = {
        "sample_ids": ids,
        "family_id": "synthetic",
        "run_ids": {"read": "synthetic-read"},
        "resampling": {
            "bootstrap_draws": 10000,
            "confidence": 0.95,
            "seed": 20261001,
            "unit": "paired utterance; keep all recording variants together",
        },
    }
    return d, recipe, roster, bindings, counts


def describe(d, recipe, roster, bindings):
    return shared._describe_complete_cohort(
        d,
        ids=recipe["sample_ids"],
        bindings=bindings,
        recipe=recipe,
        roster=roster,
        comparison_groups=GROUPS,
    )


def test_pooled_signed_points_shared_draws_and_legacy_report(monkeypatch):
    d, recipe, roster, bindings, counts = cohort()
    legacy = describe(d, recipe, roster, bindings)
    recipe["additional_paired_contrasts"] = declaration()
    calls = []
    original = shared.resampled_statistic

    def capture(**kwargs):
        sequences, values = [], []
        callback = kwargs["statistic"]

        def statistic(selected):
            value = callback(selected)
            sequences.append(tuple(selected))
            values.append(value)
            return value

        result = original(**{**kwargs, "statistic": statistic})
        calls.append((sequences, values, result))
        return result

    monkeypatch.setattr(shared, "resampled_statistic", capture)
    report = describe(d, recipe, roster, bindings)
    additional = report.pop("additional_paired_contrasts")
    assert report == legacy
    assert additional["definition"] == declaration()
    # Hand pooled F1 values: control 22/34, solver 24/34, reviewer 26/34, joint 30/36.
    f = {
        "control": 22 / 34,
        "solver-import": 24 / 34,
        "reviewer-import": 26 / 34,
        "joint-import": 30 / 36,
    }
    expected = [
        f["joint-import"] - f["solver-import"],
        f["joint-import"] - f["reviewer-import"],
        f["joint-import"] - f["solver-import"] - f["reviewer-import"] + f["control"],
    ]
    for result, point in zip(additional["contrasts"].values(), expected):
        assert result["slu_f1"]["point_estimate"] == pytest.approx(point)
        assert result["slu_f1"]["seed"] == 20261001
        assert result["slu_f1"]["n_replicates"] == 10000
        assert result["slu_f1"]["ci_level"] == 0.95
    ids = recipe["sample_ids"]
    mean_row_delta = math.fsum(
        pooled_f1(counts["joint-import"], [sid], shared.FIELDS)
        - pooled_f1(counts["solver-import"], [sid], shared.FIELDS)
        for sid in ids
    ) / len(ids)
    assert expected[0] != pytest.approx(mean_row_delta)
    assert (
        len(calls) == 17
    )  # Seven legacy comparisons, two metrics each, plus three contrasts.
    assert all(call[0] == calls[0][0] for call in calls)
    draws = calls[-1][0][1:]
    assert any(len(set(draw)) < len(draw) and len(draw) != len(ids) for draw in draws)
    for draw, value in zip(draws, calls[-1][1][1:]):
        frequencies = Counter(draw)
        for cluster in {r["utterance_id"] for r in roster.values()}:
            assert (
                len(
                    {
                        frequencies[sid]
                        for sid in ids
                        if roster[sid]["utterance_id"] == cluster
                    }
                )
                == 1
            )
        expected_draw = math.fsum(
            coefficient * pooled_f1(counts[label], draw, shared.FIELDS)
            for label, coefficient in declaration()["contrasts"][2][
                "coefficients"
            ].items()
        )
        assert value == pytest.approx(expected_draw)
    # Independent shifted member draws give different replicate values on this correlated fixture.
    independent = [
        math.fsum(
            coefficient
            * pooled_f1(counts[label], draws[(i + j) % len(draws)], shared.FIELDS)
            for j, (label, coefficient) in enumerate(
                declaration()["contrasts"][2]["coefficients"].items()
            )
        )
        for i in range(len(draws))
    ]
    assert independent != calls[-1][1][1:]
    independent_interval = (
        _percentile(sorted(independent), 0.025),
        _percentile(sorted(independent), 0.975),
    )
    assert independent_interval != calls[-1][2].ci
    assert (
        "nominal" in additional["interpretation"]
        and "selection" in additional["interpretation"]
    )
    assert all(
        set(row["contrasts"]) == set(additional["contrasts"])
        for row in additional["per_stratum"]
    )


@pytest.mark.parametrize("mode", ["zero", "identical"])
def test_zero_conventions_and_order_invariance(mode):
    d, recipe, roster, bindings, _ = cohort(
        zero=mode == "zero", identical=mode == "identical"
    )
    recipe["additional_paired_contrasts"] = declaration()
    report = describe(d, recipe, roster, bindings)["additional_paired_contrasts"]
    for entry in report["contrasts"].values():
        assert (
            entry["slu_f1"]["point_estimate"]
            == entry["slu_f1"]["ci_low"]
            == entry["slu_f1"]["ci_high"]
            == 0
        )
    recipe["sample_ids"].reverse()
    d["feedback"]["groups"].reverse()
    recipe["additional_paired_contrasts"]["contrasts"][2]["coefficients"] = dict(
        reversed(
            list(
                recipe["additional_paired_contrasts"]["contrasts"][2][
                    "coefficients"
                ].items()
            )
        )
    )
    reversed_report = describe(d, recipe, roster, bindings)[
        "additional_paired_contrasts"
    ]
    assert reversed_report == report


@pytest.mark.parametrize(
    "fault",
    [
        "null",
        "schema",
        "key",
        "group",
        "metric",
        "empty",
        "id",
        "duplicate-id",
        "duplicate-definition",
        "reserved",
        "unknown",
        "bool",
        "zero",
        "float",
        "three",
        "signs",
        "term-key",
    ],
)
def test_schema_rejects_malformed_opt_in(fault):
    block = declaration()
    c = block["contrasts"][0]
    if fault == "null":
        block = None
    elif fault == "schema":
        block["schema"] = "future"
    elif fault == "key":
        block["extra"] = True
    elif fault == "group":
        block["comparison_group"] = "unknown"
    elif fault == "metric":
        block["metric"] = "intent"
    elif fault == "empty":
        block["contrasts"] = []
    elif fault == "id":
        c["id"] = ""
    elif fault == "duplicate-id":
        block["contrasts"][1]["id"] = c["id"]
    elif fault == "duplicate-definition":
        block["contrasts"].append(
            {
                "id": "copy",
                "coefficients": dict(reversed(list(c["coefficients"].items()))),
            }
        )
    elif fault == "reserved":
        c["id"] = "joint-import-minus-parent"
    elif fault == "unknown":
        c["coefficients"] = {"joint-import": 1, "unknown": -1}
    elif fault == "bool":
        c["coefficients"]["joint-import"] = True
    elif fault == "zero":
        c["coefficients"]["joint-import"] = 0
    elif fault == "float":
        c["coefficients"]["joint-import"] = 1.0
    elif fault == "three":
        c["coefficients"]["control"] = 1
    elif fault == "signs":
        c["coefficients"]["solver-import"] = 1
    elif fault == "term-key":
        c["extra"] = 1
    with pytest.raises(PolicyError):
        shared.validate_additional_paired_contrasts(
            {"additional_paired_contrasts": block}, GROUPS
        )


@pytest.mark.parametrize("fault", ["member", "missing-count", "negative", "nonfinite"])
def test_invalid_complete_counts_never_impute_or_drop(fault):
    d, recipe, roster, bindings, _ = cohort()
    recipe["additional_paired_contrasts"] = declaration()
    members = d["feedback"]["groups"][0]["members"]
    if fault == "member":
        members.pop()
    elif fault == "missing-count":
        members[0]["native_counts"].pop("slu_f1_word_tp")
    else:
        members[0]["native_counts"]["slu_f1_word_tp"] = (
            -1 if fault == "negative" else float("nan")
        )
    with pytest.raises((PolicyError, ValueError, KeyError)):
        describe(d, recipe, roster, bindings)


def test_opt_in_resampling_drift_stops_before_bootstrap(monkeypatch):
    d, recipe, roster, bindings, _ = cohort()
    recipe["additional_paired_contrasts"] = declaration()
    registration = {
        "member_bindings": bindings,
        "registration_sha256": "synthetic",
        "additional_paired_contrasts": declaration(),
    }
    d.update(schema=manual.SCHEMA, registration_sha256="synthetic")
    scope = {
        "labels": LABELS,
        "stage": {
            "control_members": LABELS[:2],
            "candidate_members": LABELS[2:],
            "N": 6,
        },
        "review_applicability": {},
    }

    def forbidden(*a, **k):
        pytest.fail("drift reached statistics")

    monkeypatch.setattr(manual, "_describe_complete_cohort", forbidden)
    for key, value in [
        ("seed", 7),
        ("bootstrap_draws", 10000.0),
        ("bootstrap_draws", 2),
        ("confidence", 0.9),
        ("unit", "row"),
    ]:
        supplement = {"resampling": {**recipe["resampling"], key: value}}
        with pytest.raises(PolicyError, match="resampling"):
            manual.analyze(
                manual.CompleteArchitectureEvidence(canonical(d)),
                recipe=recipe,
                registration=registration,
                roster=roster,
                supplement=supplement,
                scope=scope,
            )


def test_nonzero_order_invariance_and_stratum_point_summaries():
    d, recipe, roster, bindings, _ = cohort()
    recipe["additional_paired_contrasts"] = declaration()
    report = describe(d, recipe, roster, bindings)
    additional = report["additional_paired_contrasts"]
    for stratum, described in zip(report["per_stratum"], additional["per_stratum"]):
        for contrast in declaration()["contrasts"]:
            expected = math.fsum(
                weight * stratum["members"][label]["slu_f1"]
                for label, weight in contrast["coefficients"].items()
            )
            assert described["contrasts"][contrast["id"]] == pytest.approx(expected)
    for name, point in additional["equal_stratum_macro"].items():
        assert point == pytest.approx(
            math.fsum(row["contrasts"][name] for row in additional["per_stratum"]) / 2
        )
    recipe["sample_ids"].reverse()
    d["feedback"]["groups"].reverse()
    bindings = dict(reversed(list(bindings.items())))
    for group in d["feedback"]["groups"]:
        group["members"].reverse()
    for contrast in recipe["additional_paired_contrasts"]["contrasts"]:
        contrast["coefficients"] = dict(
            reversed(list(contrast["coefficients"].items()))
        )
    assert (
        describe(d, recipe, roster, bindings)["additional_paired_contrasts"]
        == additional
    )


@pytest.mark.parametrize(
    "fault", ["recipe-only", "registration-only", "definition", "null"]
)
def test_source_registration_drift_refuses_before_source_resolution(
    tmp_path, monkeypatch, fault
):
    from test_system_architecture_read import scope_fixture
    from speech_aware_evidence_acquisition.rails.hashing import content_hash

    _, recipe, registration, owner, *_ = scope_fixture(tmp_path, monkeypatch)
    labels = list(registration["expected_members"])
    block = {
        "schema": "saea-additional-pooled-contrasts-v1",
        "comparison_group": "architecture",
        "metric": "slu_f1",
        "contrasts": [
            {"id": "synthetic", "coefficients": {labels[0]: -1, labels[2]: 1}}
        ],
    }
    recipe["additional_paired_contrasts"] = copy.deepcopy(block)
    registration["additional_paired_contrasts"] = copy.deepcopy(block)
    if fault == "recipe-only":
        registration.pop("additional_paired_contrasts")
    elif fault == "registration-only":
        recipe.pop("additional_paired_contrasts")
    elif fault == "definition":
        registration["additional_paired_contrasts"]["contrasts"][0]["id"] = "changed"
    else:
        recipe["additional_paired_contrasts"] = registration[
            "additional_paired_contrasts"
        ] = None
    registration["registration_sha256"] = content_hash(
        {k: v for k, v in registration.items() if k != "registration_sha256"}
    )
    with pytest.raises(PolicyError, match="additional"):
        manual.validate_source_registration(
            recipe, registration, owner, repo_root=tmp_path, data_root=tmp_path / "data"
        )


@pytest.mark.parametrize("duplicate", ["member", "contrast-id", "block"])
def test_optional_json_rejects_repeated_keys_before_weights_collapse(duplicate):
    import json

    raw = json.dumps({"additional_paired_contrasts": declaration()})
    if duplicate == "member":
        raw = raw.replace(
            '"joint-import": 1', '"joint-import": -1, "joint-import": 1', 1
        )
    elif duplicate == "contrast-id":
        raw = raw.replace(
            '"id": "joint-minus-solver"',
            '"id": "discarded", "id": "joint-minus-solver"',
            1,
        )
    else:
        raw = raw.replace(
            '"additional_paired_contrasts":',
            '"additional_paired_contrasts": null, "additional_paired_contrasts":',
            1,
        )
    with pytest.raises(PolicyError, match="duplicate"):
        shared.load_additional_contrast_document(raw)
    assert shared.load_additional_contrast_document('{"legacy": 1, "legacy": 2}') == {
        "legacy": 2
    }


@pytest.mark.parametrize(
    "fault", ["resampling", "missing-dependency", "wrong-dependency"]
)
def test_document_loader_refuses_drift_before_evidence_access(tmp_path, fault):
    import importlib.util
    import json
    from test_manual_architecture_authoring import helper, SOURCE

    repo = tmp_path / "source-only"
    repo.mkdir()

    def write_pin(rel, document):
        path = repo / rel
        helper.write_new(path, document)
        return helper.raw_pin(path, repo)

    source_code = {}
    for name, rel in {
        "reader": "scripts/analysis/system_text_pilot_read.py",
        "analyzer": "src/speech_aware_evidence_acquisition/analysis/system_architecture_read.py",
        **{
            name: "src/speech_aware_evidence_acquisition/analysis/" + name + ".py"
            for name in (
                "system_text_update",
                "paired",
                "bootstrap",
                "null_calibration",
            )
        },
    }.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((SOURCE / rel).read_bytes())
        source_code[name] = helper.raw_pin(path, repo)
    spec = importlib.util.spec_from_file_location(
        "synthetic_contrast_loader",
        SOURCE / "scripts/analysis/system_text_pilot_read.py",
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    recipe = {
        "manual_architecture_registration": write_pin(
            "registration.json", {"additional_paired_contrasts": declaration()}
        ),
        "architecture_proof": manual.SELECTOR,
        "comparison_groups": GROUPS,
        "additional_paired_contrasts": declaration(),
        "resampling": cohort()[1]["resampling"],
    }
    recipe_pin = write_pin("recipe.json", recipe)
    supplement = {
        "schema": "saea-manual-architecture-analysis-supplement-v1",
        "recipe": recipe_pin,
        "registration": recipe["manual_architecture_registration"],
        "owner_decision": write_pin(
            "owner.json", {"status": "synthetic metadata only"}
        ),
        "source_code": source_code,
        "resampling": copy.deepcopy(recipe["resampling"]),
    }
    valid_pin = write_pin("valid-supplement.json", supplement)
    assert cli.load_documents(recipe_pin, valid_pin, repo)[0] == json.loads(
        (repo / "recipe.json").read_text()
    )
    if fault == "resampling":
        supplement["resampling"]["seed"] = 1
    elif fault == "missing-dependency":
        supplement["source_code"].pop("paired")
    else:
        supplement["source_code"]["paired"]["sha256"] = "f" * 64
    with pytest.raises(PolicyError, match="resampling|dependency"):
        cli.load_documents(
            recipe_pin, write_pin("bad-supplement.json", supplement), repo
        )


@pytest.mark.parametrize("weight", [True, 1.0])
def test_immutable_definition_binding_requires_exact_json_types(weight):
    recipe = {"additional_paired_contrasts": declaration()}
    registration = copy.deepcopy(recipe)
    registration["additional_paired_contrasts"]["contrasts"][0]["coefficients"][
        "joint-import"
    ] = weight
    with pytest.raises(PolicyError, match="definition"):
        shared.require_additional_contrast_binding(recipe, registration)


@pytest.mark.parametrize(
    "raw",
    [
        '{"analysis_definition":{"additional_paired_contrasts":null},"analysis_definition":{}}',
        '{"outer":{"inner":{"additional_paired_contrasts":null}},"outer":{}}',
        '{"items":[{"additional_paired_contrasts":null}],"unrelated":1,"unrelated":2}',
        '{"outer":{"additional_paired_contrasts":null,"duplicate":1,"duplicate":2}}',
        '[{"additional_paired_contrasts":null},{"duplicate":1,"duplicate":2}]',
        '{"analysis_definition":{"additional\\u005fpaired_contrasts":null},"analysis_definition":{}}',
    ],
)
def test_raw_opt_in_survives_enclosing_duplicates_and_nested_objects(raw):
    with pytest.raises(PolicyError, match="duplicate"):
        shared.load_additional_contrast_document(raw)


@pytest.mark.parametrize(
    "raw",
    [
        '{"analysis_definition":{"legacy":1},"analysis_definition":{}}',
        '{"value":"additional_paired_contrasts","value":"legacy"}',
        '{"nested":{"value":"additional_paired_contrasts","duplicate":1,"duplicate":2}}',
        '[{"text":"additional_paired_contrasts","duplicate":1,"duplicate":2}]',
        '{"string":"\\"additional_paired_contrasts\\":null","duplicate":1,"duplicate":2}',
        '{"analysis_definition":null}',
        "[1,2,3]",
        "null",
    ],
)
def test_genuinely_absent_raw_property_preserves_legacy_decoding(raw):
    import json

    assert shared.load_additional_contrast_document(raw) == json.loads(raw)


def test_nested_opt_in_without_duplicate_decodes_exactly():
    import json

    raw = '{"outer":[{"additional_paired_contrasts":null}]}'
    assert shared.load_additional_contrast_document(raw) == json.loads(raw)


def test_registered_negative_control_weight_remains_descriptive():
    d, recipe, roster, bindings, _ = cohort()
    recipe["additional_paired_contrasts"] = {
        **declaration(),
        "contrasts": [
            {
                "id": "joint-minus-control",
                "coefficients": {"joint-import": 1, "control": -1},
            }
        ],
    }
    additional = describe(d, recipe, roster, bindings)["additional_paired_contrasts"]
    assert additional["contrasts"]["joint-minus-control"]["slu_f1"][
        "point_estimate"
    ] == pytest.approx(30 / 36 - 22 / 34)
    assert "unregistered calibration" in additional["interpretation"]
    assert "subtracted from these contrasts" not in additional["interpretation"]
