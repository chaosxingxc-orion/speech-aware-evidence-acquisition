"""Use real frozen registration metadata with synthetic authority and feedback."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.system_text_update import analyze_update
from speech_aware_evidence_acquisition.rails.system_text_feedback import (
    CompleteSystemFeedback,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError,
    canonical,
)
from test_system_text_search_cli import cli, read_fixture, write
from test_system_text_update_read import fixture

ROOT = Path(__file__).resolve().parents[2]
RECIPE = (
    "docs/readiness/2026-10-02-slurp-system-text-update1-v1/analysis-recipe-v1.json"
)
PROTOCOL = "docs/readiness/2026-10-01-slurp-system-text-search-v1/protocol-control-v3-owner217.json"


def registered_recipe():
    return json.loads((ROOT / RECIPE).read_text())


def authority_fixture(tmp_path):
    spec, ledger, path = read_fixture(tmp_path)
    recipe = registered_recipe()
    # Only the temporary synthetic ledger grants READ. No actual result is opened.
    recipe["read_run_id"] = "FIXTURE-READ"
    recipe["run_ids"] = {"read": "FIXTURE-READ"}
    spec.update(
        family_id=recipe["stage"],
        expected_members=recipe["members"],
        initial_reference_member=None,
    )
    write(path, recipe)
    spec["read_registration"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return spec, ledger, path, recipe


def test_actual_nested_registration_is_accepted_without_rewriting_recipe(tmp_path):
    spec, _, path, recipe = authority_fixture(tmp_path)
    before = path.read_bytes()
    authority = cli.require_read_registration(spec, repo_root=tmp_path)
    assert authority["stage_registration"] == recipe["system_search_stage"]
    assert authority["recipe"] == spec["read_registration"]
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "fault",
    [
        "family-alias",
        "member-alias",
        "stage",
        "members",
        "missing-members",
        "missing-stage",
        "missing-registration",
        "registration-hash",
        "evaluation",
        "schema",
        "initial-alias",
    ],
)
def test_conflicting_or_unbound_aliases_refuse_before_feedback(
    tmp_path, monkeypatch, fault
):
    spec, _, path, recipe = authority_fixture(tmp_path)
    if fault == "family-alias":
        recipe["family_id"] = "update-2"
    elif fault == "member-alias":
        recipe["expected_members"] = {"other": "RUN"}
    elif fault == "stage":
        recipe["stage"] = "update-2"
    elif fault == "members":
        recipe["members"].pop("B-parent-aa")
    elif fault == "missing-members":
        recipe.pop("members")
    elif fault == "missing-stage":
        recipe.pop("stage")
    elif fault == "missing-registration":
        recipe.pop("system_search_stage")
    elif fault == "registration-hash":
        recipe["system_search_stage"]["registration_sha256"] = "f" * 64
    elif fault == "evaluation":
        recipe["system_search_evaluation"]["stage"] = "update-2"
    elif fault == "schema":
        recipe["schema"] = "unregistered-format"
    else:
        recipe["initial_members"] = recipe["members"]
    write(path, recipe)
    spec["read_registration"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    family = tmp_path / "family.json"
    write(family, spec)
    monkeypatch.setattr(
        cli.CompleteSystemFeedback,
        "from_family",
        lambda *a, **k: pytest.fail("do not open feedback"),
    )
    with pytest.raises(PolicyError):
        cli.read_family(family, repo_root=tmp_path)


def test_nested_recipe_still_requires_exact_root_signature_before_feedback(
    tmp_path, monkeypatch
):
    spec, ledger, _, _ = authority_fixture(tmp_path)
    ledger.write_text(ledger.read_text().replace("ROOT COUNTERSIGNED", "DRAFT"))
    family = tmp_path / "family.json"
    write(family, spec)
    monkeypatch.setattr(
        cli.CompleteSystemFeedback,
        "from_family",
        lambda *a, **k: pytest.fail("do not open feedback"),
    )
    with pytest.raises(PolicyError, match="not unambiguously root countersigned"):
        cli.read_family(family, repo_root=tmp_path)


def test_matching_aliases_are_allowed_but_preserve_original_authority_pin(tmp_path):
    spec, _, path, recipe = authority_fixture(tmp_path)
    recipe.update(family_id=recipe["stage"], expected_members=recipe["members"])
    write(path, recipe)
    spec["read_registration"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert (
        cli.require_read_registration(spec, repo_root=tmp_path)["recipe"]
        == spec["read_registration"]
    )


def test_actual_recipe_drives_statistics_with_only_synthetic_quality(tmp_path):
    _, feedback, _, _ = fixture(tmp_path)
    document = feedback.as_json()
    recipe = registered_recipe()
    before = copy.deepcopy(recipe)
    protocol = json.loads((ROOT / PROTOCOL).read_text())
    stage = next(s for s in protocol["stages"] if s["stage"] == "update-1")
    members = recipe["members"]
    bindings = recipe["system_search_evaluation"]["member_bindings"]
    document["read_authority"]["stage_registration"] = recipe["system_search_stage"]
    document["summaries"] = {
        k: v for k, v in document["summaries"].items() if k in members
    }
    document["feedback"]["candidate_ids"] = sorted(members)
    document["feedback"]["sources"] = [
        {**row, **bindings[row["candidate_id"]]}
        for row in document["feedback"]["sources"]
        if row["candidate_id"] in members
    ]
    metadata = {}
    for i, (sid, group) in enumerate(
        zip(stage["sample_ids"], document["feedback"]["groups"], strict=True)
    ):
        group["sample_id"] = sid
        group["members"] = [m for m in group["members"] if m["candidate_id"] in members]
        metadata[sid] = {
            "sample_id": sid,
            "utterance_id": f"synthetic-{i}",
            "stratum": "synthetic",
        }
    # No real score, answer, raw trace or feedback artifact is opened by this test.
    recipe["resampling"]["bootstrap_draws"] = 2
    report = analyze_update(
        CompleteSystemFeedback(canonical(document)),
        protocol=protocol,
        recipe=recipe,
        roster=metadata,
    )
    assert set(report["official_summaries"]) == set(members)
    recipe["resampling"] = before["resampling"]
    assert recipe == before
