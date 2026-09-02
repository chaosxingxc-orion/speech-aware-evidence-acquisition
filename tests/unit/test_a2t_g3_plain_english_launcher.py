from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest


REPO = Path(__file__).resolve().parents[2]
LAUNCHER = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g3-plain-english-v1/launcher/launch_a2t_g3.py"
)


def _launcher():
    name = "test_a2t_g3_plain_english_launcher_module"
    spec = importlib.util.spec_from_file_location(name, LAUNCHER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _items():
    tiers = (
        "tier1_direct",
        "tier2_parametric",
        "tier3_multi_intent",
        "tier4_implicit",
        "tier5_needle",
        "tier6_correction",
        "tier7_multiturn",
        "tier8_intent_blending",
    )
    return [
        {
            "sample_id": f"{tier}:{index:06d}",
            "tier": tier,
            "query_block": f"{tier}:query-{index:05d}",
        }
        for tier in tiers
        for index in range(5)
    ]


def _scores(items, *, exact_fail=(), tool_fail=(), slot_f1=0.95):
    exact_fail = set(exact_fail)
    tool_fail = set(tool_fail)
    per_sample = [
        {
            "sample_id": item["sample_id"],
            "tier": item["tier"],
            "exact_match": float(item["sample_id"] not in exact_fail),
            "tool_accuracy": float(item["sample_id"] not in tool_fail),
            "parsed": True,
        }
        for item in items
    ]
    return {
        "a2t-toolcall": {
            "per_sample": per_sample,
            "aggregate": {
                "samples": 40,
                "exact_match": sum(row["exact_match"] for row in per_sample) / 40,
                "tool_accuracy": sum(row["tool_accuracy"] for row in per_sample) / 40,
                "slot_f1": slot_f1,
                "per_tier": {},
            },
        }
    }


def test_launcher_pins_config_protocol_artifacts_and_global_budget() -> None:
    launcher = _launcher()
    assert launcher.COMPOSED_CONFIG_SHA256.startswith("f258c7")
    assert launcher.PROTOCOL_SHA256.startswith("748492")
    assert launcher.ROSTER_SHA256.startswith("179535")
    assert launcher.MEDIA_SHA256.startswith("72cc")
    assert launcher.BINDING_SHA256.startswith("0bfddeb")
    assert launcher.PROMOTION_SHA256.startswith("77b1b")
    assert launcher.CARD_BUILD_SHA256.startswith("3139")
    assert launcher.CORPUS_FILE_SHA256.startswith("6c9a")
    assert launcher.CORPUS_BOUND_SHA256.startswith("95af")
    assert launcher.CONSTRUCTION_ACCESS_SHA256.startswith("1a294")

    for phase in launcher.PHASES:
        plan = launcher._execution_plan(phase, f"attempt-{phase.lower()}")
        assert plan.planned_model_calls == 192
        assert plan.planned_speech_audio_seconds == 1865
        assert plan.planned_gpu_hours == 1.0
        assert plan.protocol_hash == launcher.PROTOCOL_SHA256


def test_phase_contract_is_fresh_and_exactly_40_40_80_32_contacts() -> None:
    launcher = _launcher()
    assert launcher.PHASE_CONTACT_CEILINGS == {
        launcher.G3_M0_DIRECT_PHASE: 40,
        launcher.G3_OBSERVATION_PHASE: 40,
        launcher.G3_MATCHED_USE_PHASE: 80,
        launcher.G3_SHUFFLED_USE_PHASE: 32,
    }
    assert sum(launcher.PHASE_CONTACT_CEILINGS.values()) == 192
    assert launcher._phase_attempt_ids("20260902t000000z") == {
        phase: f"attempt-20260902t000000z-g3-{suffix}"
        for phase, suffix in launcher.PHASE_SUFFIXES.items()
    }


def test_roster_and_score_plan_require_complete_unsharded_surfaces() -> None:
    launcher = _launcher()
    roster = launcher._validate_roster({"count": 40, "items": _items()})
    assert roster["tier_counts"] == {tier: 5 for tier in launcher.CANONICAL_TIERS}
    plan = launcher._validate_official_score_plan(launcher.OFFICIAL_SCORE_PLAN)
    assert plan["workers"] == 3
    assert plan["dataset_sharding"] is False
    assert plan["shard_metric_averaging"] is False
    assert plan["network_jitter_testing"] is False
    assert [job["row_count"] for job in plan["jobs"]] == [40, 40, 40]

    drifted = json.loads(json.dumps(launcher.OFFICIAL_SCORE_PLAN))
    drifted["jobs"][0]["input"] = "a 20-row shard"
    with pytest.raises(RuntimeError, match="complete 40-row manifest"):
        launcher._validate_official_score_plan(drifted)


def test_packet_route_gate_stops_the_flight_before_use_on_any_invalid_route() -> None:
    launcher = _launcher()
    routes = {
        item["sample_id"]: SimpleNamespace(
            matched_packet="m" * 100,
            shuffled_packet="s" * 100,
            matched_tool_names=tuple(f"tool-{index}" for index in range(32)),
            shuffled_tool_names=tuple(f"other-{index}" for index in range(32)),
        )
        for item in _items()
    }
    report = launcher._validate_packet_routes(routes, tuple(routes))
    assert report["route_count"] == 40
    assert report["maximum_packet_utf8_bytes"] == 100

    routes[next(iter(routes))].matched_packet = "x" * 64_001
    with pytest.raises(RuntimeError, match="64KB"):
        launcher._validate_packet_routes(routes, tuple(routes))


def test_parallel_official_scoring_uses_three_whole_manifest_workers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = _launcher()
    captured = {}
    output_dir = tmp_path / "official-score"

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        output_dir.mkdir()
        (output_dir / "batch-summary.json").write_text(
            json.dumps({"failed": 0, "succeeded": 3}), encoding="utf-8"
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)
    manifests = {name: tmp_path / f"{name}.json" for name in ("m0", "matched", "shuffled")}
    summary = launcher._run_parallel_scorers(
        mission_dir=tmp_path,
        manifests=manifests,
        lock_sha256="a" * 64,
    )

    assert summary == {"failed": 0, "succeeded": 3}
    assert "--finalize" in captured["command"]
    assert captured["command"][-2:] == ["--workers", "3"]


def test_result_reports_absolute_tier_paired_control_repair_and_ci90() -> None:
    launcher = _launcher()
    items = _items()
    selected = tuple(item["sample_id"] for item in items if int(item["sample_id"][-6:]) < 2)
    m0_fail = tuple(item["sample_id"] for item in items[:8])
    shuffled_fail = selected[:6]
    result = launcher._build_result(
        items=items,
        selected_ids=selected,
        m0_scores=_scores(items, exact_fail=m0_fail, tool_fail=m0_fail),
        matched_scores=_scores(
            items,
            exact_fail=tuple(item["sample_id"] for item in items[:2]),
            tool_fail=tuple(item["sample_id"] for item in items[:1]),
        ),
        shuffled_scores=_scores(items, exact_fail=shuffled_fail, tool_fail=shuffled_fail),
        matched_contact_counts={item["sample_id"]: 2 if item in items[:3] else 1 for item in items},
        shuffled_contact_counts={sample_id: 2 for sample_id in selected},
    )
    assert result["absolute"]["matched"]["exact_count"] == 38
    assert result["paired"]["matched_minus_m0_exact"] == 6
    assert result["selected16"]["matched_minus_shuffled_exact"] >= 4
    assert result["hard_repair_counts"] == {"matched": 3, "shuffled": 16}
    assert result["bootstrap"]["ci_level"] == 0.9
    assert set(result["per_tier"]) == set(launcher.CANONICAL_TIERS)


def test_preflight_only_never_starts_the_service(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    launcher = _launcher()
    monkeypatch.setattr(launcher, "data_root", lambda: Path("/fixed/data"))
    monkeypatch.setattr(
        launcher,
        "_static_preflight",
        lambda _root: {
            "commit": "a" * 40,
            "sample_ids": tuple(f"sample-{index}" for index in range(40)),
            "route_build": {"corpus_utf8_bytes": 228373},
            "geometry": {"slot_count": 2},
        },
    )
    monkeypatch.setattr(
        launcher,
        "_launch",
        lambda _root: (_ for _ in ()).throw(AssertionError("launch entered")),
    )

    assert launcher.main(["--preflight-only"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["contacts"] == {
        "model": 0,
        "network": 0,
        "scorer": 0,
        "tokenizer": 0,
    }
    assert output["official_score_workers"] == 3
