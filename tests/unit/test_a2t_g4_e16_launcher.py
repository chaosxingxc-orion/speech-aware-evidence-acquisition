"""Zero-contact tests for the G4 executable-microground E16 launcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (
    Audio2ToolSample,
)
from speech_aware_evidence_acquisition.rails.obs import AudioRef


REPO = Path(__file__).resolve().parents[2]
LAUNCHER = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g4-executable-microground-e16/launcher/"
    "launch_a2t_g4_e16.py"
)


def _launcher():
    name = "test_a2t_g4_e16_launcher_module"
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


def test_selected_surface_is_the_frozen_g3_two_per_tier_control() -> None:
    launcher = _launcher()

    assert len(launcher.SELECTED_IDS) == 16
    assert len(set(launcher.SELECTED_IDS)) == 16
    assert launcher.SELECTED_IDS == tuple(sorted(launcher.SELECTED_IDS))
    assert launcher._validate_selected_ids(
        {sample_id: sample_id.split(":", 1)[0] for sample_id in launcher.SELECTED_IDS}
    ) == launcher.SELECTED_IDS
    assert {
        tier: sum(sample_id.startswith(f"{tier}:") for sample_id in launcher.SELECTED_IDS)
        for tier in launcher.EXPECTED_TIERS
    } == {tier: 2 for tier in launcher.EXPECTED_TIERS}

    drifted = dict(
        (sample_id, sample_id.split(":", 1)[0])
        for sample_id in launcher.SELECTED_IDS[:-1]
    )
    with pytest.raises(RuntimeError, match="frozen G3 selected16"):
        launcher._validate_selected_ids(drifted)


def test_execution_plan_is_exactly_sixteen_single_contact_use_requests() -> None:
    launcher = _launcher()
    plan = launcher._execution_plan(
        "attempt-20260902t000000z-g4-e16", protocol_hash="a" * 64
    )

    assert plan.run_id == launcher.RUN_ID
    assert plan.execution_profile == "bounded-discovery-probe"
    assert plan.carrier_lock_key == "audio2tool"
    assert plan.split_role == "discovery"
    assert plan.split_identity_hash == launcher.SELECTED_RUN_SHA256
    assert plan.planned_model_calls == 16
    assert plan.planned_speech_audio_seconds == launcher.PLANNED_AUDIO_SECONDS
    assert plan.protocol_hash == "a" * 64
    assert launcher.SLOT_COUNT == 2
    assert launcher.QUEUE_DEPTH == 4
    assert launcher.MAX_TOKENS == 1024
    assert launcher.MAX_CONTACTS == 1
    assert launcher.REPAIR_CONTACTS == 0
    assert launcher.RETRIES == 0
    assert launcher.JITTER_TESTING is False


def test_routes_once_per_observation_and_binds_packet_and_trace_hashes() -> None:
    launcher = _launcher()
    calls: list[str] = []

    def route(_corpus, *, observation, max_utf8_bytes):
        calls.append(observation)
        index = len(calls)
        return SimpleNamespace(
            packet=f"packet {index}",
            packet_sha256=f"{index:064x}",
            trace_sha256=f"{index + 100:064x}",
            candidate_names=(f"tool{index}",),
            packet_utf8_bytes=8,
        )

    observations = {
        sample_id: f"English observation {index}."
        for index, sample_id in enumerate(launcher.SELECTED_IDS)
    }
    routes, route_sha = launcher._route_selected(
        object(), observations, route_fn=route
    )

    assert len(calls) == 16
    assert len(routes) == 16
    assert len(route_sha) == 64
    assert tuple(routes) == launcher.SELECTED_IDS
    assert routes[launcher.SELECTED_IDS[0]].packet == "packet 1"


def test_adapter_preflight_binds_prompt_cap_and_original_runtime_samples() -> None:
    launcher = _launcher()
    samples = _samples(launcher)
    observations = {
        sample.sample_id: f"English observation for row {index}."
        for index, sample in enumerate(samples)
    }
    routes = {
        sample.sample_id: SimpleNamespace(packet=f"packet for row {index}")
        for index, sample in enumerate(samples)
    }

    adapter, prompt_report = launcher._build_adapter(
        samples, observations, routes, prompt_utf8_byte_cap=24_000
    )

    assert adapter.load_split(launcher.G4_SCREEN_SPLIT_ID) == tuple(
        sorted(samples, key=lambda sample: sample.sample_id)
    )
    assert prompt_report["count"] == 16
    assert prompt_report["max_utf8_bytes"] <= 24_000
    assert set(prompt_report["by_sample"]) == set(launcher.SELECTED_IDS)

    with pytest.raises(RuntimeError, match="prompt-size cap"):
        launcher._build_adapter(
            samples, observations, routes, prompt_utf8_byte_cap=10
        )


def test_official_score_plan_is_one_whole_manifest_job() -> None:
    launcher = _launcher()
    plan = launcher._validate_official_score_plan(launcher.OFFICIAL_SCORE_PLAN)

    assert plan == {
        "workers": 1,
        "operation": "finalize",
        "dataset_sharding": False,
        "shard_metric_averaging": False,
        "network_jitter_testing": False,
        "jobs": [
            {
                "job_id": "g4-e16",
                "input": "complete 16-row run manifest",
                "row_count": 16,
            }
        ],
    }

    drifted = json.loads(json.dumps(launcher.OFFICIAL_SCORE_PLAN))
    drifted["jobs"].append(dict(drifted["jobs"][0]))
    with pytest.raises(RuntimeError, match="one whole-manifest"):
        launcher._validate_official_score_plan(drifted)


def test_preflight_refuses_any_unbound_builder_config_or_route_constant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = _launcher()
    monkeypatch.setattr(launcher, "CORPUS_BUILD_SHA256", None)
    monkeypatch.setattr(launcher, "COMPOSED_CONFIG_SHA256", None)
    monkeypatch.setattr(launcher, "ROUTE_SET_SHA256", None)
    missing = launcher._unbound_requirements()

    assert "CORPUS_BUILD_SHA256" in missing
    assert "COMPOSED_CONFIG_SHA256" in missing
    assert "ROUTE_SET_SHA256" in missing
    with pytest.raises(RuntimeError, match="G4 launcher bindings are incomplete"):
        launcher._static_preflight(Path("/unused"))


def test_main_separates_zero_contact_preflight_from_explicit_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    launcher = _launcher()
    context = {
        "commit": "b" * 40,
        "selected_ids": launcher.SELECTED_IDS,
        "route_set_sha256": "c" * 64,
        "prompt_report": {"max_utf8_bytes": 1234},
        "execution_plan_template": launcher._execution_plan(
            "attempt-preflight-g4-e16", protocol_hash="d" * 64
        ),
    }
    calls: list[tuple[str, Path]] = []
    monkeypatch.setattr(launcher, "data_root", lambda: Path("/fixed/data"))
    monkeypatch.setattr(launcher, "_static_preflight", lambda root: context)
    monkeypatch.setattr(
        launcher, "_launch", lambda root: calls.append(("run", root)) or {"ok": True}
    )

    assert launcher.main(["--preflight-only"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["contacts"] == {
        "gold": 0,
        "model": 0,
        "network": 0,
        "retriever": 0,
        "scorer": 0,
        "tokenizer": 0,
    }
    assert payload["samples"] == 16
    assert payload["official_score_manifests"] == 1
    assert payload["planned_model_calls"] == 16
    assert calls == []

    assert launcher.main(["--run"]) == 0
    assert calls == [("run", Path("/fixed/data"))]

    with pytest.raises(SystemExit):
        launcher.main([])
