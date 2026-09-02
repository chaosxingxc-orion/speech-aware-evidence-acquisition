"""Zero-contact tests for the G5 exhaustive-family fixed16 launcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from speech_aware_evidence_acquisition.rails.adapters.audio2tool import Audio2ToolSample
from speech_aware_evidence_acquisition.rails.obs import AudioRef
from speech_aware_evidence_acquisition.rails.probes.a2t_g5_agentloop import (
    EXECUTE_CONTACT_ID,
    ParsedPlan,
    PLAN_CONTACT_ID,
)


REPO = Path(__file__).resolve().parents[2]
LAUNCHER = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g5-exhaustive-family-fixed16-v1/launcher/"
    "launch_a2t_g5_fixed16.py"
)


def _launcher():
    name = "test_a2t_g5_fixed16_launcher_module"
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


def test_fixed16_identity_tier_balance_and_two_contact_execution_plan() -> None:
    launcher = _launcher()
    tier_by_sample = {
        sample_id: sample_id.split(":", 1)[0] for sample_id in launcher.SELECTED_IDS
    }

    assert len(launcher.SELECTED_IDS) == 16
    assert launcher._validate_selected_ids(tier_by_sample) == launcher.SELECTED_IDS
    assert {
        tier: sum(value == tier for value in tier_by_sample.values())
        for tier in launcher.EXPECTED_TIERS
    } == {tier: 2 for tier in launcher.EXPECTED_TIERS}
    assert launcher.SELECTED_SPLIT_SHA256 == (
        "c1c38f4ac670846df8c2a488aa62642bb6d14733aa8cc4fa33955f5c2bf76550"
    )
    assert launcher.SELECTED_RUN_SHA256 == (
        "8c0136a901693548a737bf4bf3fa83206d9bae190283123d6412be6a78b069fe"
    )

    plan = launcher._execution_plan(
        "attempt-20260902t000000z-g5-fixed16", protocol_hash="a" * 64
    )
    assert plan.run_id == launcher.RUN_ID
    assert plan.execution_profile == "bounded-discovery-probe"
    assert plan.split_identity_hash == launcher.SELECTED_RUN_SHA256
    assert plan.planned_model_calls == 32
    assert plan.planned_speech_audio_seconds == 247
    assert launcher.SELECTED_AUDIO_SECONDS == pytest.approx(123.209)
    assert launcher.MAX_CONTACTS == 2
    assert launcher.MAX_TOTAL_CONTACTS == 32
    assert launcher.SLOT_COUNT == 2
    assert launcher.QUEUE_DEPTH == 4
    assert launcher.TEMPERATURE == 0
    assert launcher.REPAIR_CONTACTS == launcher.RETRIES == 0
    assert launcher.JITTER_TESTING is False


def test_all_launch_bindings_are_explicit_and_complete() -> None:
    launcher = _launcher()

    assert launcher._unbound_requirements() == ()
    assert launcher._require_bound_requirements() is None
    assert launcher.EXPERIMENT_CONFIG_SHA256 == (
        "fb69d031fc291e9fdc228430acfda95d9f743059795059593205891e57afe0c4"
    )
    assert launcher.COMPOSED_CONFIG_SHA256 == (
        "797bf47bcb7fb7c94c46a79cc62e9cd1963414d48c3aa3f8912020f450607f09"
    )
    assert launcher.PROTOCOL_SHA256 == (
        "e669d545e7ffb7ed09e9a827e99951807699c9fc49796d5942a0b31f6716f9fd"
    )


def test_compiler_maps_each_declared_family_to_every_contract_without_ranking() -> None:
    launcher = _launcher()
    corpus = launcher._load_committed_corpus()
    compiler, snapshot = launcher._build_compiler(corpus)

    assert len(compiler.taxonomy) == 28
    assert len(compiler.registered_tool_names) == 152
    assert snapshot.content_hash() == launcher._snapshot_sha256(corpus)
    for taxon in compiler.taxonomy:
        plan = ParsedPlan(
            valid=True,
            status="VALID",
            operations=(),
            selected_family_tags=(taxon.family_tag,),
            canonical_json='{"operations":[]}',
        )
        bundle = compiler.compile(plan)
        assert bundle.family_tags == (taxon.family_tag,)
        assert len(bundle.contracts) == 1
        assert bundle.contracts[0].content.encode("ascii") == (
            compiler.family_records[taxon.family_tag].bundle_bytes
        )
        assert bundle.complete is True
        assert bundle.selection_mode == "full-unranked-compatible"
        assert bundle.synthetic_literals == ()


def test_integration_mapping_and_prompt_envelope_are_exhaustive_and_bounded() -> None:
    launcher = _launcher()
    corpus = launcher._load_committed_corpus()
    compiler, snapshot = launcher._build_compiler(corpus)
    integration = {
        "schema": launcher.INTEGRATION_SCHEMA,
        "fallback_family_tags": list(compiler.fallback_family_tags),
        "allowed_family_unions": [[taxon.family_tag] for taxon in corpus.taxonomy],
        "plan_text_token_cap": 6000,
        "execute_text_token_cap": 12000,
        "special_token_reserve": 512,
    }
    speech_tokens = {sample_id: 468 for sample_id in launcher.SELECTED_IDS}

    report = launcher._validate_integration_and_envelopes(
        integration,
        corpus=corpus,
        compiler=compiler,
        snapshot=snapshot,
        speech_feature_tokens_by_sample=speech_tokens,
    )

    assert report["family_count"] == 28
    assert report["declared_union_count"] == 28
    assert report["maximum_total_tokens"] <= 32_768
    assert report["maximum_bundle_ascii_bytes"] <= 18_432
    drifted = dict(integration)
    drifted["allowed_family_unions"] = integration["allowed_family_unions"][:-1]
    with pytest.raises(RuntimeError, match="exhaustive"):
        launcher._validate_integration_and_envelopes(
            drifted,
            corpus=corpus,
            compiler=compiler,
            snapshot=snapshot,
            speech_feature_tokens_by_sample=speech_tokens,
        )


def test_run_boundary_requires_exactly_plan_then_execute_for_all_sixteen() -> None:
    launcher = _launcher()
    samples = _samples(launcher)
    corpus = launcher._load_committed_corpus()
    compiler, snapshot = launcher._build_compiler(corpus)
    adapter = launcher.G5AgentLoopAdapter(
        samples,
        split_id=launcher.SPLIT_ID,
        taxonomy=compiler.taxonomy,
    )
    calls: list[dict[str, object]] = []
    summary = SimpleNamespace(
        results=tuple(
            SimpleNamespace(
                sample_id=sample_id,
                contacts=(
                    SimpleNamespace(plan=SimpleNamespace(contact_id=PLAN_CONTACT_ID)),
                    SimpleNamespace(plan=SimpleNamespace(contact_id=EXECUTE_CONTACT_ID)),
                ),
                agent_states=(SimpleNamespace(as_json=lambda: {"kind": "plan"}),),
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
        snapshot=snapshot,
        packet_bindings={sample_id: {} for sample_id in launcher.SELECTED_IDS},
        speech_feature_tokens_by_sample={
            sample_id: 1 for sample_id in launcher.SELECTED_IDS
        },
        compiler=compiler,
        trace_sink=object(),
        run_phase=run_phase,
    )

    assert result is summary
    assert len(calls) == 1
    assert sum(len(row.contacts) for row in result.results) == 32
    assert all(
        tuple(contact.plan.contact_id for contact in row.contacts)
        == (PLAN_CONTACT_ID, EXECUTE_CONTACT_ID)
        for row in result.results
    )


def test_plan_state_seal_is_nonfinal_and_final_manifest_source_is_execute_only() -> None:
    launcher = _launcher()
    summary = SimpleNamespace(
        results=tuple(
            SimpleNamespace(
                sample_id=sample_id,
                contacts=(
                    SimpleNamespace(plan=SimpleNamespace(contact_id=PLAN_CONTACT_ID)),
                    SimpleNamespace(plan=SimpleNamespace(contact_id=EXECUTE_CONTACT_ID)),
                ),
                agent_states=(
                    SimpleNamespace(
                        as_json=lambda sid=sample_id: {
                            "state_kind": "g5-closed-family-plan-v1",
                            "state_id": f"state:{sid}",
                        }
                    ),
                ),
                final_response_text=f"[{{\"name\":\"tool-{sample_id}\",\"arguments\":{{}}}}]",
            )
            for sample_id in launcher.SELECTED_IDS
        )
    )

    plans = launcher._plan_state_rows(summary)
    finals = launcher._final_execute_texts(summary)

    assert len(plans) == len(finals) == 16
    assert all(row["nonfinal"] is True for row in plans)
    assert all("final_response_text" not in row for row in plans)
    assert tuple(finals) == launcher.SELECTED_IDS


def test_official_score_plan_is_one_complete_final16_manifest_job() -> None:
    launcher = _launcher()

    assert launcher._validate_official_score_plan(launcher.OFFICIAL_SCORE_PLAN)[
        "jobs"
    ] == [
        {
            "job_id": "g5-final16",
            "input": "complete final16 output manifest",
            "row_count": 16,
        }
    ]
    drifted = json.loads(json.dumps(launcher.OFFICIAL_SCORE_PLAN))
    drifted["jobs"].append(dict(drifted["jobs"][0]))
    with pytest.raises(RuntimeError, match="one complete final16"):
        launcher._validate_official_score_plan(drifted)


def test_main_separates_zero_contact_preflight_from_explicit_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    launcher = _launcher()
    context = {
        "commit": "b" * 40,
        "selected_ids": launcher.SELECTED_IDS,
        "prompt_report": {"maximum_total_tokens": 1234},
        "execution_plan_template": launcher._execution_plan(
            "attempt-preflight-g5", protocol_hash="d" * 64
        ),
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
    assert payload["planned_model_calls"] == 32
    assert calls == []

    assert launcher.main(["--run"]) == 0
    assert calls == [Path("/fixed/data")]
    with pytest.raises(SystemExit):
        launcher.main([])
