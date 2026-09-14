"""Synthetic-only tests for the native TRAIN stage diagnostic sidecar."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis.native_train_stage_diagnostics import (
    NativeTrainStageDiagnosticError,
    build_native_train_stage_diagnostics,
)
from speech_aware_evidence_acquisition.analysis import native_train_stage_diagnostics as module
from speech_aware_evidence_acquisition.analysis.slurp_topn_diagnostics import (
    ReferenceIntentRow,
    SourceCandidateRow,
)
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash


@dataclass(frozen=True)
class _Source:
    source_sample_id: str


class _Link:
    def __init__(self, sample_id: str, exact: int, roster_sha256: str = "b" * 64):
        self.source = _Source(sample_id)
        self.construction_roster_sha256 = roster_sha256
        self.native_score_vector = {
            "per_sample": {sample_id: {"scenario_action_exact": exact}}
        }

    def validate(self):
        return self


def _source(ids):
    return {
        "manifest_sha256": "1" * 64,
        "phase_artifact_sha256": "2" * 64,
        "diagnostic_config_sha256": "0" * 64,
        "reward_config_sha256": "3" * 64,
        "reward_artifact_sha256": "4" * 64,
        "complete_score_receipt_sha256": "5" * 64,
        "reference_binding_sha256": "a" * 64,
        "reference_lock_sha256": "d" * 64,
        "config_hash": "6" * 64,
        "run_id": "SAEA-SYNTHETIC-TRAIN-A",
        "attempt_id": "attempt-synthetic-train-a",
        "protocol_hash": "7" * 64,
        "split_identity_hash": split_identity_hash(prefixed("slurp", ids)),
        "candidate_projection_policy": (
            "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"
        ),
        "legal_candidate_inventory_sha256": "8" * 64,
    }


def _world():
    ids = tuple(f"slurp:train:synthetic-{index}" for index in range(4))
    candidates = (
        SourceCandidateRow(ids[0], ("intent-alpha", "intent-beta")),
        SourceCandidateRow(ids[1], ("intent-beta",)),
        SourceCandidateRow(ids[2], ("intent-alpha", "intent-beta", "intent-gamma")),
        SourceCandidateRow(ids[3], ("intent-gamma",)),
    )
    references = (
        ReferenceIntentRow(ids[0], "intent-alpha"),
        ReferenceIntentRow(ids[1], "intent-beta"),
        ReferenceIntentRow(ids[2], "private-gold-delta"),
        ReferenceIntentRow(ids[3], "private-gold-epsilon"),
    )
    links = tuple(_Link(sample_id, exact) for sample_id, exact in zip(ids, (1, 0, 0, 1)))
    return ids, candidates, references, links


def test_export_separates_coverage_and_conditional_correctness_without_gold_text():
    ids, candidates, references, links = _world()
    result = build_native_train_stage_diagnostics(
        candidate_rows=candidates,
        reference_rows=references,
        reward_links=links,
        source=_source(ids),
    )

    assert [row["initial_candidate_width"] for row in result["samples"]] == [2, 1, 3, 1]
    assert result["samples"][0]["covered_and_correct"] is True
    assert result["samples"][1]["covered_and_wrong"] is True
    assert result["samples"][2]["uncovered"] is True
    assert result["samples"][3]["uncovered"] is True
    assert result["aggregate"]["candidate_coverage"] == {
        "numerator": 2, "denominator": 4, "value": 0.5,
    }
    assert result["aggregate"]["conditional_accuracy_given_coverage"] == {
        "numerator": 1, "denominator": 2, "value": 0.5,
    }
    assert result["aggregate"]["correct_outside_candidate_set"] == {
        "numerator": 1, "denominator": 2, "value": 0.5,
    }
    serialized = json.dumps(result)
    assert "private-gold-delta" not in serialized
    assert "private-gold-epsilon" not in serialized
    assert result["semantics"]["uncovered_conditional_reward"] is None


def test_absent_coverage_has_an_explicit_zero_denominator_not_conditional_failures():
    ids, candidates, _references, links = _world()
    references = tuple(
        ReferenceIntentRow(sample_id, f"never-covered-{index}")
        for index, sample_id in enumerate(ids)
    )
    result = build_native_train_stage_diagnostics(
        candidate_rows=candidates,
        reference_rows=references,
        reward_links=links,
        source=_source(ids),
    )
    assert result["aggregate"]["conditional_accuracy_given_coverage"] == {
        "numerator": 0, "denominator": 0, "value": None,
    }
    assert all(row["uncovered"] for row in result["samples"])


@pytest.mark.parametrize(
    "bad_candidates",
    (
        (SourceCandidateRow("slurp:train:one", ()),),
        (SourceCandidateRow("slurp:train:one", ("a", "a")),),
        (
            SourceCandidateRow("slurp:train:one", ("a",)),
            SourceCandidateRow("slurp:train:one", ("b",)),
        ),
    ),
)
def test_malformed_or_duplicate_candidate_rows_fail_closed(bad_candidates):
    ids = tuple(row.sample_id for row in bad_candidates)
    references = tuple(ReferenceIntentRow(sample_id, "a") for sample_id in ids)
    links = tuple(_Link(sample_id, 1) for sample_id in ids)
    with pytest.raises(NativeTrainStageDiagnosticError):
        build_native_train_stage_diagnostics(
            candidate_rows=bad_candidates,
            reference_rows=references,
            reward_links=links,
            source=_source(ids),
        )


@pytest.mark.parametrize("mutation", ("reference-order", "reward-sample", "source-split", "roster"))
def test_wrong_cohort_or_source_fails_closed(mutation):
    ids, candidates, references, links = _world()
    source = _source(ids)
    if mutation == "reference-order":
        references = tuple(reversed(references))
    elif mutation == "reward-sample":
        links = (_Link("slurp:train:foreign", 1), *links[1:])
    elif mutation == "source-split":
        source["split_identity_hash"] = "9" * 64
    else:
        links = (*links[:-1], _Link(ids[-1], 1, roster_sha256="c" * 64))
    with pytest.raises(NativeTrainStageDiagnosticError):
        build_native_train_stage_diagnostics(
            candidate_rows=candidates,
            reference_rows=references,
            reward_links=links,
            source=source,
        )


def _write(path: Path, value: object) -> str:
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_prepared_sidecar_reuses_verified_source_candidate_and_reward_joins(
    tmp_path, monkeypatch
):
    ids, candidates, references, links = _world()
    manifest_path = tmp_path / "manifest.json"
    manifest_sha = _write(manifest_path, {"synthetic": True})
    phase_path = tmp_path / "phases.json"
    phase_sha = _write(phase_path, {"synthetic": True})
    reward_artifact_path = tmp_path / "reward-links.json"
    reward_artifact_sha = _write(reward_artifact_path, {"synthetic": True})
    reward_config = {
        "manifest": {"path": str(manifest_path), "sha256": manifest_sha},
        "complete_score_receipt": {"sha256": "5" * 64},
    }
    reward_config_path = tmp_path / "reward-config.json"
    reward_config_sha = _write(reward_config_path, reward_config)
    reference_lock_path = tmp_path / "lock.json"
    reference_lock_sha = _write(reference_lock_path, {"synthetic": True})
    reference = {
        "kind": "synthetic-reference",
        "lock": {"path": str(reference_lock_path), "sha256": reference_lock_sha},
    }
    config = {
        "schema": module.CONFIG_SCHEMA,
        "native_source": {
            "manifest": {"path": str(manifest_path), "sha256": manifest_sha},
            "phase_artifact": {"path": str(phase_path), "sha256": phase_sha},
        },
        "reward_source": {
            "config": {"path": str(reward_config_path), "sha256": reward_config_sha},
            "artifact": {
                "path": str(reward_artifact_path), "sha256": reward_artifact_sha,
            },
        },
        "reference_source": reference,
    }
    config_path = tmp_path / "config.json"
    config_sha = _write(config_path, config)
    verified = SimpleNamespace(
        plan=SimpleNamespace(
            carrier_lock_key="slurp",
            split_role="discovery",
            split_identity_hash=split_identity_hash(prefixed("slurp", ids)),
            run_id="SAEA-SYNTHETIC-TRAIN-A",
            attempt_id="attempt-synthetic-train-a",
            protocol_hash="7" * 64,
        ),
        sample_ids=ids,
        composed=SimpleNamespace(
            config_hash="6" * 64,
            values={
                "policy": "phase-native-candidates-review-revise-v1",
                "phase_material": {
                    "perception": {"fill_params": {"max_candidates": 3}}
                },
            },
        ),
        bundle=object(),
    )
    calls = []
    monkeypatch.setattr(
        module, "verify_native_episode_source", lambda **_kwargs: verified
    )
    monkeypatch.setattr(
        module,
        "read_verified_reward_link_artifact",
        lambda config, path: calls.append((config, path)) or links,
    )
    monkeypatch.setattr(
        module, "load_authoritative_slurp_candidate_ids", lambda *_args, **_kwargs: {"a"}
    )
    monkeypatch.setattr(
        module, "load_verified_slurp_reference_intents", lambda *_args, **_kwargs: references
    )
    monkeypatch.setattr(
        module,
        "load_verified_native_system_candidate_rows",
        lambda *_args, **_kwargs: (
            candidates,
            (),
            {
                "projection_policy": "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1",
                "legal_candidate_inventory_sha256": "8" * 64,
            },
        ),
    )

    output_path = tmp_path / "diagnostics.json"
    receipt = module.prepare_native_train_stage_diagnostics(
        config_path=config_path,
        expected_config_sha256=config_sha,
        source_repo_root=tmp_path,
        output_path=output_path,
        reference_loader=lambda *_args, **_kwargs: (),
        candidate_contract_loader=lambda *_args, **_kwargs: None,
    )

    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["output"]["aggregate"]["candidate_coverage"]["numerator"] == 2
    assert artifact["contact_class"] == "model-free"
    assert receipt["path"] == str(output_path)
    assert calls == [(reward_config, reward_artifact_path)]


def test_prepared_sidecar_rejects_a_reward_config_for_another_manifest(
    tmp_path, monkeypatch
):
    manifest_path = tmp_path / "manifest.json"
    manifest_sha = _write(manifest_path, {})
    phase_path = tmp_path / "phases.json"
    phase_sha = _write(phase_path, {})
    reward_artifact_path = tmp_path / "reward-links.json"
    reward_artifact_sha = _write(reward_artifact_path, {})
    reward_config_path = tmp_path / "reward-config.json"
    reward_config_sha = _write(
        reward_config_path,
        {
            "manifest": {"path": str(tmp_path / "foreign.json"), "sha256": "a" * 64},
            "complete_score_receipt": {"sha256": "5" * 64},
        },
    )
    config = {
        "schema": module.CONFIG_SCHEMA,
        "native_source": {
            "manifest": {"path": str(manifest_path), "sha256": manifest_sha},
            "phase_artifact": {"path": str(phase_path), "sha256": phase_sha},
        },
        "reward_source": {
            "config": {"path": str(reward_config_path), "sha256": reward_config_sha},
            "artifact": {
                "path": str(reward_artifact_path), "sha256": reward_artifact_sha,
            },
        },
        "reference_source": {
            "kind": "synthetic-reference",
            "lock": {"path": str(manifest_path), "sha256": manifest_sha},
        },
    }
    config_path = tmp_path / "config.json"
    config_sha = _write(config_path, config)
    monkeypatch.setattr(
        module,
        "verify_native_episode_source",
        lambda **_kwargs: SimpleNamespace(
            plan=SimpleNamespace(carrier_lock_key="slurp", split_role="discovery"),
            sample_ids=("slurp:train:synthetic",),
        ),
    )

    with pytest.raises(NativeTrainStageDiagnosticError, match="different native manifest"):
        module.prepare_native_train_stage_diagnostics(
            config_path=config_path,
            expected_config_sha256=config_sha,
            source_repo_root=tmp_path,
            output_path=tmp_path / "diagnostics.json",
            reference_loader=lambda *_args, **_kwargs: (),
        )
