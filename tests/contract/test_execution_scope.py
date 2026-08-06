"""Contract: the Stage-2 execution-scope guard is fail-closed (consolidated contract §6/§7).

This repository is a Stage-2 study carrier (umbrella Decision-Log 续91/续92). It accepts
exactly three execution profiles; ``paper-scale-confirmatory`` — and any forged variant —
is refused before any receipt or model asset is read.
"""

import pytest

from speech_aware_evidence_acquisition.contracts import (
    ALLOWED_EXECUTION_PROFILES,
    ExecutionPlan,
    ExecutionScopeError,
    FrozenCoreGate,
    assert_execution_scope,
)


def _plan(**overrides: object) -> ExecutionPlan:
    base: dict = dict(
        run_id="SAEA-E-000-smoke",
        execution_profile="baseline-reproduction",
        carrier_lock_key="earnings21-original",
        split_role="dev",
        split_identity_hash="a" * 64,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=600,
        protocol_hash="b" * 64,
    )
    base.update(overrides)
    return ExecutionPlan(**base)


@pytest.mark.parametrize("profile", ALLOWED_EXECUTION_PROFILES)
def test_stage2_profiles_are_accepted(profile):
    assert assert_execution_scope(profile) == profile


@pytest.mark.parametrize(
    "profile",
    [
        "paper-scale-confirmatory",
        "Paper-Scale-Confirmatory",
        "confirmatory",
        "large-scale-confirmatory-campaign",
        "production-scale",
        "paper",
    ],
)
def test_paper_scale_profiles_are_always_refused_with_the_gate_token(profile):
    with pytest.raises(ExecutionScopeError, match="OWNER_GO_AND_PAPER_EXECUTION_CONTRACT"):
        assert_execution_scope(profile)


@pytest.mark.parametrize(
    "profile",
    [
        "",
        "   ",
        None,
        7,
        "baseline_reproduction",
        "bounded-discovery-probe ",
        "BASELINE-REPRODUCTION",
        "stage2",
    ],
)
def test_unknown_or_forged_profiles_fail_closed(profile):
    with pytest.raises(ExecutionScopeError):
        assert_execution_scope(profile)


def test_model_touch_refuses_out_of_scope_plans_before_reading_any_receipt(tmp_path):
    gate = FrozenCoreGate(
        e0_receipt=tmp_path / "missing-e0.json",
        runtime_receipt=tmp_path / "missing-runtime.json",
        data_root=tmp_path,
        lock_path=tmp_path / "missing-lock.json",
        runtime_root=tmp_path,
        exposure_ledger=tmp_path / "missing-ledger.md",
        source_root=tmp_path,
    )
    # Scope refusal must precede receipt/ledger validation: with a forbidden profile
    # the error is ExecutionScopeError, not GateClosed-about-missing-files.
    with pytest.raises(ExecutionScopeError):
        gate.assert_model_touch_allowed(_plan(execution_profile="paper-scale-confirmatory"))
    # A model-free profile is legal for the repo but never authorizes a model touch.
    with pytest.raises(ExecutionScopeError):
        gate.assert_model_touch_allowed(_plan(execution_profile="model-free-check"))


def test_gate_refuses_execution_plan_subclasses(tmp_path):
    class NeuteredPlan(ExecutionPlan):
        def validate(self):  # a subclass could no-op every check
            return self

    gate = FrozenCoreGate(
        e0_receipt=tmp_path / "missing-e0.json",
        runtime_receipt=tmp_path / "missing-runtime.json",
        data_root=tmp_path,
        lock_path=tmp_path / "missing-lock.json",
        runtime_root=tmp_path,
        exposure_ledger=tmp_path / "missing-ledger.md",
        source_root=tmp_path,
    )
    plan = NeuteredPlan(
        run_id="SAEA-E-000-smoke",
        execution_profile="baseline-reproduction",
        carrier_lock_key="earnings21-original",
        split_role="dev",
        split_identity_hash="a" * 64,
        planned_model_calls=999999,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=600,
        protocol_hash="b" * 64,
    )
    with pytest.raises(ExecutionScopeError, match="exact contract type"):
        gate.assert_model_touch_allowed(plan)


def test_plan_budget_fields_must_be_finite_and_integral():
    with pytest.raises(ExecutionScopeError, match="finite positive integer"):
        _plan(planned_model_calls=10.5).validate()
    with pytest.raises(ExecutionScopeError, match="finite positive integer"):
        _plan(planned_speech_audio_seconds=600.0).validate()
    with pytest.raises(ExecutionScopeError, match="finite positive number"):
        _plan(planned_gpu_hours=float("nan")).validate()
    with pytest.raises(ExecutionScopeError, match="finite positive number"):
        _plan(planned_gpu_hours=float("inf")).validate()
    _plan(planned_gpu_hours=1.5).validate()


def test_plan_budget_fields_carry_no_numeric_ceiling_after_the_2026_08_06_amendment():
    """Owner amendment 2026-08-06 (SAEA-OWNER-AMENDMENT-2026-08-06-BUDGET-CAPS)
    retired the first-slice numeric caps (formerly <=3,000 calls / <=40 GPU-hours
    / <=72,000 speech-audio seconds) that ``ExecutionPlan.validate()`` used to
    enforce. A plan whose budget fields are merely finite/positive/integral now
    validates regardless of magnitude -- field-shape validation (the test above)
    is the only thing left to check here."""

    _plan(
        planned_model_calls=999999,
        planned_gpu_hours=4000.0,
        planned_speech_audio_seconds=9_999_999,
    ).validate()


# ---------------------------------------------------------------------------
# IMPORTANT 3 (external-threat-model review round 3): run_id/attempt_id must
# match the SAME filesystem-safe identifier pattern every downstream module
# (core.attempts, core.tracing, core.session, core.bundle) already enforces
# on its own authority -- before this, ExecutionPlan.validate() accepted ANY
# non-empty string, including one containing `../`, `/`, `\`, or a leading
# dot, letting a malicious run_id reach core.bundle.build_manifest (reachable
# pre-gate via core.driver.run_experiment_bundled's ABORTED-manifest path)
# and write a manifest OUTSIDE its own run directory.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_run_id",
    [
        "../../VICTIM/pwned",
        "../evil",
        "a/b",
        "a\\b",
        "/absolute",
        ".leadingdot",
        "-leadingdash",
        "",
        "   ",
    ],
)
def test_plan_run_id_rejects_path_shaped_values(bad_run_id):
    with pytest.raises(ExecutionScopeError, match="run_id"):
        _plan(run_id=bad_run_id).validate()


@pytest.mark.parametrize(
    "bad_attempt_id",
    ["../evil", "a/b", "a\\b", "/absolute", ".leadingdot", ""],
)
def test_plan_attempt_id_rejects_path_shaped_values_when_present(bad_attempt_id):
    with pytest.raises(ExecutionScopeError, match="attempt_id"):
        _plan(attempt_id=bad_attempt_id).validate()


def test_plan_attempt_id_none_is_still_legal():
    """attempt_id stays optional -- a missing attempt_id (e0's frozen dry-run
    construction) is not itself a validation failure; refusal for a real
    model touch happens at FrozenCoreAdapter construction instead."""

    _plan(attempt_id=None).validate()


def test_plan_legitimate_run_id_and_attempt_id_still_validate():
    _plan(run_id="SAEA-E-000-smoke", attempt_id="attempt-0001").validate()
