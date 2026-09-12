"""Receipt-scoped Audio2Tool uses the shared factory without reading targets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import runpy

import pytest

from speech_aware_evidence_acquisition.core.base import CoreError, Registry
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails.adapters import (
    audio2tool_runtime as module,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (
    Audio2ToolAdapter,
)


TIERS = (
    "tier1_direct",
    "tier2_parametric",
    "tier3_multi_intent",
    "tier4_implicit",
    "tier5_needle",
    "tier6_correction",
    "tier7_multiturn",
    "tier8_intent_blending",
)


def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def world(tmp_path):
    repo, data = tmp_path / "repo", tmp_path / "data"
    items = []
    for i, tier in enumerate(TIERS):
        relative = f"media/{tier}.wav"
        audio = data / relative
        audio.parent.mkdir(parents=True, exist_ok=True)
        audio.write_bytes(f"synthetic speech {i}".encode())
        sample_id = f"{tier}:{i:06d}"
        items.append(
            {
                "sample_id": sample_id,
                "key": f"audio2tool:{sample_id}",
                "tier": tier,
                "id": i,
                "query_idx": i + 100,
                "media_relpath": relative,
                "audio_seconds": 1.0,
                "audio_sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
            }
        )
    doc = {
        "schema": "saea-a2t-agentloop-flight-roster-receipt-v1",
        "carrier": "audio2tool",
        "split_name": "A2T-SYNTHETIC",
        "split_role": "discovery",
        "count": len(items),
        "items": items,
        "split_identity_hash": split_identity_hash(x["key"] for x in items),
        "flight_split_identity_hash": split_identity_hash(
            prefixed("audio2tool", [x["sample_id"] for x in items])
        ),
    }
    rel = "docs/receipts/synthetic-a2t-roster.json"
    digest = write_json(repo / rel, doc)
    dataset = {
        "carrier_lock_key": "audio2tool",
        "split_id": doc["split_name"],
        "a2t_calibration_subset_receipt": rel,
        "a2t_calibration_subset_receipt_sha256": digest,
        "a2t_calibration_split_name": doc["split_name"],
        "a2t_calibration_split_role": "discovery",
        "a2t_calibration_split_identity_hash": doc["split_identity_hash"],
        "a2t_calibration_flight_split_identity_hash": doc["flight_split_identity_hash"],
        "a2t_calibration_count": len(items),
    }
    write_json(repo / "configs/dataset/d.json", dataset)
    values = {
        **dataset,
        "serving_geometry": {"slots": 4, "slot_tokens": 8192, "max_tokens": 256},
        "server_args": ["-np", "4", "-c", "32768"],
        "decoding_params": {"max_tokens": 256},
        "task_instruction": "Listen and return the required tool calls.",
        "policy": "phase-direct-only-v1",
    }
    return repo, data, values, doc


def build(repo, data, values):
    return module.build_runtime_adapter(values, {}, data, repo, dataset_fragment="d")


def rewrite_receipt(repo, values, doc):
    digest = write_json(repo / values["a2t_calibration_subset_receipt"], doc)
    values["a2t_calibration_subset_receipt_sha256"] = digest
    path = repo / "configs/dataset/d.json"
    dataset = json.loads(path.read_text())
    dataset["a2t_calibration_subset_receipt_sha256"] = digest
    write_json(path, dataset)


def test_all_tiers_use_exact_media_only_receipt_and_no_gold(tmp_path, monkeypatch):
    repo, data, values, doc = world(tmp_path)
    from speech_aware_evidence_acquisition.rails.adapters import audio2tool
    from speech_aware_evidence_acquisition.data import audio2tool as loader

    def forbidden(*args, **kwargs):
        raise AssertionError("runtime must not open raw tier manifests or targets")

    for name in ("load_expected_calls", "load_audio2tool", "audio2tool_receipts"):
        monkeypatch.setattr(audio2tool, name, forbidden)
    monkeypatch.setattr(loader, "load_query_rows", forbidden)
    adapter = build(repo, data, values)
    samples = adapter.load_split("A2T-SYNTHETIC")
    assert isinstance(adapter, Audio2ToolAdapter)
    assert [s.sample_id for s in samples] == sorted(
        x["sample_id"] for x in doc["items"]
    )
    assert adapter.serving_geometry() == values["serving_geometry"]
    assert adapter.instruction(samples[0]) == values["task_instruction"]
    assert set(vars(samples[0])) == {
        "sample_id",
        "audio_ref",
        "audio_seconds",
        "media_relpath",
    }
    assert adapter.score(samples[0], "[]")["scored_post_hoc_by"].endswith(
        "core.scoring_batch"
    )
    with pytest.raises(CoreError, match="gold"):
        adapter.gold(samples[0])
    with pytest.raises(CoreError, match="split"):
        adapter.load_split("discovery")
    adapter.bind_runtime(object(), values)
    with pytest.raises(CoreError, match="changed"):
        adapter.bind_runtime(object(), dict(values, task_instruction="Different."))


def test_shared_loader_hashes_before_parsing_or_reading_media(tmp_path, monkeypatch):
    repo, data, values, _ = world(tmp_path)
    p = repo / values["a2t_calibration_subset_receipt"]
    p.write_text("not JSON")
    with pytest.raises(CoreError, match="hash"):
        module.roster_samples(p, values["a2t_calibration_subset_receipt_sha256"], data)


@pytest.mark.parametrize(
    "change,match",
    [
        ({"a2t_calibration_subset_receipt_sha256": "0" * 64}, "dataset"),
        ({"split_id": "different"}, "dataset"),
        ({"a2t_calibration_split_role": "confirmatory"}, "dataset"),
        ({"a2t_calibration_count": 7}, "dataset"),
        ({"carrier_lock_key": "slurp"}, "audio2tool"),
        (
            {
                "serving_geometry": {
                    "slots": True,
                    "slot_tokens": 8192,
                    "max_tokens": 256,
                }
            },
            "geometry",
        ),
        (
            {"serving_geometry": {"slots": 4, "slot_tokens": 8192, "max_tokens": 64}},
            "max_tokens",
        ),
        ({"server_args": ["-np", "2", "-c", "32768"]}, "geometry"),
        ({"serving_slots": 2}, "geometry"),
    ],
)
def test_config_cannot_override_roster_or_silently_change_geometry(
    tmp_path, change, match
):
    repo, data, values, _ = world(tmp_path)
    values.update(change)
    with pytest.raises((CoreError, ValueError), match=match):
        build(repo, data, values)


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda doc: doc.update(split_role="confirmatory"), "discovery"),
        (lambda doc: doc.update(carrier="slurp"), "carrier"),
        (lambda doc: doc.update(count=7), "count"),
        (lambda doc: doc.update(split_identity_hash="0" * 64), "identity"),
        (lambda doc: doc.update(flight_split_identity_hash="0" * 64), "identity"),
        (
            lambda doc: doc["items"][0].update(expected_tool_call="forbidden"),
            "non-media",
        ),
        (
            lambda doc: doc["items"][0].update(media_relpath="../outside.wav"),
            "confined",
        ),
        (lambda doc: doc["items"][0].update(audio_seconds=float("nan")), "positive"),
        (lambda doc: doc["items"][0].update(audio_sha256="0" * 64), "hash"),
        (lambda doc: doc["items"][0].update(key="audio2tool:wrong"), "identity"),
        (lambda doc: doc["items"].__setitem__(1, dict(doc["items"][0])), "duplicate"),
    ],
)
def test_bad_pinned_rosters_refuse_before_runtime(tmp_path, mutation, match):
    repo, data, values, doc = world(tmp_path)
    mutation(doc)
    rewrite_receipt(repo, values, doc)
    with pytest.raises((CoreError, ValueError), match=match):
        build(repo, data, values)


def test_registered_subset_is_exact_and_never_relabels_full_identity(tmp_path):
    repo, data, values, doc = world(tmp_path)
    selected = [doc["items"][2]["sample_id"], doc["items"][7]["sample_id"]]
    values["populations"] = [{"dataset_fragment": "d", "ids": selected}]
    adapter = build(repo, data, values)
    assert [s.sample_id for s in adapter.load_split("A2T-SYNTHETIC")] == sorted(
        selected
    )
    values["populations"][0]["ids"] += ["absent"]
    with pytest.raises((CoreError, ValueError), match="missing"):
        build(repo, data, values)


def test_media_variant_stays_under_its_declared_root(tmp_path):
    repo, data, values, doc = world(tmp_path)
    with pytest.raises(CoreError, match="derived"):
        module.roster_samples(
            repo / values["a2t_calibration_subset_receipt"],
            values["a2t_calibration_subset_receipt_sha256"],
            data,
            media_prefix="derived/a2t",
        )


def test_inactive_template_preserves_legacy_instruction(tmp_path, monkeypatch):
    repo, data, values, _ = world(tmp_path)
    values.pop("task_instruction")
    values.update(
        task_instruction_template="missing-template.txt",
        task_instruction_fill="missing-fill",
    )
    monkeypatch.setattr(Audio2ToolAdapter, "instruction", lambda *_: "Legacy registry.")
    assert build(repo, data, values).instruction(None) == "Legacy registry."
    values["task_instruction_template_active"] = True
    with pytest.raises(CoreError):
        build(repo, data, values)


def test_active_template_uses_shared_resolver_without_changing_contract(
    tmp_path, monkeypatch
):
    repo, data, values, _ = world(tmp_path)
    values.pop("task_instruction")
    values.update(
        task_instruction_template_active=True, task_instruction_template="pinned.txt"
    )
    from speech_aware_evidence_acquisition.core import instructions

    monkeypatch.setattr(
        instructions, "resolve_task_instruction", lambda *_: "Native pinned schema."
    )
    assert build(repo, data, values).instruction(None) == "Native pinned schema."


def test_registry_is_idempotent_and_does_not_replace_another_adapter(monkeypatch):
    from speech_aware_evidence_acquisition.core import base

    registry = Registry("task adapter")
    monkeypatch.setattr(base, "TASK_ADAPTERS", registry)
    module.register_runtime_adapter()
    module.register_runtime_adapter()
    assert registry.resolve("audio2tool") is module.build_runtime_adapter
    registry._entries["audio2tool"] = object()
    with pytest.raises(CoreError, match="already registered"):
        module.register_runtime_adapter()


def test_legacy_entry_reexports_shared_loader_and_adapter(monkeypatch):
    repo = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setenv("PYTHONPATH", str(repo / "src"))
    namespace = runpy.run_path(str(repo / "scripts/flights/run_calibration_cell.py"))
    assert namespace["roster_samples"] is module.roster_samples
    assert namespace["CalibrationAdapter"] is module.Audio2ToolRuntimeAdapter


def test_factory_registers_audio2tool_with_the_existing_runtime(tmp_path):
    from speech_aware_evidence_acquisition.core.flight.factory import (
        build_flight_runtime,
    )
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    from test_flight_runtime import _make_repo, _git, _HAPPY_PATH_KWARGS, _FakeGate

    repo, data, values, doc = world(tmp_path)
    # Keep a separate synthetic Git repository and copy only the configured media receipt.
    fixture = tmp_path / "factory"
    fixture.mkdir()
    target = _make_repo(
        fixture,
        "A2T-FACTORY",
        carrier_lock_key="audio2tool",
        policy="phase-direct-only-v1",
        model_extra={
            k: values[k] for k in ("server_args", "serving_geometry", "decoding_params")
        },
        baseline_extra={"task_instruction": values["task_instruction"]},
    )
    write_json(target / values["a2t_calibration_subset_receipt"], doc)
    write_json(
        target / "configs/dataset/d.json",
        json.loads((repo / "configs/dataset/d.json").read_text()),
    )
    _git(target, "add", "-A")
    _git(target, "commit", "-qm", "bind synthetic all-tier roster")
    runtime = build_flight_runtime(
        target,
        data,
        model="m",
        dataset="d",
        baseline="b",
        experiment="e",
        run_id="A2T-FACTORY",
        attempt_id="a",
        runtime_root=tmp_path / "runtime",
        lock={},
        gate_factory=lambda *a, **kw: _FakeGate(),
        **_HAPPY_PATH_KWARGS,
    )
    runtime.preflight()
    assert isinstance(runtime, FlightRuntime)
    assert isinstance(runtime.adapter, module.Audio2ToolRuntimeAdapter)
    assert len(runtime.adapter.load_split("A2T-SYNTHETIC")) == 8


@pytest.mark.parametrize(
    "policy", ["phase-direct-only-v1", "phase-task-tools-then-solve-v1"]
)
def test_factory_executes_direct_and_live_state_through_real_shared_program(
    tmp_path,
    monkeypatch,
    policy,
):
    from test_flight_runtime import _make_repo, _HAPPY_PATH_KWARGS
    from test_rails_frozen_core_client import _World, _speech_feature_world
    from test_rails_runner import _knowledge_snapshot
    from speech_aware_evidence_acquisition.core.flight.factory import (
        build_flight_runtime,
    )
    from speech_aware_evidence_acquisition.rails.core_client import (
        FrozenCoreClient,
        build_payload_binding,
    )
    from speech_aware_evidence_acquisition.rails.phase_runner import run_program
    from speech_aware_evidence_acquisition.rails.adapters import audio2tool

    synthetic = _World(tmp_path)
    feature_root, _, packets = _speech_feature_world(synthetic, tmp_path)
    phases = ("direct",) if policy == "phase-direct-only-v1" else ("plan", "solve")
    baseline = {
        "task_instruction": "Return the tool calls supported by the current speech.",
        "phase_material": {
            phase: {
                "instruction_template": f"probes/{phase}.txt",
                "predecessor_binding": "none",
            }
            for phase in phases
        },
    }
    if len(phases) == 2:
        baseline["phase_tools"] = {
            "plan": {
                "mode": "fixed",
                "allowed_tools": ["saea-tool-task-contract-v1"],
                "fixed_action": {
                    "tool_id": "saea-tool-task-contract-v1",
                    "arguments": {},
                },
            }
        }
    repo = _make_repo(
        tmp_path,
        "A2T-LIVE-WIRE",
        carrier_lock_key="audio2tool",
        arm="speech-feature-query",
        policy=policy,
        model_extra={
            "speech_feature_root": str(feature_root),
            "server_args": ["-np", "2", "-c", "16384"],
            "serving_geometry": {"slots": 2, "slot_tokens": 8192, "max_tokens": 256},
            "decoding_params": {"max_tokens": 256},
        },
        baseline_extra=baseline,
    )
    items = [
        {
            "sample_id": sample.sample_id,
            "key": "audio2tool:" + sample.sample_id,
            "media_relpath": sample.audio_ref.path,
            "audio_sha256": sample.audio_ref.sha256,
            "audio_seconds": sample.audio_seconds,
        }
        for sample in synthetic.samples
    ]
    roster = {
        "schema": "saea-a2t-agentloop-flight-roster-receipt-v1",
        "carrier": "audio2tool",
        "split_name": "A2T-LIVE-SYNTHETIC",
        "split_role": "discovery",
        "count": 2,
        "items": items,
        "split_identity_hash": split_identity_hash(item["key"] for item in items),
        "flight_split_identity_hash": split_identity_hash(
            prefixed("audio2tool", [item["sample_id"] for item in items])
        ),
    }
    rel = "docs/receipts/live-synthetic.json"
    digest = write_json(repo / rel, roster)
    write_json(
        repo / "configs/dataset/d.json",
        {
            "carrier_lock_key": "audio2tool",
            "split_id": roster["split_name"],
            "a2t_calibration_subset_receipt": rel,
            "a2t_calibration_subset_receipt_sha256": digest,
            "a2t_calibration_split_name": roster["split_name"],
            "a2t_calibration_split_role": "discovery",
            "a2t_calibration_split_identity_hash": roster["split_identity_hash"],
            "a2t_calibration_flight_split_identity_hash": roster[
                "flight_split_identity_hash"
            ],
            "a2t_calibration_count": 2,
        },
    )
    for phase in phases:
        (repo / f"configs/probes/{phase}.txt").parent.mkdir(parents=True, exist_ok=True)
        (repo / f"configs/probes/{phase}.txt").write_text(
            f"Use the current speech during {phase}."
        )
    # The only task-source substitute is a synthetic public tool registry.
    monkeypatch.setattr(
        audio2tool, "render_tool_schemas", lambda *_: "setLight(state: boolean)"
    )
    seams = dict(_HAPPY_PATH_KWARGS)
    seams.update(
        client_factory=FrozenCoreClient,
        phase_runner=run_program,
        payload_binding_factory=lambda **kw: build_payload_binding(
            carrier_lock_key="audio2tool",
            samples=synthetic.samples,
            data_root=synthetic.data_root,
            carrier_root=synthetic.carrier_root,
        ),
    )
    runtime = build_flight_runtime(
        repo,
        synthetic.data_root,
        model="m",
        dataset="d",
        baseline="b",
        experiment="e",
        run_id="A2T-LIVE-WIRE",
        attempt_id="a",
        runtime_root=tmp_path / "runtime",
        lock={},
        **seams,
    )
    runtime._load_knowledge_snapshot = _knowledge_snapshot
    runtime.speech_packet_bindings = lambda: packets
    runtime._speech_feature_root = lambda: feature_root
    payloads = []
    receipt = runtime.wire_check(
        seal_and_score=False,
        response_text="synthetic current-speech state",
        request_payload_observer=payloads.append,
    )
    assert receipt["model_contacts"] == 0
    assert receipt["contact_count"] == 2 * len(phases)
    expected_dispatch = (
        "phase-program" if len(phases) == 1 else "phase-program-continuous"
    )
    assert receipt["dispatch"]["dispatch"] == expected_dispatch
    assert len(payloads) == 2 * len(phases)
    if len(phases) == 2:
        assert receipt["dispatch"]["phase_tools"]["completed"] == 2
        followups = [
            json.dumps(p)
            for p in payloads
            if "saea-tool-task-contract-v1" in json.dumps(p)
        ]
        assert followups
        assert any(
            "synthetic current-speech state" in p and "setLight" in p for p in followups
        )


def test_active_contract_uses_one_schema_in_actual_shared_request(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.rails.knowledge import QueryState
    from speech_aware_evidence_acquisition.rails.runner import _agent_messages

    repo, data, values, _ = world(tmp_path)
    values["task_contract_source"] = "active-instruction"
    values["task_instruction"] = "Return tool_name(). Available tools: alpha(), beta()."
    adapter = build(repo, data, values)
    sample = adapter.load_split("A2T-SYNTHETIC")[0]
    monkeypatch.setattr(
        Audio2ToolAdapter, "build_task_contract", lambda *_: "Duplicated legacy registry."
    )
    contract = adapter.build_task_contract(sample, None)
    state = QueryState(
        query_id="q", query_sample_id=sample.sample_id,
        speech_packet_id="tier1_direct/000000", speech_packet_sha256="a" * 64,
        use_split_identity_hash="b" * 64,
    )
    messages = _agent_messages(
        adapter=adapter, sample=sample, task_contract=contract, query_state=state,
        snapshot=SimpleNamespace(facets=(), values=()), snapshot_sha256="c" * 64,
    )
    assert messages[0]["content"] == values["task_instruction"]
    assert "Duplicated legacy registry." not in str(messages)


def test_legacy_task_contract_stays_unchanged_and_bad_source_refuses(tmp_path, monkeypatch):
    repo, data, values, _ = world(tmp_path)
    monkeypatch.setattr(
        Audio2ToolAdapter, "build_task_contract", lambda *_: "Legacy contract."
    )
    assert build(repo, data, values).build_task_contract(None, None) == "Legacy contract."
    values["task_contract_source"] = "unsupported"
    with pytest.raises(CoreError, match="task_contract_source"):
        build(repo, data, values)
    values["task_contract_source"] = "active-instruction"
    values.pop("task_instruction")
    with pytest.raises(CoreError, match="active instruction"):
        build(repo, data, values)
