"""Model-free tests for the executable-ground qualification launcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


REPO = Path(__file__).resolve().parents[2]
LAUNCHER = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-executable-ground-qualification-104-v1/launcher/"
    "launch_ground_qualification.py"
)


def _launcher():
    name = "test_a2t_executable_ground_qualification_launcher_module"
    spec = importlib.util.spec_from_file_location(name, LAUNCHER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _roster() -> dict[str, object]:
    items = [
        {
            "sample_id": f"tier{tier}_kind:{index:06d}",
            "tier": f"tier{tier}_kind",
            "packet_id": f"tier{tier}_kind/{index:06d}",
            "audio_sha256": f"{tier:x}" * 64,
            "media_relpath": f"datasets/audio2tool/tier{tier}/{index}.wav",
        }
        for tier in range(1, 9)
        for index in range(13)
    ]
    return {
        "count": 104,
        "audio_seconds_total": 543.107,
        "split_identity_hash": (
            "c6bb080bb264733087b3da352fe930702ec6509bc02e6a639b0f4c30c5017dac"
        ),
        "run_identity_hash": (
            "fbd4addd541ff29214cbff7c35564b15f27e2fb7f438202b79d694b1c5961d4b"
        ),
        "items": items,
    }


def test_execution_plan_encodes_the_registered_discovery_budget() -> None:
    launcher = _launcher()
    plan = launcher._execution_plan("attempt-20260902t000000z-groundqual")
    assert plan.run_id == launcher.RUN_ID
    assert plan.execution_profile == "bounded-discovery-probe"
    assert plan.carrier_lock_key == "audio2tool"
    assert plan.split_role == "discovery"
    assert plan.split_identity_hash == launcher.SPLIT_IDENTITY_SHA256
    assert plan.planned_model_calls == 230
    assert plan.planned_gpu_hours == 0.7
    assert plan.planned_speech_audio_seconds == 1300
    assert plan.protocol_hash == launcher.PROTOCOL_SHA256


def test_roster_requires_exactly_thirteen_rows_in_each_of_eight_tiers() -> None:
    launcher = _launcher()
    validated = launcher._validate_roster(_roster())
    assert len(validated["sample_ids"]) == 104
    assert validated["tier_counts"] == {
        f"tier{tier}_kind": 13 for tier in range(1, 9)
    }

    drifted = _roster()
    drifted["items"][0]["sample_id"] = drifted["items"][1]["sample_id"]
    with pytest.raises(RuntimeError, match="unique sample"):
        launcher._validate_roster(drifted)


def test_server_geometry_preserves_two_32768_token_slots() -> None:
    launcher = _launcher()
    assert launcher.GGUF_DECLARED_CONTEXT_TOKENS == 65536
    assert launcher.SERVER_CONTEXT_TOKENS == 65536
    assert launcher.SERVER_SLOT_COUNT == 2
    assert launcher.CONTEXT_TOKENS_PER_SLOT == 32768
    values = {
        "server_args": ["-c", "65536", "-np", "2"],
        "profile_slot_count": 2,
        "decoding_params": {
            "temperature": 0,
            "seed": 20260803,
            "max_tokens": 1024,
            "id_slot": "per-sample",
        },
    }
    assert launcher._validate_server_geometry(values) == {
        "context_tokens": 65536,
        "slot_count": 2,
        "context_tokens_per_slot": 32768,
    }
    values["server_args"] = ["-c", "65536", "-np", "4"]
    with pytest.raises(RuntimeError, match="two 32768-token slots"):
        launcher._validate_server_geometry(values)


def test_official_score_plan_is_two_complete_manifests_without_shards() -> None:
    launcher = _launcher()
    plan = launcher._validate_official_score_plan(launcher.OFFICIAL_SCORE_PLAN)
    assert plan["workers"] == 2
    assert plan["operation"] == "finalize"
    assert plan["dataset_sharding"] is False
    assert plan["shard_metric_averaging"] is False
    assert plan["network_jitter_testing"] is False
    assert [job["row_count"] for job in plan["jobs"]] == [104, 104]

    drifted = json.loads(json.dumps(launcher.OFFICIAL_SCORE_PLAN))
    drifted["jobs"][0]["input"] = "dataset shard"
    with pytest.raises(RuntimeError, match="complete 104-row manifest"):
        launcher._validate_official_score_plan(drifted)


def test_preflight_only_never_enters_full_launch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    launcher = _launcher()
    sentinel = {
        "commit": "a" * 40,
        "sample_ids": tuple(f"sample-{index}" for index in range(104)),
        "execution_plan": launcher._execution_plan(
            "attempt-20260902t000000z-groundqualpre"
        ),
    }
    monkeypatch.setattr(launcher, "data_root", lambda: Path("/fixed/data"))
    monkeypatch.setattr(launcher, "_static_preflight", lambda root: sentinel)

    def forbidden_launch(root: Path):
        raise AssertionError(f"full launch was entered for {root}")

    monkeypatch.setattr(launcher, "_launch", forbidden_launch)
    assert launcher.main(["--preflight-only"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "contacts": {
            "gold": 0,
            "model": 0,
            "network": 0,
            "retriever": 0,
            "scorer": 0,
            "tokenizer": 0,
        },
        "official_score_manifests": 2,
        "official_score_workers": 2,
        "preflight": "passed",
        "run_id": launcher.RUN_ID,
        "samples": 104,
        "study_commit": "a" * 40,
    }


def test_full_launch_is_a_contact_closed_scaffold() -> None:
    launcher = _launcher()
    with pytest.raises(RuntimeError, match="contact-closed scaffold"):
        launcher._launch(Path("/fixed/data"))
