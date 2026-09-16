"""Synthetic-only tests for the native TRAIN stage diagnostic sidecar."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis.native_train_stage_diagnostics import (
    NativeTrainStageDiagnosticError,
    build_native_train_candidate_stage_diagnostics,
    build_native_train_stage_diagnostics,
)
from speech_aware_evidence_acquisition.analysis.native_candidate_stage_projections import (
    NativeCandidateStage,
    NativeCandidateStagePair,
    project_verified_native_candidate_stages,
)
from speech_aware_evidence_acquisition.analysis import native_candidate_stage_projections
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


def _stage(sample_id, candidate_ids, visit_index, marker):
    return NativeCandidateStage(
        visit_index=visit_index,
        state_id=f"state:{sample_id}:{marker}",
        state_sha256=marker * 64,
        query_state_sha256="9" * 64,
        agent_contact_id=f"contact:{sample_id}:{marker}",
        request_id=f"request:{sample_id}:{marker}",
        request_sha256="a" * 64,
        response_sha256="b" * 64,
        response_text_sha256="c" * 64,
        candidate_ids=tuple(candidate_ids),
        candidate_set_sha256=hashlib.sha256(
            json.dumps(list(candidate_ids)).encode()
        ).hexdigest(),
    )


def _stage_pairs(ids, c0_rows, c1_rows):
    pairs = []
    for index, (sample_id, c0_row, c1_row) in enumerate(
        zip(ids, c0_rows, c1_rows, strict=True)
    ):
        c0 = _stage(sample_id, c0_row.candidate_ids, 0, str(index + 1))
        if c0_row.candidate_ids == c1_row.candidate_ids:
            c1 = c0
        else:
            c1 = _stage(sample_id, c1_row.candidate_ids, 4, str(index + 5))
        pairs.append(
            NativeCandidateStagePair(
                sample_id=sample_id,
                c0=c0,
                c1=c1,
                refresh_executed=c1 is not c0,
            )
        )
    return tuple(pairs)


def _receipt_contact(marker):
    return {
        "agent_contact_id": f"contact-{marker}",
        "request_id": f"request-{marker}",
        "request_sha256": "1" * 64,
        "response_sha256": "2" * 64,
        "response_text_sha256": "3" * 64,
    }


def _visit(stage, marker):
    contact = _receipt_contact(marker)
    return {
        "role_id": stage,
        "stage": stage,
        "execution_receipt": {"contacts": [contact], "final_contact": contact},
    }


def _finite_receipt(visits, interrupted, *, solver_receipt=None):
    rejected = interrupted["execution_receipt"]["final_contact"]
    receipt = {
        "role_visits": visits,
        "planner_routes": [],
        "interrupted_role": interrupted,
        "terminal_disposition": {
            "reason": "finite_completion",
            "finish_reason": "length",
            "role_id": interrupted["role_id"],
            "stage": interrupted["stage"],
            "revision_count": 0,
            "planner_accepted": False,
            "rejected_contact": rejected,
        },
    }
    if solver_receipt is None:
        receipt["abstention_receipt"] = {"source_contact": rejected}
    else:
        receipt["terminal_solver_receipt"] = solver_receipt
    return receipt


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


def test_train_diagnostics_accept_configured_five_and_reject_over_limit():
    sample_id = "slurp:train:synthetic-five"
    candidate_ids = tuple(f"intent-{index}" for index in range(5))
    candidates = (SourceCandidateRow(sample_id, candidate_ids),)
    references = (ReferenceIntentRow(sample_id, candidate_ids[-1]),)
    links = (_Link(sample_id, 1),)

    result = build_native_train_stage_diagnostics(
        candidate_rows=candidates,
        reference_rows=references,
        reward_links=links,
        source=_source((sample_id,)),
        max_candidates=5,
    )
    assert result["samples"][0]["initial_candidate_width"] == 5
    with pytest.raises(NativeTrainStageDiagnosticError, match="at most 4"):
        build_native_train_stage_diagnostics(
            candidate_rows=candidates,
            reference_rows=references,
            reward_links=links,
            source=_source((sample_id,)),
            max_candidates=4,
        )


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


def test_c0_c1_export_reports_recovery_loss_and_conditional_cohorts_without_gold_text():
    ids, c0_rows, references, links = _world()
    c1_rows = (
        c0_rows[0],
        SourceCandidateRow(ids[1], ("intent-gamma",)),
        SourceCandidateRow(ids[2], ("private-gold-delta",)),
        SourceCandidateRow(ids[3], ("intent-gamma",)),
    )
    result = build_native_train_candidate_stage_diagnostics(
        stage_pairs=_stage_pairs(ids, c0_rows, c1_rows),
        reference_rows=references,
        reward_links=links,
        source=_source(ids),
    )

    assert result["aggregate"]["initial_candidate_coverage"] == {
        "numerator": 2,
        "denominator": 4,
        "value": 0.5,
    }
    assert result["aggregate"]["pre_final_candidate_coverage"] == {
        "numerator": 2,
        "denominator": 4,
        "value": 0.5,
    }
    assert result["aggregate"]["recovered"]["numerator"] == 1
    assert result["aggregate"]["lost"]["numerator"] == 1
    assert result["aggregate"]["stable_covered"]["numerator"] == 1
    assert result["aggregate"]["stable_uncovered"]["numerator"] == 1
    assert result["aggregate"]["final_accuracy"] == {
        "numerator": 2,
        "denominator": 4,
        "value": 0.5,
    }
    assert result["aggregate"]["conditional_accuracy_given_initial_coverage"] == {
        "numerator": 1,
        "denominator": 2,
        "value": 0.5,
    }
    assert result["aggregate"]["conditional_accuracy_given_pre_final_coverage"] == {
        "numerator": 1,
        "denominator": 2,
        "value": 0.5,
    }
    assert result["aggregate"]["common_covered_final_accuracy"] == {
        "numerator": 1,
        "denominator": 1,
        "value": 1.0,
    }
    assert result["aggregate"]["correct_answers_outside_c1"] == {
        "numerator": 1,
        "denominator": 2,
        "value": 0.5,
    }
    assert result["samples"][0]["refresh_executed"] is False
    assert result["samples"][0]["c0"] == result["samples"][0]["c1"]
    assert result["samples"][1]["lost"] is True
    assert result["samples"][2]["recovered"] is True
    serialized = json.dumps(result)
    assert "private-gold-delta" not in serialized
    assert "private-gold-epsilon" not in serialized


def test_c0_c1_export_retains_explicit_zero_conditional_denominators():
    ids, c0_rows, references, links = _world()
    uncovered = tuple(
        SourceCandidateRow(sample_id, ("never-gold",)) for sample_id in ids
    )
    result = build_native_train_candidate_stage_diagnostics(
        stage_pairs=_stage_pairs(ids, uncovered, uncovered),
        reference_rows=references,
        reward_links=links,
        source=_source(ids),
    )

    for name in (
        "conditional_accuracy_given_initial_coverage",
        "conditional_accuracy_given_pre_final_coverage",
        "common_covered_final_accuracy",
    ):
        assert result["aggregate"][name] == {
            "numerator": 0,
            "denominator": 0,
            "value": None,
        }
    assert result["aggregate"]["correct_answers_outside_c1"] == {
        "numerator": 2,
        "denominator": 4,
        "value": 0.5,
    }


def test_stage_diagnostics_retain_missing_stages_and_report_available_denominators():
    ids, candidates, references, links = _world()
    pairs = list(_stage_pairs(ids, candidates, candidates))
    pairs[1] = NativeCandidateStagePair(ids[1], pairs[1].c0, None, False)
    pairs[2] = NativeCandidateStagePair(ids[2], None, None, False)

    result = build_native_train_candidate_stage_diagnostics(
        stage_pairs=pairs,
        reference_rows=references,
        reward_links=links,
        source=_source(ids),
    )

    assert result["cohort"]["sample_count"] == 4
    assert result["stage_availability"] == {
        "c0_available_count": 3,
        "c0_unavailable_count": 1,
        "c1_available_count": 2,
        "c1_unavailable_count": 2,
        "transition_eligible_count": 2,
        "transition_unavailable_count": 2,
    }
    assert result["aggregate"]["initial_candidate_coverage"] == {
        "numerator": 2, "denominator": 4, "value": 0.5,
    }
    assert result["aggregate"]["pre_final_candidate_coverage"] == {
        "numerator": 1, "denominator": 4, "value": 0.25,
    }
    assert result["aggregate"]["initial_candidate_coverage_available_stage"] == {
        "numerator": 2, "denominator": 3, "value": 2 / 3,
    }
    assert result["aggregate"]["pre_final_candidate_coverage_available_stage"] == {
        "numerator": 1, "denominator": 2, "value": 0.5,
    }
    for name in ("recovered", "lost", "stable_covered", "stable_uncovered"):
        assert result["aggregate"][name]["denominator"] == 2
    assert result["aggregate"]["correct_answers_outside_c1"] == {
        "numerator": 1, "denominator": 1, "value": 1.0,
    }
    assert result["aggregate"]["final_accuracy"] == {
        "numerator": 2, "denominator": 4, "value": 0.5,
    }
    missing_c1 = result["samples"][1]
    assert missing_c1["c0_available"] is True
    assert missing_c1["c1_available"] is False
    assert missing_c1["c1"] is None
    assert missing_c1["pre_final_covered"] is False
    assert missing_c1["recovered"] is None
    missing_both = result["samples"][2]
    assert missing_both["c0"] is None and missing_both["c1"] is None
    assert missing_both["initial_covered"] is False
    assert missing_both["transition_available"] is False


def test_projection_never_promotes_an_interrupted_initial_perception(monkeypatch):
    sample_id = "slurp:train:synthetic-finite-perception"
    interrupted = _visit("perception", "interrupted-perception")
    receipt = _finite_receipt([], interrupted)
    source = SimpleNamespace(
        sample_ids=(sample_id,),
        phase_results={sample_id: {"native_episode_receipt": receipt}},
    )
    monkeypatch.setattr(
        native_candidate_stage_projections,
        "_stage",
        lambda **_kwargs: pytest.fail("interrupted Perception must not be parsed"),
    )

    pair = project_verified_native_candidate_stages(
        source,
        legal_candidate_ids=frozenset({"intent-alpha"}),
        max_candidates=1,
    )[0]
    assert pair.c0 is None
    assert pair.c1 is None
    assert pair.refresh_executed is False


def test_projection_has_c0_but_no_c1_without_a_delivered_solver(monkeypatch):
    sample_id = "slurp:train:synthetic-no-solver"
    perception = _visit("perception", "completed-perception")
    interrupted = _visit("solver", "interrupted-solver")
    receipt = _finite_receipt([perception], interrupted)
    source = SimpleNamespace(
        sample_ids=(sample_id,),
        phase_results={sample_id: {"native_episode_receipt": receipt}},
    )
    monkeypatch.setattr(
        native_candidate_stage_projections,
        "_stage",
        lambda **kwargs: _stage(
            sample_id, ("intent-alpha",), kwargs["visit_index"], "a"
        ),
    )

    pair = project_verified_native_candidate_stages(
        source,
        legal_candidate_ids=frozenset({"intent-alpha"}),
        max_candidates=1,
    )[0]
    assert pair.c0 is not None
    assert pair.c1 is None
    assert pair.refresh_executed is False


def test_projection_keeps_c1_before_delivered_solver_despite_later_failed_work(
    monkeypatch,
):
    sample_id = "slurp:train:synthetic-prior-solver"
    perception_before = _visit("perception", "perception-before")
    solver = _visit("solver", "delivered-solver")
    perception_after = _visit("perception", "perception-after")
    interrupted = _visit("reviewer", "interrupted-reviewer")
    interrupted["stage"] = "review"
    visits = [perception_before, solver, perception_after]
    receipt = _finite_receipt(
        visits, interrupted, solver_receipt=solver["execution_receipt"],
    )
    source = SimpleNamespace(
        sample_ids=(sample_id,),
        phase_results={sample_id: {"native_episode_receipt": receipt}},
    )

    def stage(**kwargs):
        return _stage(sample_id, ("intent-alpha",), kwargs["visit_index"], "a")

    monkeypatch.setattr(native_candidate_stage_projections, "_stage", stage)
    pair = project_verified_native_candidate_stages(
        source,
        legal_candidate_ids=frozenset({"intent-alpha"}),
        max_candidates=1,
    )[0]
    assert pair.c0.visit_index == 0
    assert pair.c1.visit_index == 0
    assert pair.refresh_executed is True
    assert pair.refresh_used_by_delivered_solver is False
    assert pair.refresh_after_delivered_solver is True


def test_c0_c1_export_rejects_inconsistent_refresh_metadata():
    ids, candidates, references, links = _world()
    pair = _stage_pairs(ids, candidates, candidates)[0]
    malformed = NativeCandidateStagePair(
        sample_id=pair.sample_id,
        c0=pair.c0,
        c1=pair.c1,
        refresh_executed=True,
    )
    with pytest.raises(NativeTrainStageDiagnosticError, match="refresh semantics"):
        build_native_train_candidate_stage_diagnostics(
            stage_pairs=(malformed,),
            reference_rows=references[:1],
            reward_links=links[:1],
            source=_source(ids[:1]),
        )


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


def test_explicit_null_candidate_stage_projection_fails_as_malformed(tmp_path):
    config = {
        "schema": module.CONFIG_SCHEMA,
        "native_source": {},
        "reward_source": {},
        "reference_source": {},
        "candidate_stage_projection": None,
    }
    config_path = tmp_path / "config.json"
    config_sha = _write(config_path, config)
    with pytest.raises(
        NativeTrainStageDiagnosticError,
        match="candidate_stage_projection contract is invalid",
    ):
        module.prepare_native_train_stage_diagnostics(
            config_path=config_path,
            expected_config_sha256=config_sha,
            source_repo_root=tmp_path,
            output_path=tmp_path / "diagnostics.json",
            reference_loader=lambda *_args, **_kwargs: (),
        )


@pytest.mark.parametrize("stage_projection_enabled,support_enabled", ((False, False), (True, False), (True, True)))
def test_prepared_sidecar_reuses_verified_source_candidate_and_reward_joins(
    tmp_path, monkeypatch, stage_projection_enabled, support_enabled
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
    if stage_projection_enabled:
        config["candidate_stage_projection"] = {
            "schema": module.PROJECTION_CONFIG_SCHEMA,
            "policy_id": module.PROJECTION_POLICY_ID,
            "candidate_projection_policy": (
                "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"
            ),
        }
    if support_enabled:
        config["initial_intent_support_projection"] = {
            "schema": "saea-initial-intent-support-projection-v1",
            "policy_id": "initial-perception-request-intent-value-id-suffix-v1",
            "store_id": "intent-boundaries",
            "value_id_prefix": "intent-boundary:",
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
    reference_rows = {"value": references}
    monkeypatch.setattr(
        module,
        "load_verified_slurp_reference_intents",
        lambda *_args, **_kwargs: reference_rows["value"],
    )
    def singleton_reader(*_args, **_kwargs):
        if stage_projection_enabled:
            raise AssertionError("stage mode must not call the singleton reader")
        return (
            candidates,
            (),
            {
                "projection_policy": "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1",
                "legal_candidate_inventory_sha256": "8" * 64,
            },
        )

    def stage_reader(*_args, **_kwargs):
        if not stage_projection_enabled:
            raise AssertionError("legacy mode must not call the stage projector")
        return _stage_pairs(ids, candidates, candidates)

    monkeypatch.setattr(
        module, "load_verified_native_system_candidate_rows", singleton_reader
    )
    monkeypatch.setattr(
        module, "project_verified_native_candidate_stages", stage_reader
    )

    support_calls = []
    def support_reader(**kwargs):
        assert support_enabled
        assert kwargs["source"] is verified
        assert tuple(x.sample_id for x in kwargs["stage_pairs"]) == ids
        assert kwargs["reference_rows"] == reference_rows["value"]
        support_calls.append(kwargs["specification"])
        return {"synthetic_support": True}

    monkeypatch.setattr(module, "build_initial_intent_support_diagnostics", support_reader)
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
    coverage_name = (
        "initial_candidate_coverage"
        if stage_projection_enabled
        else "candidate_coverage"
    )
    assert artifact["output"]["aggregate"][coverage_name]["numerator"] == 2
    assert artifact["output"]["schema"] == (
        module.STAGE_OUTPUT_SCHEMA
        if stage_projection_enabled
        else module.OUTPUT_SCHEMA
    )
    assert artifact["kind"] == (
        module.STAGE_ARTIFACT_KIND
        if stage_projection_enabled
        else module.ARTIFACT_KIND
    )
    assert artifact["contact_class"] == "model-free"
    assert ("initial_intent_support" in artifact["output"]) == support_enabled
    assert bool(support_calls) == support_enabled
    if support_enabled:
        assert artifact["output"]["initial_intent_support"] == {"synthetic_support": True}
    assert receipt["path"] == str(output_path)
    assert calls == [(reward_config, reward_artifact_path)]

    warm_receipt = module.prepare_native_train_stage_diagnostics(
        config_path=config_path,
        expected_config_sha256=config_sha,
        source_repo_root=tmp_path,
        output_path=output_path,
        reference_loader=lambda *_args, **_kwargs: (),
        candidate_contract_loader=lambda *_args, **_kwargs: None,
    )
    assert warm_receipt == {**receipt, "cache": "warm"}

    reference_rows["value"] = (
        ReferenceIntentRow(ids[0], "changed-derived-reference"),
        *references[1:],
    )
    with pytest.raises(
        NativeTrainStageDiagnosticError,
        match="cannot persist stage diagnostics",
    ):
        module.prepare_native_train_stage_diagnostics(
            config_path=config_path,
            expected_config_sha256=config_sha,
            source_repo_root=tmp_path,
            output_path=output_path,
            reference_loader=lambda *_args, **_kwargs: (),
            candidate_contract_loader=lambda *_args, **_kwargs: None,
        )


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


def test_initial_support_requires_verified_candidate_stage_projection(tmp_path):
    config = {
        "schema": module.CONFIG_SCHEMA,
        "native_source": {}, "reward_source": {}, "reference_source": {},
        "initial_intent_support_projection": {
            "schema": "saea-initial-intent-support-projection-v1",
            "policy_id": "initial-perception-request-intent-value-id-suffix-v1",
            "store_id": "intent-boundaries", "value_id_prefix": "intent-boundary:",
        },
    }
    config_path = tmp_path / "config.json"
    sha = _write(config_path, config)
    with pytest.raises(NativeTrainStageDiagnosticError, match="requires candidate_stage_projection"):
        module.prepare_native_train_stage_diagnostics(
            config_path=config_path, expected_config_sha256=sha,
            source_repo_root=tmp_path, output_path=tmp_path / "output.json",
            reference_loader=lambda *_args, **_kwargs: (),
        )


@pytest.mark.parametrize("delivery_kind", ("accepted", "terminal", "finite"))
def test_delivered_solver_requires_completed_perception(monkeypatch, delivery_kind):
    sample_id = "slurp:train:missing-perception"
    solver = _visit("solver", "solver")
    source = SimpleNamespace(
        sample_ids=(sample_id,),
        phase_results={sample_id: {"native_episode_receipt": {"role_visits": [solver]}}},
    )
    monkeypatch.setattr(
        native_candidate_stage_projections, "validate_native_episode_delivery_receipt",
        lambda *_args, **_kwargs: SimpleNamespace(
            kind=delivery_kind, solver_receipt=solver["execution_receipt"],
        ),
    )
    with pytest.raises(
        native_candidate_stage_projections.NativeCandidateStageProjectionError,
        match="completed Perception",
    ):
        project_verified_native_candidate_stages(
            source, legal_candidate_ids=frozenset({"intent-alpha"}), max_candidates=1,
        )


@pytest.mark.parametrize("delivery_kind", ("accepted", "terminal"))
def test_legacy_delivery_rejects_later_perception(monkeypatch, delivery_kind):
    sample_id = "slurp:train:legacy-late-perception"
    solver = _visit("solver", "solver")
    visits = [_visit("perception", "p0"), solver, _visit("perception", "p1")]
    source = SimpleNamespace(
        sample_ids=(sample_id,),
        phase_results={sample_id: {"native_episode_receipt": {"role_visits": visits}}},
    )
    monkeypatch.setattr(
        native_candidate_stage_projections, "validate_native_episode_delivery_receipt",
        lambda *_args, **_kwargs: SimpleNamespace(
            kind=delivery_kind, solver_receipt=solver["execution_receipt"],
        ),
    )
    monkeypatch.setattr(
        native_candidate_stage_projections, "_stage",
        lambda **kwargs: _stage(sample_id, ("intent-alpha",), kwargs["visit_index"], "a"),
    )
    with pytest.raises(
        native_candidate_stage_projections.NativeCandidateStageProjectionError,
        match="after the delivered Solver",
    ):
        project_verified_native_candidate_stages(
            source, legal_candidate_ids=frozenset({"intent-alpha"}), max_candidates=1,
        )


def test_completed_refresh_after_fallback_is_counted_without_c1_credit():
    ids, candidates, references, links = _world()
    pairs = list(_stage_pairs(ids, candidates, candidates))
    pairs[0] = replace(
        pairs[0], refresh_executed=True, refresh_after_delivered_solver=True,
    )
    result = build_native_train_candidate_stage_diagnostics(
        stage_pairs=pairs, reference_rows=references,
        reward_links=links, source=_source(ids),
    )
    row = result["samples"][0]
    assert row["refresh_executed"] is True
    assert row["refresh_used_by_delivered_solver"] is False
    assert row["refresh_after_delivered_solver"] is True
    assert row["c0"] == row["c1"]
    assert result["aggregate"]["completed_refreshes"]["numerator"] == 1
    assert result["aggregate"]["refreshes_used_by_delivered_solver"]["numerator"] == 0
