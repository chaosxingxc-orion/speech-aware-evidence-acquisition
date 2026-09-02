"""Model-free tests for the executable-ground qualification launcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import ToolCall


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
            "query_block": f"tier{tier}_kind:query-{index:06d}",
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
    assert callable(launcher._launch)


def _official_score(
    sample_ids: list[str], *, exact_count: int, tool_count: int, slot_f1: float
) -> dict[str, object]:
    per_sample = [
        {
            "sample_id": sample_id,
            "tier": sample_id.split(":", 1)[0],
            "exact_match": float(index < exact_count),
            "tool_accuracy": float(index < tool_count),
            "parsed": True,
        }
        for index, sample_id in enumerate(sample_ids)
    ]
    return {
        "a2t-toolcall": {
            "per_sample": per_sample,
            "aggregate": {
                "samples": 104,
                "exact_match": exact_count / 104,
                "tool_accuracy": tool_count / 104,
                "slot_precision": slot_f1,
                "slot_recall": slot_f1,
                "slot_f1": slot_f1,
                "parse_failures": 0,
                "per_tier": {},
            },
        }
    }


def test_qualification_result_applies_every_registered_gate_deterministically() -> None:
    launcher = _launcher()
    roster = _roster()
    items = roster["items"]
    sample_ids = [item["sample_id"] for item in items]
    resend_ids = launcher.ground_flight.select_resend_ids(
        {item["sample_id"]: item["tier"] for item in items}
    )
    response = '[{"name":"tool","arguments":{"value":"fixed"}}]'
    expected = {
        sample_id: (ToolCall("tool", {"value": "fixed"}),)
        for sample_id in sample_ids
    }

    first = launcher._build_qualification_result(
        m0_scores=_official_score(
            sample_ids, exact_count=79, tool_count=80, slot_f1=0.75
        ),
        g1_scores=_official_score(
            sample_ids, exact_count=99, tool_count=100, slot_f1=0.95
        ),
        g1_texts={sample_id: response for sample_id in sample_ids},
        resend_texts={sample_id: response for sample_id in resend_ids},
        expected_by_id=expected,
        items=items,
        resend_ids=resend_ids,
    )
    second = launcher._build_qualification_result(
        m0_scores=_official_score(
            sample_ids, exact_count=79, tool_count=80, slot_f1=0.75
        ),
        g1_scores=_official_score(
            sample_ids, exact_count=99, tool_count=100, slot_f1=0.95
        ),
        g1_texts={sample_id: response for sample_id in sample_ids},
        resend_texts={sample_id: response for sample_id in resend_ids},
        expected_by_id=expected,
        items=items,
        resend_ids=resend_ids,
    )
    assert first == second
    assert first["bootstrap"] == {
        **first["bootstrap"],
        "n_replicates": 10_000,
        "seed": 20260902,
        "ci_level": 0.9,
    }
    assert first["counts"]["g1_exact"] == 99
    assert first["counts"]["g1_tool"] == 100
    assert first["counts"]["g1_parse"] == 104
    assert first["counts"]["resend_semantic_call_agreement"] == 16
    assert first["counts"]["resend_exact_outcome_agreement"] == 16
    assert all(first["gates"].values())
    assert first["basic_ground_passed"] is True
    assert first["target_ground_passed"] is True


def test_qualification_result_refuses_incomplete_official_surface() -> None:
    launcher = _launcher()
    roster = _roster()
    items = roster["items"]
    sample_ids = [item["sample_id"] for item in items]
    incomplete = _official_score(
        sample_ids, exact_count=99, tool_count=100, slot_f1=0.95
    )
    incomplete["a2t-toolcall"]["per_sample"].pop()
    with pytest.raises(RuntimeError, match="complete 104-row official score"):
        launcher._build_qualification_result(
            m0_scores=incomplete,
            g1_scores=_official_score(
                sample_ids, exact_count=99, tool_count=100, slot_f1=0.95
            ),
            g1_texts={},
            resend_texts={},
            expected_by_id={},
            items=items,
            resend_ids=(),
        )


def test_resend_payloads_preserve_source_slot_and_content() -> None:
    launcher = _launcher()
    source = {
        "sample-1": {
            "request_id": "ground-g1-0001",
            "sample_id": "sample-1",
            "task_instruction": "handbook",
            "speech_feature_parts": [
                {"packet_id": "tier/1", "sha256": "a" * 64, "role": "query"}
            ],
            "decoding_params": {
                "temperature": 0,
                "seed": 20260803,
                "max_tokens": 1024,
                "id_slot": 1,
            },
            "key_representation_id": "ground",
            "matcher_policy_id": "ground-policy",
            "history": [],
            "supplied_evidence": [],
            "evidence_provenance": [],
        }
    }
    resend = json.loads(json.dumps(source))
    resend["sample-1"]["request_id"] = "ground-resend-0001"
    assert launcher._assert_resend_equivalence(source, resend) == {"sample-1": 1}

    resend["sample-1"]["decoding_params"]["id_slot"] = 0
    with pytest.raises(RuntimeError, match="source request equivalence"):
        launcher._assert_resend_equivalence(source, resend)


def test_parallel_finalizer_uses_two_whole_manifest_jobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = _launcher()
    captured: dict[str, object] = {}
    output_dir = tmp_path / "parallel-official-finalize"

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        output_dir.mkdir()
        (output_dir / "batch-summary.json").write_text(
            json.dumps({"failed": 0, "succeeded": 2}), encoding="utf-8"
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)
    summary = launcher._run_parallel_finalizers(
        mission_dir=tmp_path,
        jobs=(
            {
                "job_id": "m0-registry-direct",
                "manifest": "/fixed/m0.run-manifest.json",
                "ledger_cells": "/fixed/m0-ledger.json",
            },
            {
                "job_id": "g1-full-executable-ground",
                "manifest": "/fixed/g1.run-manifest.json",
                "ledger_cells": "/fixed/g1-ledger.json",
            },
        ),
    )
    assert summary == {"failed": 0, "succeeded": 2}
    assert captured["command"][2:4] == ["--finalize", "--jobs"]
    assert captured["command"][-2:] == ["--workers", "2"]


def test_postseal_read_opens_gold_only_after_both_finalizers_settle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = _launcher()
    events: list[str] = []
    roster = _roster()
    items = roster["items"]
    sample_ids = [item["sample_id"] for item in items]
    resend_ids = launcher.ground_flight.select_resend_ids(
        {item["sample_id"]: item["tier"] for item in items}
    )
    response = '[{"name":"tool","arguments":{}}]'
    expected = {sample_id: (ToolCall("tool", {}),) for sample_id in sample_ids}
    m0 = {
        "manifest": tmp_path / "m0.run-manifest.json",
        "texts": {sample_id: response for sample_id in sample_ids},
    }
    g1 = {
        "manifest": tmp_path / "g1.run-manifest.json",
        "texts": {sample_id: response for sample_id in sample_ids},
    }
    resend = {
        "texts": {sample_id: response for sample_id in resend_ids},
        "resend_ids": resend_ids,
    }

    monkeypatch.setattr(
        launcher,
        "_assert_contact_surface_sealed",
        lambda **kwargs: events.append("sealed"),
    )

    def fake_finalize(**kwargs):
        assert events == ["sealed"]
        events.append("finalized")
        return {"failed": 0, "succeeded": 2}

    monkeypatch.setattr(launcher, "_run_parallel_finalizers", fake_finalize)
    monkeypatch.setattr(
        launcher,
        "verify_bundle",
        lambda path: SimpleNamespace(attempt_state="FINALIZED"),
    )
    monkeypatch.setattr(
        launcher,
        "_load_final_scores",
        lambda path: _official_score(
            sample_ids, exact_count=99, tool_count=100, slot_f1=0.95
        ),
    )

    def fake_expected(*args, **kwargs):
        assert events == ["sealed", "finalized"]
        events.append("gold")
        return expected

    monkeypatch.setattr(launcher, "load_expected_calls", fake_expected)
    monkeypatch.setattr(
        launcher,
        "_build_qualification_result",
        lambda **kwargs: {"schema": "fixed-result"},
    )
    result = launcher._postseal_qualification(
        root=tmp_path,
        context={"items": items, "lock": {}, "resend_ids": resend_ids},
        mission_dir=tmp_path,
        lock_sha256="a" * 64,
        m0=m0,
        g1=g1,
        resend=resend,
    )
    assert events == ["sealed", "finalized", "gold"]
    assert result["qualification"] == {"schema": "fixed-result"}


def test_request_payload_extractor_requires_hash_bound_unique_samples() -> None:
    launcher = _launcher()
    payload = {
        "request_id": "ground-g1-0001",
        "sample_id": "sample-1",
        "decoding_params": {"id_slot": 0},
    }
    envelope = {
        "arm": "speech-feature-query",
        "payload": payload,
        "payload_sha256": launcher.hashlib.sha256(
            launcher.canonical_payload_bytes(payload)
        ).hexdigest(),
    }
    documents = (
        {
            "channel": "MODEL_REQUEST",
            "record_id": "ground-g1-0001/request",
            "payload": envelope,
        },
    )
    assert launcher._request_payloads_by_sample(documents) == {"sample-1": payload}
    envelope["payload_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="payload hash drift"):
        launcher._request_payloads_by_sample(documents)


def test_committed_prompt_fit_receipt_passes_the_zero_contact_gate() -> None:
    launcher = _launcher()
    receipt = json.loads((REPO / launcher.PROMPT_FIT_RELPATH).read_text("utf-8"))
    launcher._validate_prompt_fit(receipt)
