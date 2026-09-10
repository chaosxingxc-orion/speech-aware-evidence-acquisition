"""Keep all CPU request preparation ahead of the first service contact."""
import json
from types import SimpleNamespace
import pytest

from speech_aware_evidence_acquisition.core.flight.campaign import CampaignError
from speech_aware_evidence_acquisition.core.flight.fit_batch import coordinate_fit_batch
from speech_aware_evidence_acquisition.core.preparation import PreparationError, canonical_bytes, prepare_artifact


def setup_batch(tmp_path, *, fail_materialize=None, fail_fit=None, identity_drift=False):
    events = []
    flights = [
        SimpleNamespace(
            run_id=str(i), attempt_id="attempt",
            preparation_context=lambda i=i: {"required_identity": {"weights": i if identity_drift else 0}},
        ) for i in range(3)
    ]
    jobs = [
        {"output": tmp_path / f"{i}.json", "contact_cap": 3, "model_fragment": "frozen"}
        for i in range(3)
    ]
    def materializer(flight):
        events.append(("materialize", flight.run_id))
        if flight.run_id == fail_materialize:
            raise PreparationError("CPU preparation failed")
        return SimpleNamespace(inputs_bytes=canonical_bytes({"run_id": flight.run_id}))
    def coordinator(flight, **kwargs):
        events.append(("contact", flight.run_id))
        assert kwargs["hold_wrapper_foreground"] is False
        prepared = kwargs["fit_runner"].keywords["prepared_phase"]
        return prepare_artifact(
            kwargs["output"], kind="request-fit",
            inputs=json.loads(prepared.inputs_bytes),
            producer=lambda: {"every_request_fits": flight.run_id != fail_fit},
            contact_class="tokenizer",
        )
    options = dict(
        repo_root=tmp_path, data_root=tmp_path, runtime_root=tmp_path,
        owner="root", expected_session_id="resident",
        materializer=materializer, coordinator=coordinator,
    )
    return flights, jobs, events, options


def test_batch_materializes_all_then_fits_serially(tmp_path):
    flights, jobs, events, options = setup_batch(tmp_path)
    result = coordinate_fit_batch(flights, jobs, **options)
    assert events == [("materialize", str(i)) for i in range(3)] + [
        ("contact", str(i)) for i in range(3)
    ]
    assert len(result["results"]) == 3


def test_cpu_failure_causes_zero_service_contacts(tmp_path):
    flights, jobs, events, options = setup_batch(tmp_path, fail_materialize="2")
    with pytest.raises(PreparationError, match="CPU"):
        coordinate_fit_batch(flights, jobs, **options)
    assert all(stage == "materialize" for stage, _ in events)


def test_failed_fit_stops_dispatch_and_preserves_completed_artifacts(tmp_path):
    flights, jobs, events, options = setup_batch(tmp_path, fail_fit="1")
    with pytest.raises(PreparationError, match="does not fit"):
        coordinate_fit_batch(flights, jobs, **options)
    assert ("contact", "2") not in events
    assert jobs[0]["output"].is_file() and jobs[1]["output"].is_file()
    assert not jobs[2]["output"].exists()


@pytest.mark.parametrize("defect", ["identity", "duplicate", "outside", "cap"])
def test_batch_invalid_plan_refused_before_preparation(tmp_path, defect):
    flights, jobs, events, options = setup_batch(tmp_path, identity_drift=defect == "identity")
    if defect == "duplicate":
        jobs[1]["output"] = jobs[0]["output"]
    if defect == "outside":
        jobs[0]["output"] = tmp_path.parent / "escape.json"
    if defect == "cap":
        jobs[0]["contact_cap"] = True
    with pytest.raises(CampaignError):
        coordinate_fit_batch(flights, jobs, **options)
    assert not events


def test_module_entry_runs_argument_parser_without_model_contact():
    """The public module entry must execute main instead of silently exiting."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    env = dict(os.environ, PYTHONPATH=str(root / "src"), PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(
        [sys.executable, "-m", "speech_aware_evidence_acquisition.core.flight.fit_batch", "--help"],
        cwd=root, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "--expected-session-id" in result.stdout
    assert "--plan" in result.stdout
