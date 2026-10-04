"""Full semantic evidence reaches learners only after complete-family admission."""

import copy

import pytest
from test_system_trajectory import _source
from test_native_episode_diagnostics import _terminal_fixture, _finite_fixture
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from speech_aware_evidence_acquisition.rails import system_context_material as material


def test_full_role_requests_responses_and_phase_are_preserved():
    source = _source()
    source.bundle.trace_records["unrelated/request"] = {
        "sample_id": "other",
        "private": "exclude",
    }
    result = material.materialize_context_trajectory(source, "s1")
    assert result["phase_result"] == source.phase_results["s1"]
    assert result["terminal_output"] == source.output_rows["s1"]
    assert "unrelated/request" not in result["trace_records"]
    assert (
        result["trace_records"]["request-reviewer-2/request"]
        == source.bundle.trace_records["request-reviewer-2/request"]
    )
    assert (
        result["trace_records"]["request-reviewer-2/response"]
        == source.bundle.trace_records["request-reviewer-2/response"]
    )
    assert result["omissions"] == []
    assert result["material_sha256"] == content_hash(
        {k: v for k, v in result.items() if k != "material_sha256"}
    )


@pytest.mark.parametrize(
    "fixture", [_terminal_fixture, lambda: _finite_fixture(with_solver=True)]
)
def test_failure_and_interrupted_evidence_is_not_filtered(fixture):
    source = _source(fixture)
    result = material.materialize_context_trajectory(source, "s1")
    assert result["terminal_output"] == source.output_rows["s1"]
    assert result["trajectory"]["delivery"]["kind"] in {"terminal", "finite"}


def test_unknown_sample_and_missing_role_record_fail():
    with pytest.raises((ValueError, KeyError)):
        material.materialize_context_trajectory(_source(), "outside")
    source = _source()
    del source.bundle.trace_records["request-reviewer-2/response"]
    with pytest.raises(ValueError):
        material.materialize_context_trajectory(source, "s1")


def test_material_is_independent_and_non_english_is_not_silently_dropped():
    source = _source()
    result = material.materialize_context_trajectory(source, "s1")
    result["phase_result"]["new"] = "separate"
    assert "new" not in source.phase_results["s1"]
    source.phase_results["s1"]["extra"] = "\u4e2d\u6587"
    with pytest.raises(ValueError):
        material.materialize_context_trajectory(source, "s1")


class Archive:
    def __init__(self):
        self.rows = {}

    def _write(self, path, value):
        assert path not in self.rows
        self.rows[path] = value


def setup(monkeypatch):
    source = _source()
    source.bundle.manifest.update(raw_trace={"path": "/trace", "sha256": "d" * 64})
    source.bundle.manifest["outputs"]["path"] = "/outputs"
    row = {
        "candidate_id": "candidate",
        "execution": {
            "trace": source.bundle.manifest["raw_trace"],
            "terminal_output": source.bundle.manifest["outputs"],
        },
    }
    evidence = {
        "read_authority": {"read_id": "signed"},
        "feedback": {"groups": [{"sample_id": "s1", "members": [row]}]},
    }
    recipe = {"sample_ids": ["s1"], "family_id": "test"}
    registration = {
        "member_bindings": {
            "candidate": {
                "run_id": "run",
                "attempt_id": "attempt",
                "config_hash": "c" * 64,
            }
        }
    }
    qualified = (
        evidence,
        recipe,
        registration,
        {},
        ["candidate"],
        ["seed", "seed-aa"],
        {},
    )
    monkeypatch.setattr(material, "_qualified_feedback", lambda *a, **kw: qualified)
    monkeypatch.setattr(material, "verify_native_episode_source", lambda **kw: source)
    bindings = [
        {
            "candidate_id": "candidate",
            "config": {"manifest": {"path": "/manifest", "sha256": "e" * 64}},
        }
    ]
    specs = {
        "candidate": {
            "repo_root": "/frozen",
            "phase": {"path": "/phase", "sha256": "b" * 64},
        }
    }
    return source, evidence, recipe, bindings, specs


def export(archive, bindings, specs):
    return material.export_context_source_material(
        archive,
        bindings=bindings,
        recipe_pin={"relpath": "recipe.json", "sha256": "f" * 64},
        repo_root="/current",
        data_root="/data",
        source_specs=specs,
    )


