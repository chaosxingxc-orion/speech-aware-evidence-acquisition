from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from speech_aware_evidence_acquisition.contracts import TraceRecord


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
            "slot_f1": slot_f1,
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


def _recovery_documents(sample_ids):
    documents = []
    for index, sample_id in enumerate(sample_ids, start=1):
        request_id = f"prior-{index:04d}"
        text = f"opaque-{index}"
        payload = {
            "sample_id": sample_id,
            "request_id": request_id,
            "key_representation_id": "audio2tool-direct-registry-v1",
            "matcher_policy_id": "saea-a2t-contract-v2-m0-direct",
        }
        outer = {
            "arm": "speech-feature-query",
            "payload": payload,
            "payload_sha256": hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }
        records = (
            ("MODEL_REQUEST", f"{request_id}/request", outer),
            (
                "MODEL_RESPONSE",
                f"{request_id}/response",
                {
                    "response_sha256": "a" * 64,
                    "response_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "text": text,
                    "usage": {
                        "completion_tokens": 1,
                        "prompt_tokens": 2,
                        "total_tokens": 3,
                    },
                },
            ),
            (
                "COST",
                f"{request_id}/cost",
                {
                    "audio_seconds": 1.0,
                    "calls": 1,
                    "completion_tokens": 1,
                    "latency_seconds": 0.5,
                    "prompt_tokens": 2,
                },
            ),
        )
        documents.extend(
            {"channel": channel, "record_id": record_id, "payload": record_payload}
            for channel, record_id, record_payload in records
        )
    manifest = {
        "run_id": "SAEA-A2T-G3-PLAIN-ENGLISH-V1",
        "records": {
            document["record_id"]: TraceRecord(**document).content_hash()
            for document in documents
        },
    }
    return documents, manifest


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
    assert launcher.M0_RECOVERY_TRACE_SHA256.startswith("d101379")
    assert launcher.M0_RECOVERY_TRACE_MANIFEST_SHA256.startswith("3fe909")
    assert launcher.M0_RECOVERY_COMPLETED_COUNT == 31
    assert launcher.COMPLETED_FLIGHT_M0_OUTPUTS_SHA256.startswith("15c542")
    assert launcher.COMPLETED_FLIGHT_M0_MANIFEST_SHA256.startswith("1a25d4")
    assert launcher.COMPLETED_FLIGHT_OBS_TRACE_SHA256.startswith("7f50c9")
    assert launcher.COMPLETED_FLIGHT_OBS_TRACE_MANIFEST_SHA256.startswith("5c06db")
    assert launcher.MATCHED_RECOVERY_OUTPUTS_SHA256.startswith("6e6589")
    assert launcher.MATCHED_RECOVERY_AGENT_TRACE_SHA256.startswith("431025")
    assert launcher.MATCHED_RECOVERY_COMPOSITE_TRACE_SHA256.startswith("18b55f")

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
    split = launcher._verified_split(tuple(item["sample_id"] for item in _items()))
    assert split.identity_hash == launcher.RUN_IDENTITY_SHA256


def test_scoped_media_gate_maps_only_derived_contact_identities() -> None:
    launcher = _launcher()
    calls = []

    class Delegate:
        def verify_media_identity(self, carrier_lock_key, media_facts):
            calls.append((carrier_lock_key, media_facts))

        def assert_model_touch_allowed(self, plan, **kwargs):
            return (plan, kwargs)

    identity_map = {
        "tier1_direct:000001": "tier1_direct:000001",
        "tier7_multiturn:000318": "a2t-g3-dialogue:000318",
    }
    delegate = Delegate()
    gate = launcher._G3MediaIdentityGate(delegate, identity_map)
    facts = {
        "tier1_direct:000001": ("datasets/original.wav", 1.0),
        "tier7_multiturn:000318": ("derived/dialogue.wav", 33.444375),
    }

    gate.verify_media_identity("audio2tool", facts)

    assert calls == [
        (
            "audio2tool",
            {
                "tier1_direct:000001": ("datasets/original.wav", 1.0),
                "a2t-g3-dialogue:000318": ("derived/dialogue.wav", 33.444375),
            },
        )
    ]
    assert gate.assert_model_touch_allowed("plan", full_hash=True) == (
        "plan",
        {"full_hash": True},
    )


