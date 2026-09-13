"""Verify the actual recovered source shape, without inventing a finalized run."""

import hashlib
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis.slurp_topn_diagnostics_cli import (
    SlurpTopNAnalysisError, _source_pin, _source_contract,
)
from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import (
    FIRST_OCCURRENCE_PROJECTION_POLICY_ID, FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256,
)


def derived(tmp_path):
    contract = {"source_catalog": {"source_sha256": "c" * 64}}
    config = tmp_path / "baseline.json"
    config.write_text(json.dumps({"artifact_result": {"content_contract": contract}}))
    source = tmp_path / "hypotheses.source.json"
    source.write_text("{}")
    pin = {"path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
    bundle = SimpleNamespace(attempt_state="DERIVED", manifest={
        "schema": "saea-derived-hypothesis-source-v1",
        "status": "COMPLETED_DERIVATION", "source_attempt_state": "ABORTED",
        "result_kind": "artifact",
        "artifact_result": {
            "schema": "saea-derived-hypothesis-result-binding-v1",
            "role": "slurp-intent-hypotheses",
            "projection_policy_id": FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
            "projection_policy_sha256": FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256,
        },
        "data_root": str(tmp_path),
        "source_inputs": {"source_config": {
            "path": str(config),
            "sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
        }},
    })
    return {"hypothesis_artifact": pin}, bundle, contract


def test_verified_derived_source_keeps_aborted_parent_and_loads_original_contract(tmp_path):
    binding, bundle, contract = derived(tmp_path)
    assert _source_pin(binding, distinct=True)[0].name == "hypotheses.source.json"
    actual, root = _source_contract(bundle, distinct=True)
    assert actual == contract and root == tmp_path
    assert bundle.attempt_state == "DERIVED"
    assert bundle.manifest["source_attempt_state"] == "ABORTED"


@pytest.mark.parametrize("field,value", [
    ("status", "COMPLETED"),
    ("source_attempt_state", "FINALIZED"),
    ("schema", "unknown"),
])
def test_derived_source_identity_cannot_be_relabelled(tmp_path, field, value):
    _, bundle, _ = derived(tmp_path)
    bundle.manifest[field] = value
    with pytest.raises(SlurpTopNAnalysisError):
        _source_contract(bundle, distinct=True)


def test_legacy_fixed_source_cannot_borrow_derived_authority(tmp_path):
    _, bundle, _ = derived(tmp_path)
    with pytest.raises(SlurpTopNAnalysisError):
        _source_contract(bundle, distinct=False)


def test_derived_contract_source_bytes_are_pinned(tmp_path):
    _, bundle, _ = derived(tmp_path)
    (tmp_path / "baseline.json").write_text("{}")
    with pytest.raises((ValueError, SlurpTopNAnalysisError)):
        _source_contract(bundle, distinct=True)


def test_conflicting_source_aliases_are_rejected(tmp_path):
    binding, _, _ = derived(tmp_path)
    binding["manifest"] = {"path": "/different", "sha256": "a" * 64}
    with pytest.raises(SlurpTopNAnalysisError):
        _source_pin(binding, distinct=True)


def test_variable_source_width_preserves_every_actual_candidate():
    from speech_aware_evidence_acquisition.analysis.slurp_topn_diagnostics import (
        BranchOutcomeRow, ReferenceIntentRow, SourceCandidateRow,
        TopNDiagnosticError, aggregate_topn_diagnostics,
    )
    source = [SourceCandidateRow("s1", ("a",)), SourceCandidateRow("s2", ("a", "b"))]
    refs = [ReferenceIntentRow("s1", "a"), ReferenceIntentRow("s2", "b")]
    branches = {"joint": [BranchOutcomeRow("s1", "a", False), BranchOutcomeRow("s2", "b", False)]}
    with pytest.raises(TopNDiagnosticError, match="shorter"):
        aggregate_topn_diagnostics(source, refs, branches, candidate_width=3)
    report = aggregate_topn_diagnostics(
        source, refs, branches, candidate_width=3, allow_variable_width=True,
    ).as_json()
    assert [row["candidate_ids"] for row in report["per_sample"]] == [["a"], ["a", "b"]]
    assert all(row["topn_included"] for row in report["per_sample"])
    with pytest.raises(TopNDiagnosticError, match="maximum"):
        aggregate_topn_diagnostics(
            source, refs, branches, candidate_width=1, allow_variable_width=True,
        )