def test_unsigned_read_precedes_any_semantic_source_or_write(monkeypatch):
    def refuse(*a, **kw):
        raise PolicyError("unsigned READ")

    monkeypatch.setattr(material, "_qualified_feedback", refuse)
    monkeypatch.setattr(
        material,
        "verify_native_episode_source",
        lambda **kw: pytest.fail("source opened"),
    )
    archive = Archive()
    with pytest.raises(PolicyError, match="unsigned"):
        export(archive, [], {})
    assert archive.rows == {}


def test_complete_qualified_source_export_has_exact_index_and_no_controls(monkeypatch):
    source, evidence, recipe, bindings, specs = setup(monkeypatch)
    archive = Archive()
    index = export(archive, bindings, specs)
    assert len(index["members"]["candidate"]) == 1
    ref = index["members"]["candidate"][0]
    assert ref["sample_id"] == "s1"
    assert (
        archive.rows[ref["archive_path"]]["material_sha256"] == ref["material_sha256"]
    )
    assert index["family_sha256"] == content_hash(evidence)
    assert index["contacts_added"] == {"model": 0, "scorer": 0}
    assert len(archive.rows) == 2


@pytest.mark.parametrize(
    "mutation", ["control", "identity", "cohort", "trace", "output"]
)
def test_wrong_source_binding_fails_before_material_publication(monkeypatch, mutation):
    source, evidence, recipe, bindings, specs = setup(monkeypatch)
    if mutation == "control":
        specs["seed"] = specs["candidate"]
    elif mutation == "identity":
        source.plan.run_id = "different"
    elif mutation == "cohort":
        recipe["sample_ids"] = ["different"]
    else:
        evidence["feedback"]["groups"][0]["members"][0]["execution"][
            "trace" if mutation == "trace" else "terminal_output"
        ] = {"path": "/wrong", "sha256": "0" * 64}
    archive = Archive()
    with pytest.raises(ValueError):
        export(archive, bindings, specs)
    assert archive.rows == {}


def test_authority_change_after_materialization_prevents_publication(monkeypatch):
    _, _, _, bindings, specs = setup(monkeypatch)
    original = material._qualified_feedback
    calls = []

    def changing(*args, **kwargs):
        result = copy.deepcopy(original(*args, **kwargs))
        calls.append(True)
        if len(calls) == 2:
            result[0]["read_authority"] = {"read_id": "different"}
        return result

    monkeypatch.setattr(material, "_qualified_feedback", changing)
    archive = Archive()
    with pytest.raises(PolicyError, match="changed during"):
        export(archive, bindings, specs)
    assert archive.rows == {}


def test_unexpected_phase_spec_is_refused(monkeypatch):
    _, _, _, bindings, specs = setup(monkeypatch)
    specs["candidate"]["extra"] = "not admitted"
    with pytest.raises(PolicyError, match="specification"):
        export(Archive(), bindings, specs)


def test_bulk_projection_indexes_each_source_once_with_identical_episode_bytes(
    monkeypatch,
):
    from dataclasses import replace

    source, evidence, recipe, bindings, specs = setup(monkeypatch)
    initial_index = material.export_system_trajectories(source)
    expected_first = material.materialize_context_trajectory(source, "s1")
    # Synthetic two-input projection isolates index scheduling; the existing
    # full-source tests verify actual request/response/receipt custody.
    second = copy.deepcopy(initial_index["trajectories"][0])
    second["sample_id"] = "s2"
    initial_index["sample_ids"].append("s2")
    initial_index["trajectories"].append(second)
    source = replace(
        source,
        sample_ids=("s1", "s2"),
        phase_results={
            "s1": source.phase_results["s1"],
            "s2": copy.deepcopy(source.phase_results["s1"]),
        },
        output_rows={
            "s1": source.output_rows["s1"],
            "s2": copy.deepcopy(source.output_rows["s1"]),
        },
    )
    recipe["sample_ids"].append("s2")
    other = copy.deepcopy(evidence["feedback"]["groups"][0])
    other["sample_id"] = "s2"
    evidence["feedback"]["groups"].append(other)
    monkeypatch.setattr(material, "verify_native_episode_source", lambda **kw: source)
    calls = []

    def index_once(value):
        calls.append(value)
        return initial_index

    monkeypatch.setattr(material, "export_system_trajectories", index_once)
    archive = Archive()
    index = export(archive, bindings, specs)
    assert len(calls) == 1
    first = index["members"]["candidate"][0]
    assert archive.rows[first["archive_path"]] == expected_first
