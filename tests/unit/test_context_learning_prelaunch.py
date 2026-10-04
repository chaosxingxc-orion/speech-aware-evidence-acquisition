"""Bind deterministic context families before any flight contact."""

import json
from types import SimpleNamespace
import pytest
from test_flight_registration_check import gate
from test_system_context_learning import setup, pin
from speech_aware_evidence_acquisition.rails import system_text_policy
from speech_aware_evidence_acquisition.core import config
from speech_aware_evidence_acquisition.rails.hashing import content_hash


@pytest.mark.parametrize(
    "mutation",
    [
        None,
        "attempt",
        "bundle",
        "config",
        "missing-member",
        "protocol",
        "registration-hash",
        "ambiguous",
    ],
)
def test_exact_context_registration_prelaunch(tmp_path, monkeypatch, mutation):
    setup(tmp_path, monkeypatch)
    recipe = json.loads((tmp_path / "recipe.json").read_text())
    registration = json.loads((tmp_path / "registration.json").read_text())
    member = registration["member_bindings"]["context-0"]
    cell = dict(
        model_fragment="m",
        dataset_fragment="d",
        baseline_fragment="b",
        attempt_id=member["attempt_id"],
        system_text_policy_binding={"bundle_id": member["bundle_id"]},
    )
    effective = {
        "system_search_measurement": recipe["measurement_profile"],
        "serving_slots": 4,
        "serving_slot_tokens": 24576,
        "native_episode": {},
        "decoding_params": {"max_tokens": 512},
        "server_args": ["-np", "4", "-c", "98304"],
    }
    composed = SimpleNamespace(values=effective, config_hash=member["config_hash"])
    monkeypatch.setattr(config, "compose", lambda *a, **k: composed)
    monkeypatch.setattr(
        system_text_policy, "verify_system_text_binding", lambda *a, **k: None
    )
    if mutation in ("attempt", "bundle", "config"):
        member[
            {"attempt": "attempt_id", "bundle": "bundle_id", "config": "config_hash"}[
                mutation
            ]
        ] = "1" * 64
    elif mutation == "missing-member":
        del registration["member_bindings"]["context-3"]
    elif mutation == "protocol":
        protocol = json.loads((tmp_path / "protocol.json").read_text())
        protocol["K"] = 8
        registration["protocol"] = pin(tmp_path, "protocol.json", protocol)
    elif mutation == "ambiguous":
        recipe["system_panel_registration"] = recipe["context_learning_registration"]
    registration["registration_sha256"] = content_hash(
        {k: v for k, v in registration.items() if k != "registration_sha256"}
    )
    if mutation == "registration-hash":
        registration["registration_sha256"] = "1" * 64
    recipe["context_learning_registration"] = pin(
        tmp_path, "registration.json", registration
    )
    report = SimpleNamespace(run_id="run-context-0", experiment="e", findings=[])
    gate._check_system_text_binding(
        report, cell, {}, recipe, tmp_path, tmp_path / "data"
    )
    assert bool(report.findings) == (mutation is not None)


@pytest.mark.parametrize("mixed", [False, True])
def test_analysis_order_is_not_runtime_admission_order(tmp_path, mixed):
    from test_system_search_measurement import measured_fixture, timing
    from speech_aware_evidence_acquisition.rails.system_search_measurement import (
        measured_rows,
    )
    from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError

    _, protocol, feedback, evaluation = measured_fixture(tmp_path)
    d = feedback.as_json()
    ids = [g["sample_id"] for g in d["feedback"]["groups"]]
    members = list(d["summaries"])
    bindings = {cid: {"bundle_id": content_hash(cid)} for cid in members}
    for i, cid in enumerate(members):
        d["summaries"][cid]["sample_timing"] = timing(
            ids if mixed and i == 0 else ids[::-1]
        )
    if mixed:
        with pytest.raises(PolicyError, match="order"):
            measured_rows(d, members, bindings, profile=protocol["measurement_profile"])
    else:
        assert len(
            measured_rows(d, members, bindings, profile=protocol["measurement_profile"])
        ) == len(members)


def test_timing_summary_preserves_actual_first_not_analysis_first():
    from speech_aware_evidence_acquisition.rails.system_text_feedback import (
        _summarize_official_sample_timing,
    )

    def row(sid, index, seconds):
        return {
            "sample_timing_record": dict(
                schema="saea-sample-execution-timing-v1",
                sample_id=sid,
                execution_unit_id=None,
                admission_index=index,
                expected_samples=2,
                slot_count=4,
                queue_depth=4,
                batch_started_ns=0,
                admitted_ns=index * 1000000000,
                finished_ns=(index + seconds) * 1000000000,
                status="completed",
                error_type=None,
            )
        }

    rows = {"b": row("b", 1, 7), "a": row("a", 0, 20)}
    report = _summarize_official_sample_timing(rows, ["b", "a"])
    assert report["first_admitted_sample"]["sample_id"] == "a"
    assert report["excluding_first"]["mean_seconds"] == 7