def test_g3_gate_uses_protocol_bound_dialogue_supplement(tmp_path: Path) -> None:
    launcher = _launcher()
    captured = {}
    delegate = SimpleNamespace()

    def gate_factory(repo, data_root, runtime_root, **kwargs):
        captured.update(
            repo=repo,
            data_root=data_root,
            runtime_root=runtime_root,
            kwargs=kwargs,
        )
        return delegate

    values = {
        "model_lock_key": "model-key",
        "model_materialization_root": str(tmp_path / "model"),
        "d1_media_supplement": "receipts/artifacts/dialogue.json",
        "d1_media_supplement_sha256": "a" * 64,
    }
    mapping = {"tier7_multiturn:000318": "a2t-g3-dialogue:000318"}

    gate = launcher._build_g3_gate(
        root=tmp_path,
        values=values,
        media_identity_by_sample=mapping,
        gate_factory=gate_factory,
    )

    assert gate.delegate is delegate
    assert captured["kwargs"]["d1_media_supplement_relpath"] == (
        "receipts/artifacts/dialogue.json"
    )
    assert captured["kwargs"]["d1_media_supplement_sha256"] == "a" * 64
    assert captured["kwargs"]["expected_model_lock_key"] == "model-key"


def test_g3_client_confines_verified_original_and_derived_paths_to_data_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = _launcher()
    captured = {}

    def fake_binding(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(launcher, "build_payload_binding", fake_binding)
    monkeypatch.setattr(
        launcher,
        "FrozenCoreClient",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )
    root = tmp_path / "data"
    sample = SimpleNamespace(sample_id="tier7_multiturn:000318")

    launcher._client(
        root=root,
        context={"carrier_root": root / "datasets/audio2tool"},
        gate=object(),
        transport=object(),
        plan=object(),
        samples=(sample,),
        packet_bindings={sample.sample_id: {"packet_id": "p", "sha256": "a" * 64}},
        run_dir=tmp_path / "run",
        prefix="test",
    )

    assert captured["carrier_root"] == root


def test_recovery_trace_reuses_complete_triples_and_returns_only_missing_ids() -> None:
    launcher = _launcher()
    expected_ids = (
        "tier1_direct:000001",
        "tier7_multiturn:000318",
        "tier8_intent_blending:000324",
    )
    documents, manifest = _recovery_documents(expected_ids[:2])

    recovery = launcher._validate_m0_recovery_trace(
        documents,
        manifest,
        expected_ids=expected_ids,
        expected_completed_count=2,
    )

    assert recovery["completed_ids"] == expected_ids[:2]
    assert recovery["missing_ids"] == (expected_ids[2],)
    assert tuple(row.sample_id for row in recovery["summary"].results) == expected_ids[:2]


def test_recovery_trace_refuses_hash_drift_or_incomplete_contact() -> None:
    launcher = _launcher()
    expected_ids = ("tier1_direct:000001", "tier7_multiturn:000318")
    documents, manifest = _recovery_documents(expected_ids[:1])

    drifted = json.loads(json.dumps(documents))
    next(row for row in drifted if row["channel"] == "MODEL_RESPONSE")["payload"][
        "text"
    ] = "changed"
    with pytest.raises(RuntimeError, match="record hash"):
        launcher._validate_m0_recovery_trace(
            drifted,
            manifest,
            expected_ids=expected_ids,
            expected_completed_count=1,
        )

    incomplete = [row for row in documents if row["channel"] != "COST"]
    incomplete_manifest = {
        **manifest,
        "records": {
            row["record_id"]: TraceRecord(**row).content_hash() for row in incomplete
        },
    }
    with pytest.raises(RuntimeError, match="complete request/response/cost"):
        launcher._validate_m0_recovery_trace(
            incomplete,
            incomplete_manifest,
            expected_ids=expected_ids,
            expected_completed_count=1,
        )


def test_completed_obs_trace_recovery_requires_40_hashed_contact_triples() -> None:
    launcher = _launcher()
    expected_ids = tuple(item["sample_id"] for item in _items())
    documents, _manifest = _recovery_documents(expected_ids)
    for document in documents:
        if document["channel"] != "MODEL_REQUEST":
            continue
        request = document["payload"]["payload"]
        request["key_representation_id"] = (
            "saea-a2t-contract-v2-self-transcript-observation:speech"
        )
        request["matcher_policy_id"] = (
            "saea-a2t-contract-v2-self-transcript-observation"
        )
        document["payload"]["payload_sha256"] = hashlib.sha256(
            json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    manifest = {
        "run_id": launcher.RUN_ID,
        "records": {
            document["record_id"]: TraceRecord(**document).content_hash()
            for document in documents
        },
    }

    recovered = launcher._validate_obs_recovery_trace(
        documents,
        manifest,
        expected_ids=expected_ids,
    )

    assert len(recovered["texts"]) == 40
    assert recovered["cost"]["calls"] == 40
    assert set(recovered["contact_counts"]) == set(expected_ids)


def test_completed_matched_trace_recovery_preserves_40_plus_5_contacts() -> None:
    launcher = _launcher()
    expected_ids = tuple(item["sample_id"] for item in _items())
    documents, _manifest = _recovery_documents(expected_ids + expected_ids[:5])
    for document in documents:
        if document["channel"] != "MODEL_REQUEST":
            continue
        request = document["payload"]["payload"]
        request["key_representation_id"] = "a2t-g3-plain-english-k32-v1"
        request["matcher_policy_id"] = "a2t-g3-construction-bm25-k32-matched-v1"
        document["payload"]["payload_sha256"] = hashlib.sha256(
            json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    manifest = {
        "run_id": launcher.RUN_ID,
        "records": {
            document["record_id"]: TraceRecord(**document).content_hash()
            for document in documents
        },
    }

    recovered = launcher._validate_matched_recovery_trace(
        documents,
        manifest,
        expected_ids=expected_ids,
    )

    assert sum(recovered["contact_counts"].values()) == 45
    assert recovered["repair_count"] == 5
    assert set(recovered["repair_sample_ids"]) == set(expected_ids[:5])


def test_trace_reader_uses_the_g3_run_identity(tmp_path: Path) -> None:
    launcher = _launcher()
    expected = {"channel": "COST", "record_id": "x/cost", "payload": {"calls": 1}}
    (tmp_path / f"{launcher.RUN_ID}.trace.jsonl").write_text(
        json.dumps(expected) + "\n",
        encoding="utf-8",
    )

    assert launcher._trace_documents(tmp_path) == (expected,)


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


def test_recovered_observation_normalization_is_shared_by_routing_and_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = _launcher()
    sample_ids = tuple(item["sample_id"] for item in _items())
    normalized = {sample_id: f"normalized {sample_id}" for sample_id in sample_ids}
    captured = {}

    def normalize(summary, **kwargs):
        captured["summary"] = summary
        flags = kwargs["representation_flags"]
        for index, sample_id in enumerate(sample_ids):
            flags[sample_id] = {
                "role_labels_missing": index < 5,
                "normalized_non_ascii": index == 0,
            }
        return normalized

    def route(summary, **kwargs):
        captured["route_summary"] = summary
        captured["routed_observations"] = kwargs["normalized_observation_texts"]
        return {
            sample_id: SimpleNamespace(
                matched_packet="matched",
                shuffled_packet="shuffled",
                matched_tool_names=tuple(f"matched-{index}" for index in range(32)),
                shuffled_tool_names=tuple(f"shuffled-{index}" for index in range(32)),
            )
            for sample_id in sample_ids
        }

    monkeypatch.setattr(launcher.g3_flight, "normalize_observation_texts", normalize)
    monkeypatch.setattr(launcher.g3_flight, "build_packet_routes", route)
    summary = object()
    surface = SimpleNamespace(derived_dialogue_sample_ids=frozenset(sample_ids[:5]))

    observations, _routes, report = launcher._prepare_recovered_observations(
        observation_summary=summary,
        surface=surface,
        corpus=object(),
        sample_ids=sample_ids,
    )

    assert observations is normalized
    assert captured["summary"] is summary
    assert captured["route_summary"] is summary
    assert captured["routed_observations"] is normalized
    assert report["role_labels_missing"] == 5
    assert report["normalized_non_ascii"] == 1


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
    assert "--per-job-operation" in captured["command"]
    assert "--finalize" not in captured["command"]
    assert captured["command"][-2:] == ["--workers", "3"]
    jobs = [json.loads(line) for line in (tmp_path / "official-score-jobs.jsonl").read_text().splitlines()]
    assert [job["operation"] for job in jobs] == ["score", "score", "finalize"]
    assert all("ledger_cells" not in job for job in jobs[:2])
    assert "ledger_cells" in jobs[2]


def test_composite_seal_places_trace_where_manifest_discovers_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = _launcher()
    captured = {}
    run_dir = tmp_path / "run"
    source_trace = run_dir / "agent-trace" / f"{launcher.RUN_ID}.trace.jsonl"
    source_trace.parent.mkdir(parents=True)
    source_trace.write_text("source\n", encoding="utf-8")

    class Sink:
        def __init__(self, path, run_id):
            captured["sink_path"] = path
            captured["run_id"] = run_id

        def close(self):
            return "a" * 64

    monkeypatch.setattr(launcher, "TraceSink", Sink)
    monkeypatch.setattr(
        launcher.g3_flight,
        "emit_g3_use_rows",
        lambda **_kwargs: (
            {
                "sample_id": "tier1_direct:000001",
                "text": "[]",
            },
        ),
    )
    monkeypatch.setattr(
        launcher,
        "_build_completed_manifest",
        lambda **kwargs: captured.update(manifest_kwargs=kwargs)
        or tmp_path / "manifest.json",
    )

    launcher._seal_composite(
        phase=launcher.G3_SHUFFLED_USE_PHASE,
        texts={"tier1_direct:000001": "[]"},
        source_result={
            "client": {"cost": {"calls_used": 1}},
            "agent_trace_hash": "b" * 64,
            "run_dir": run_dir,
        },
        root=tmp_path,
        context={},
        plan=object(),
        run_dir=run_dir,
        session_receipt_path=tmp_path / "session.json",
    )

    assert captured["sink_path"] == run_dir
    assert captured["manifest_kwargs"]["run_dir"] == run_dir


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
    assert "shuffled" not in result["absolute"]
    assert result["absolute"]["shuffled_composite_40"]["exact_count"] == 34
    assert result["paired"]["matched_minus_m0_exact"] == 6
    assert result["selected16"]["scope"] == "preregistered-selected16-only"
    assert result["selected16"]["matched"]["samples"] == 16
    assert result["selected16"]["matched"]["exact_count"] == 14
    assert result["selected16"]["shuffled"]["exact_count"] == 10
    assert result["selected16"]["paired_exact"]["net"] == 4
    assert result["hard_repair_counts"] == {"matched": 3, "shuffled": 16}
    assert result["bootstrap"]["ci_level"] == 0.9
    assert set(result["per_tier"]) == set(launcher.CANONICAL_TIERS)


def test_batch_score_loader_normalizes_inline_and_path_score_shapes(
    tmp_path: Path,
) -> None:
    launcher = _launcher()
    inline_path = tmp_path / "inline.json"
    inline_path.write_text(
        json.dumps(
            {
                "verified": True,
                "manifest": "/fixed/m0.run-manifest.json",
                "scores": {
                    "a2t-toolcall": {"samples": 40, "exact_match": 0.2},
                    "cost": {"calls_used": 40},
                },
            }
        ),
        encoding="utf-8",
    )
    full_scores = {
        "a2t-toolcall": {
            "per_sample": [{"sample_id": "sample-1"}],
            "aggregate": {"samples": 40, "exact_match": 0.175},
        },
        "cost": {"per_sample": [], "aggregate": {"calls_used": 16}},
    }
    full_path = tmp_path / "scores.json"
    full_path.write_text(json.dumps(full_scores), encoding="utf-8")
    path_result = tmp_path / "path.json"
    path_result.write_text(
        json.dumps(
            {
                "verified": True,
                "attempt_state": "FINALIZED",
                "manifest": "/fixed/shuffled.run-manifest.json",
                "scores": str(full_path),
            }
        ),
        encoding="utf-8",
    )

    inline = launcher._load_batch_scores(inline_path)
    referenced = launcher._load_batch_scores(path_result)

    assert inline["a2t-toolcall"] == {
        "per_sample": None,
        "aggregate": {"samples": 40, "exact_match": 0.2},
    }
    assert inline["cost"]["aggregate"] == {"calls_used": 40}
    assert referenced == full_scores


def test_postprocess_existing_mode_never_enters_launch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    launcher = _launcher()
    monkeypatch.setattr(launcher, "data_root", lambda: Path("/fixed/data"))
    monkeypatch.setattr(
        launcher,
        "_postprocess_existing",
        lambda _root: {"status": "SCORED", "postprocess_existing": True},
        raising=False,
    )
    monkeypatch.setattr(
        launcher,
        "_launch",
        lambda _root: (_ for _ in ()).throw(AssertionError("launch entered")),
    )

    assert launcher.main(["--postprocess-existing"]) == 0
    assert json.loads(capsys.readouterr().out)["postprocess_existing"] is True


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
