"""Keep heuristic preparation distinct from exact native request admission."""

from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight import runtime as module
from speech_aware_evidence_acquisition.core.preparation import PreparationError


def _runtime(monkeypatch, **changes):
    values = {
        "policy": "phase-native-candidates-review-revise-v1",
        "native_episode": {"context_fit_policy": "raise"},
        "native_contact_fit": {"run_id": "fit-run", "attempt_id": "fit-attempt", "contact_cap": 44},
        "preflight_budget_mode": "defer-to-native-contact-fit",
    }
    values.update(changes)
    runtime = object.__new__(module.FlightRuntime)
    runtime._composed = SimpleNamespace(values=values)
    runtime._adapter = SimpleNamespace(
        serving_geometry=lambda: {"slot_tokens": 4096},
        assemble_prompt=lambda *_: ({"role": "user", "content": "speech"},),
    )
    runtime._token_counter = module._default_token_counter
    runtime._speech_tokens_per_second = 13
    runtime._completion_token_ceiling = lambda: 512
    runtime._obs_policy_names = lambda: ()
    runtime.uses_speech_feature_packets = lambda: True
    runtime.shows_construction_targets = lambda: False
    runtime.execution_unit_roster = lambda: None
    phases = ("perception", "solver", "reviewer", "planner")
    # This envelope is deliberately much larger than any physical slot.
    runtime._phase_prompt_payloads = lambda *_: {phase: b"x" * 100000 for phase in phases}
    monkeypatch.setattr(module, "default_phase_program", lambda _: SimpleNamespace(
        stop_rule="native-role-episode", max_contacts=11, phase_names=lambda: phases,
    ))
    return runtime, (SimpleNamespace(sample_id="sample", audio_seconds=1.0),)


def test_declared_heuristic_defer_records_overflow_without_certifying_capacity(monkeypatch):
    runtime, samples = _runtime(monkeypatch)
    receipts = runtime._assess_prompt_budget(samples)
    assert len(receipts) == 4
    for row in receipts:
        assert row["decision"] == "COMPACT_REQUIRED"
        assert row["physical_margin_tokens"] < 0
        assert row["capacity_verified"] is False
        assert row["estimate_only"] is True
        assert row["enforcement"] == "native-contact-fit-before-each-request"
    assert runtime._context_fit_policy() == "raise"


def test_deferral_is_valid_under_compact_or_abstain(monkeypatch):
    """2026-10-12: the exact per-contact gate compacts or abstains at the wire, so the placeholder estimate is recorded, not enforced."""
    runtime, samples = _runtime(monkeypatch, native_episode={"context_fit_policy": "compact-or-abstain"})
    receipts = runtime._assess_prompt_budget(samples)
    assert len(receipts) == 4
    for row in receipts:
        assert row["decision"] == "COMPACT_REQUIRED" and row["physical_margin_tokens"] < 0
        assert row["estimate_only"] is True and row["capacity_verified"] is False


def test_deferral_refuses_an_unknown_fit_policy(monkeypatch):
    from speech_aware_evidence_acquisition.rails.context_fit import ContextFitError

    runtime, samples = _runtime(monkeypatch, native_episode={"context_fit_policy": "ignore"})
    with pytest.raises((module.FlightRuntimeError, ContextFitError), match="context_fit_policy"):
        runtime._assess_prompt_budget(samples)


def test_omitted_mode_preserves_legacy_overflow_refusal(monkeypatch):
    runtime, samples = _runtime(monkeypatch)
    runtime._composed.values.pop("preflight_budget_mode")
    with pytest.raises(module.FlightRuntimeError, match="prompt budget"):
        runtime._assess_prompt_budget(samples)


@pytest.mark.parametrize("change", [
    {"native_contact_fit": None},
    {"native_contact_fit": {"run_id": "fit-run"}},
    {"native_episode": None},
    {"policy": "fixed"},
    {"preflight_budget_mode": "ignore-overflow"},
])
def test_deferral_refuses_missing_or_incompatible_exact_gate(monkeypatch, change):
    runtime, samples = _runtime(monkeypatch, **change)
    runtime._phase_prompt_payloads = lambda *_: {}
    with pytest.raises((module.FlightRuntimeError, PreparationError)):
        runtime._assess_prompt_budget(samples)


def test_deferral_cannot_override_a_supplied_counter(monkeypatch):
    runtime, samples = _runtime(monkeypatch)
    runtime._token_counter = lambda _: 25000
    with pytest.raises(module.FlightRuntimeError, match="heuristic"):
        runtime._assess_prompt_budget(samples)
