"""Zero-contact tests for the G4 structured-state SE16 launcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from speech_aware_evidence_acquisition.rails.adapters.audio2tool import Audio2ToolSample
from speech_aware_evidence_acquisition.rails.obs import AudioRef


REPO = Path(__file__).resolve().parents[2]
LAUNCHER = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g4-executable-microground-se16/launcher/"
    "launch_a2t_g4_se16.py"
)


def _launcher():
    name = "test_a2t_g4_se16_launcher_module"
    spec = importlib.util.spec_from_file_location(name, LAUNCHER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _samples(launcher) -> tuple[Audio2ToolSample, ...]:
    return tuple(
        Audio2ToolSample(
            sample_id=sample_id,
            audio_ref=AudioRef(
                path=f"audio/{index:02d}.wav", sha256=f"{index + 1:064x}"
            ),
            audio_seconds=1.0,
            media_relpath=f"audio/{index:02d}.wav",
        )
        for index, sample_id in enumerate(launcher.SELECTED_IDS)
    )


def _observations(launcher) -> dict[str, str]:
    return {
        sample_id: f"Please execute action number {index}."
        for index, sample_id in enumerate(launcher.SELECTED_IDS, start=1)
    }


def test_execution_plan_and_verified_split_use_carrier_prefixed_run_identity() -> None:
    launcher = _launcher()
    plan = launcher._execution_plan("attempt-20260902t000000z-g4-se16", "a" * 64)
    split = launcher._verified_split()

    assert plan.run_id == launcher.RUN_ID
    assert plan.execution_profile == "bounded-discovery-probe"
    assert plan.carrier_lock_key == "audio2tool"
    assert plan.split_role == "discovery"
    assert plan.split_identity_hash == launcher.SELECTED_RUN_SHA256
    assert plan.planned_model_calls == 16
    assert split.identity_hash == launcher.SELECTED_RUN_SHA256
    assert split.ids == launcher.SELECTED_IDS
    assert split.prefixed_ids == tuple(
        f"audio2tool/{sample_id}" for sample_id in launcher.SELECTED_IDS
    )
    assert launcher.STATE_SET_SHA256 == (
        "2e42e636e36d7e15dcab9a6c7e3e450bd38a930b02f1e7270d4a617d8c45abad"
    )
    assert launcher.ROUTE_SET_SHA256 == (
        "2b2d8b444ae67edd06abf7a3d59bab09d74db3e21b242246a392569f4ce5236c"
    )
    assert launcher.EXPERIMENT_CONFIG_SHA256 == (
        "f0b942d05121f14ee433371c730b77d155fb5ae0cfdb80b5ef110f862bcbacf7"
    )
    assert launcher.COMPOSED_CONFIG_SHA256 == (
        "04f02dfd3c620351799947ef6582ef5b5064a80591bca07fc6519a717887d8f9"
    )
    assert launcher.PROTOCOL_SHA256 == (
        "041b87305f8357ffb19487ac3f8a76a7da78f37fdad0ea4dca4399c13b733cf4"
    )


def test_organizer_builds_exactly_sixteen_bounded_states_and_source_free_receipt() -> None:
    launcher = _launcher()
    states, receipt = launcher._organize_selected(_observations(launcher))

    assert tuple(states) == launcher.SELECTED_IDS
    assert receipt["observation_count"] == 16
    assert receipt["state_count"] == 16
    assert receipt["source_observations_rendered"] == 0
    assert all(len(text.encode("utf-8")) <= 8192 for text in states.values())
    rendered = json.dumps(receipt, sort_keys=True)
    assert not any(sample_id in rendered for sample_id in launcher.SELECTED_IDS)
    assert not any(text in rendered for text in _observations(launcher).values())
    assert receipt["state_set_sha256"] == launcher._state_set_sha256(states)


def test_router_consumes_structured_states_once_and_freezes_route_set() -> None:
    launcher = _launcher()
    states, _receipt = launcher._organize_selected(_observations(launcher))
    calls: list[dict[str, object]] = []

    def route(_corpus, **kwargs):
        calls.append(kwargs)
        index = len(calls)
        return SimpleNamespace(
            packet=f"packet {index}",
            packet_sha256=f"{index:064x}",
            trace_sha256=f"{index + 100:064x}",
            candidate_names=(f"tool{index}",),
            packet_utf8_bytes=8,
        )

    routes, route_set = launcher._route_selected(object(), states, route_fn=route)

    assert len(calls) == 16
    assert all("structured_state" in call and "observation" not in call for call in calls)
    assert all(call["max_utf8_bytes"] == 16_384 for call in calls)
    assert tuple(routes) == launcher.SELECTED_IDS
    assert len(route_set) == 64


def test_adapter_is_se_phase_and_enforces_prompt_cap() -> None:
    launcher = _launcher()
    samples = _samples(launcher)
    states, _receipt = launcher._organize_selected(_observations(launcher))
    routes = {
        sample_id: SimpleNamespace(packet=f"packet for {sample_id}")
        for sample_id in launcher.SELECTED_IDS
    }

    adapter, report = launcher._build_adapter(samples, states, routes)

    assert adapter._phase == launcher.G4_MICROGROUND_SE_PHASE
    assert report["count"] == 16
    assert report["max_utf8_bytes"] <= 24_000
    with pytest.raises(RuntimeError, match="prompt-size cap"):
        launcher._build_adapter(samples, states, routes, prompt_utf8_byte_cap=10)


def test_official_score_plan_is_one_single_process_whole_manifest_job() -> None:
    launcher = _launcher()
    plan = launcher._validate_official_score_plan(launcher.OFFICIAL_SCORE_PLAN)

    assert plan["workers"] == 1
    assert plan["processes_per_job"] == 1
    assert plan["jobs"] == [
        {
            "job_id": "g4-se16",
            "input": "complete 16-row run manifest",
            "row_count": 16,
        }
    ]
    drifted = json.loads(json.dumps(plan))
    drifted["jobs"].append(dict(drifted["jobs"][0]))
    with pytest.raises(RuntimeError, match="one whole-manifest"):
        launcher._validate_official_score_plan(drifted)


def test_run_phase_uses_fixed_boundary_and_requires_exactly_sixteen_contacts() -> None:
    launcher = _launcher()
    samples = _samples(launcher)
    states, _receipt = launcher._organize_selected(_observations(launcher))
    routes = {
        sample_id: SimpleNamespace(packet=f"packet for {sample_id}")
        for sample_id in launcher.SELECTED_IDS
    }
    adapter, _report = launcher._build_adapter(samples, states, routes)
    calls: list[dict[str, object]] = []
    summary = SimpleNamespace(
        results=tuple(
            SimpleNamespace(
                sample_id=sample_id,
                contacts=(SimpleNamespace(),),
                final_response_text="[]",
            )
            for sample_id in launcher.SELECTED_IDS
        )
    )

    def run_phase(**kwargs):
        calls.append(kwargs)
        return summary

    result = launcher._run_phase(
        root=Path("/data"),
        plan=object(),
        adapter=adapter,
        client=object(),
        snapshot=object(),
        packet_bindings={sample_id: {} for sample_id in launcher.SELECTED_IDS},
        trace_sink=object(),
        run_phase=run_phase,
    )

    assert result is summary
    assert len(calls) == 1
    assert calls[0]["adapter"] is adapter
    assert sum(len(row.contacts) for row in result.results) == 16


def test_preflight_is_zero_contact_and_main_requires_explicit_mode(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    launcher = _launcher()
    context = {
        "commit": "b" * 40,
        "selected_ids": launcher.SELECTED_IDS,
        "state_set_sha256": "c" * 64,
        "route_set_sha256": "d" * 64,
        "prompt_report": {"max_utf8_bytes": 1234},
        "state_receipt_path": Path("/data/state-receipt.json"),
    }
    calls: list[Path] = []
    monkeypatch.setattr(launcher, "data_root", lambda: Path("/fixed/data"))
    monkeypatch.setattr(launcher, "_static_preflight", lambda root: context)
    monkeypatch.setattr(
        launcher, "_launch", lambda root: calls.append(root) or {"status": "SEALED"}
    )

    assert launcher.main(["--preflight-only"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["contacts"] == {
        "gold": 0,
        "model": 0,
        "network": 0,
        "retriever_service": 0,
        "scorer": 0,
        "tokenizer": 0,
    }
    assert payload["samples"] == 16
    assert calls == []

    assert launcher.main(["--run"]) == 0
    assert calls == [Path("/fixed/data")]
    with pytest.raises(SystemExit):
        launcher.main([])
