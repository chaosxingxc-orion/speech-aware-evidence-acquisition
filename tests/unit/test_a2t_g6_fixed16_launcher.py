"""Zero-contact tests for the G6 exhaustive family-sweep fixed16 launcher."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from speech_aware_evidence_acquisition.rails.adapters.audio2tool import Audio2ToolSample
from speech_aware_evidence_acquisition.rails.obs import AudioRef
from speech_aware_evidence_acquisition.rails.probes.a2t_g6_family_sweep import (
    CONTROLLER_POLICY_ID,
    RESOLVE_CONTACT_ID,
    SCAN_CONTACT_PREFIX,
    ContactContext,
    ParsedResolution,
)


REPO = Path(__file__).resolve().parents[2]
LAUNCHER = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g6-exhaustive-family-sweep-fixed16-v1/launcher/"
    "launch_a2t_g6_fixed16.py"
)


def _launcher():
    name = "test_a2t_g6_fixed16_launcher_module"
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


class _Context:
    def __init__(self, contact_id: str, stage: str, family_tag: str | None = None):
        self.contact_id = contact_id
        self.stage = stage
        self.family_tag = family_tag
        self.speech_packet_id = "packet"
        self.speech_packet_sha256 = "a" * 64
        self.task_contract = "Use only the original speech."
        self.instruction = f"{stage} instruction"
        self.contracts = ()
        self.report_jsons = ()
        self.completion_token_ceiling = 512 if stage == "SCAN" else 1024

    def measure_exact_request(self, rendered_request, *, token_counter, speech_feature_tokens):
        assert rendered_request
        return SimpleNamespace(
            contact_id=self.contact_id,
            rendered_request_sha256=hashlib.sha256(
                rendered_request.encode("utf-8")
            ).hexdigest(),
            text_tokens=token_counter(rendered_request),
            speech_feature_tokens=speech_feature_tokens,
            special_token_reserve=512,
            completion_token_ceiling=self.completion_token_ceiling,
            total_tokens=2000,
            remaining_tokens=30_768,
        )


class _Sweep:
    family_tags = tuple(f"family-{index:02d}" for index in range(28))

    def build_scan_contexts(self, **kwargs):
        assert kwargs["speech_packet_id"] == "packet"
        assert kwargs["speech_packet_sha256"] == "a" * 64
        return tuple(
            _Context(f"{SCAN_CONTACT_PREFIX}{family}", "SCAN", family)
            for family in self.family_tags
        )

    def parse_scan_responses(self, responses):
        assert tuple(responses) == self.family_tags
        return tuple(
            SimpleNamespace(
                family_tag=family,
                valid=True,
                status="VALID",
                canonical_json=json.dumps({"family_tag": family}),
            )
            for family in self.family_tags
        )

    def build_resolve_context(self, **kwargs):
        assert len(kwargs["reports"]) == 28
        return ContactContext(
            contact_id=RESOLVE_CONTACT_ID,
            stage="RESOLVE",
            speech_packet_id=kwargs["speech_packet_id"],
            speech_packet_sha256=kwargs["speech_packet_sha256"],
            task_contract=kwargs["task_contract"],
            instruction="RESOLVE instruction",
            family_tag=None,
            contracts=(),
            report_jsons=tuple(report.canonical_json for report in kwargs["reports"]),
            causal_dependency_contact_ids=tuple(
                f"{SCAN_CONTACT_PREFIX}{family}" for family in self.family_tags
            ),
            completion_token_ceiling=1024,
        )

    def parse_resolve_response(self, response_text, *, reports):
        assert len(reports) == 28
        return ParsedResolution(valid=True, calls=(), canonical_json=response_text)


class _Adapter:
    def build_sweep(self):
        return _Sweep()


class _Client:
    def __init__(self):
        self.contact_ids: list[str] = []

    def complete(self, messages, **kwargs):
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"][0]["type"] == "input_speech_features"
        contact_id = kwargs["agent_contact_id"]
        self.contact_ids.append(contact_id)
        if contact_id == RESOLVE_CONTACT_ID:
            return "[]"
        return "scan response"


class _Sink:
    run_id = "SAEA-A2T-G6-EXHAUSTIVE-FAMILY-SWEEP-FIXED16-V1"

    def __init__(self):
        self.records: list[tuple[str, str, object]] = []

    def emit(self, channel, record_id, payload):
        self.records.append((channel, record_id, payload))
        return "b" * 64


def _surface(launcher):
    samples = _samples(launcher)
    return SimpleNamespace(
        samples=samples,
        packet_bindings={
            sample.sample_id: {"packet_id": "packet", "sha256": "a" * 64}
            for sample in samples
        },
        speech_feature_tokens_by_sample={sample.sample_id: 100 for sample in samples},
    )


def _synchronous_workflow_runner(states, **kwargs):
    assert kwargs["branch_count"] == 28
    assert kwargs["slot_count"] == 2
    assert kwargs["queue_depth"] == 4
    for state in states:
        while kwargs["should_continue"](state):
            active = kwargs["prepare_wave"](state, SimpleNamespace())
            responses = tuple(
                kwargs["invoke_contact"](state, branch, 0)
                for branch in range(active)
            )
            assert all(
                set(response)
                == {"response_text", "slot_id", "response_sha256"}
                for response in responses
            )
            kwargs["aggregate_wave"](state, responses, SimpleNamespace())
    return list(states)


def _fake_prompt_fit(**kwargs):
    context = kwargs["context"]
    return {
        "status": "PASS",
        "refuse_contact": False,
        "contact_id": context.contact_id,
        "rendered_request_sha256": hashlib.sha256(
            kwargs["rendered_request"].encode("utf-8")
        ).hexdigest(),
        "text_tokens": 100,
        "speech_feature_tokens": 100,
        "special_token_reserve": 512,
        "completion_token_ceiling": context.completion_token_ceiling,
        "total_tokens": 1224,
        "remaining_tokens": 31_544,
    }


def test_fixed16_identity_and_execution_plan_use_manifest_hash_everywhere() -> None:
    launcher = _launcher()
    expected = "a99a64f004534516399c520c742132dc31d5c06cab5e59240653ff586a60fcb5"
    tiers = {sample_id: sample_id.split(":", 1)[0] for sample_id in launcher.SELECTED_IDS}

    assert len(launcher.SELECTED_IDS) == 16
    assert launcher._validate_selected_ids(tiers) == launcher.SELECTED_IDS
    assert launcher.SELECTED_SPLIT_SHA256 == expected
    assert launcher.SELECTED_RUN_SHA256 == expected
    assert launcher._verified_split().identity_hash == expected
    plan = launcher._execution_plan("attempt-g6-test", protocol_hash="c" * 64)
    assert plan.split_identity_hash == expected
    assert plan.planned_model_calls == 464
    assert plan.planned_speech_audio_seconds == 2600


def test_contact_and_concurrency_geometry_is_frozen() -> None:
    launcher = _launcher()

    assert launcher.SCAN_CONTACTS == 28
    assert launcher.RESOLVE_CONTACTS == 1
    assert launcher.MAX_CONTACTS == 29
    assert launcher.MAX_TOTAL_CONTACTS == 464
    assert launcher.SLOT_COUNT == launcher.MAX_CONCURRENT_REQUESTS == 2
    assert launcher.QUEUE_DEPTH == 4
    assert launcher.TEMPERATURE == 0
    assert launcher.REPAIR_CONTACTS == launcher.RETRIES == launcher.RESENDS == 0
    assert launcher.JITTER_TESTING is False


def test_all_launch_bindings_are_explicit_and_complete() -> None:
    launcher = _launcher()

    assert launcher._unbound_requirements() == ()
    assert launcher._require_bound_requirements() is None
    assert launcher.BASELINE_CONFIG_SHA256 == (
        "0e91cb0a5b3386b30726abd6bbee59455764bf0a66a35bee7a75c0d338a29784"
    )
    assert launcher.EXPERIMENT_CONFIG_SHA256 == (
        "1c9b666e31e5c9171db2f550de649b795906a864ceb64895586616b62755be0c"
    )
    assert launcher.COMPOSED_CONFIG_SHA256 == (
        "1cb12843cce818e3ce6fcb8d74213cbedf28de7bbd41435cd7ece3aff80b4007"
    )
    assert launcher.PROTOCOL_SHA256 == (
        "42d6589ee37d285d0af60c0521be1b83a6106ce643385ec79e9ffaa10e2204bd"
    )


def test_fake_client_schedule_runs_all_scans_before_one_resolve_per_row() -> None:
    launcher = _launcher()
    surface = _surface(launcher)
    client = _Client()
    sink = _Sink()

    summary = launcher._run_phase(
        root=Path("/data"),
        plan=SimpleNamespace(run_id=launcher.RUN_ID, protocol_hash="c" * 64),
        adapter=_Adapter(),
        client=client,
        surface=surface,
        trace_sink=sink,
        workflow_runner=_synchronous_workflow_runner,
        prompt_fit_measurer=_fake_prompt_fit,
    )

    assert len(summary.results) == 16
    assert sum(len(row.contacts) for row in summary.results) == 464
    for row in summary.results:
        contact_ids = tuple(contact.contact_id for contact in row.contacts)
        assert len(contact_ids) == 29
        assert all(value.startswith(SCAN_CONTACT_PREFIX) for value in contact_ids[:28])
        assert contact_ids[-1] == RESOLVE_CONTACT_ID
        assert row.final_response_text == "[]"
    assert len(client.contact_ids) == 464
    assert {channel for channel, _, _ in sink.records} == {"OBS", "ORG", "SUPPLY", "USE"}


def test_run_boundary_rejects_missing_contact_without_recontact() -> None:
    launcher = _launcher()

    def broken_runner(states, **kwargs):
        _synchronous_workflow_runner(states, **kwargs)
        states[0].contacts.pop()
        return states

    with pytest.raises(RuntimeError, match="exactly 464 contacts"):
        launcher._run_phase(
            root=Path("/data"),
            plan=SimpleNamespace(run_id=launcher.RUN_ID, protocol_hash="c" * 64),
            adapter=_Adapter(),
            client=_Client(),
            surface=_surface(launcher),
            trace_sink=_Sink(),
            workflow_runner=broken_runner,
            prompt_fit_measurer=_fake_prompt_fit,
        )


def test_scan_seal_is_nonfinal_and_final_manifest_source_is_resolve_only() -> None:
    launcher = _launcher()
    summary = launcher._run_phase(
        root=Path("/data"),
        plan=SimpleNamespace(run_id=launcher.RUN_ID, protocol_hash="c" * 64),
        adapter=_Adapter(),
        client=_Client(),
        surface=_surface(launcher),
        trace_sink=_Sink(),
        workflow_runner=_synchronous_workflow_runner,
        prompt_fit_measurer=_fake_prompt_fit,
    )

    scans = launcher._scan_state_rows(summary)
    finals = launcher._final_resolve_texts(summary)

    assert len(scans) == 16 * 28
    assert all(row["nonfinal"] is True for row in scans)
    assert all(row["stage"] == "SCAN" for row in scans)
    assert all("final_response_text" not in row for row in scans)
    assert tuple(finals) == launcher.SELECTED_IDS


def test_official_score_plan_is_one_complete_final16_manifest_job() -> None:
    launcher = _launcher()

    assert launcher._validate_official_score_plan(launcher.OFFICIAL_SCORE_PLAN)[
        "jobs"
    ][0]["job_id"] == "g6-final16"
    drifted = json.loads(json.dumps(launcher.OFFICIAL_SCORE_PLAN))
    drifted["jobs"].append(dict(drifted["jobs"][0]))
    with pytest.raises(RuntimeError, match="one complete final16"):
        launcher._validate_official_score_plan(drifted)


def test_main_separates_zero_contact_preflight_from_explicit_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    launcher = _launcher()
    context = {
        "commit": "d" * 40,
        "selected_ids": launcher.SELECTED_IDS,
        "prompt_report": {
            "scan": {"maximum_envelope_tokens": 1200},
            "resolve": {"maximum_envelope_tokens": 2200},
        },
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
    assert payload["planned_model_calls"] == 464
    assert calls == []

    assert launcher.main(["--run"]) == 0
    assert calls == [Path("/fixed/data")]
    with pytest.raises(SystemExit):
        launcher.main([])


def test_controller_policy_stays_bound_to_frozen_g6_core() -> None:
    launcher = _launcher()
    assert launcher.CONTROLLER_POLICY_ID == CONTROLLER_POLICY_ID


def test_phase_trace_payloads_use_disjoint_channel_prefixes() -> None:
    launcher = _launcher()
    sink = _Sink()
    state = SimpleNamespace(
        sample=SimpleNamespace(sample_id="sample-a"),
        trace_documents={
            "OBS": {"packet": "a"},
            "ORG": {"reports": []},
            "SUPPLY": {"contracts": []},
            "USE": {"resolution": "[]"},
        },
    )

    launcher._emit_phase_traces(state, sink)

    for channel, _record_id, payload in sink.records:
        prefix = channel.lower() + "_"
        assert payload
        assert all(key.startswith(prefix) for key in payload)


def test_recovery_reuses_exact_eight_contacts_and_sends_only_456() -> None:
    launcher = _launcher()
    surface = _surface(launcher)
    sweep = _Sweep()
    source_pairs = (
        (launcher.SELECTED_IDS[0], f"{SCAN_CONTACT_PREFIX}{sweep.family_tags[0]}"),
        (launcher.SELECTED_IDS[0], f"{SCAN_CONTACT_PREFIX}{sweep.family_tags[1]}"),
        (launcher.SELECTED_IDS[1], f"{SCAN_CONTACT_PREFIX}{sweep.family_tags[0]}"),
        (launcher.SELECTED_IDS[1], f"{SCAN_CONTACT_PREFIX}{sweep.family_tags[1]}"),
        (launcher.SELECTED_IDS[2], f"{SCAN_CONTACT_PREFIX}{sweep.family_tags[0]}"),
        (launcher.SELECTED_IDS[2], f"{SCAN_CONTACT_PREFIX}{sweep.family_tags[1]}"),
        (launcher.SELECTED_IDS[3], f"{SCAN_CONTACT_PREFIX}{sweep.family_tags[0]}"),
        (launcher.SELECTED_IDS[3], f"{SCAN_CONTACT_PREFIX}{sweep.family_tags[1]}"),
    )
    contacts = {}
    for index, (sample_id, contact_id) in enumerate(source_pairs, start=1):
        text = f"opaque-{index}"
        contacts[(sample_id, contact_id)] = launcher.RecoveryContact(
            request_id=f"g6fixed16-{index:04d}",
            sample_id=sample_id,
            contact_id=contact_id,
            packet_sha256="a" * 64,
            payload_sha256=f"{index:064x}",
            response_sha256=f"{index + 20:064x}",
            response_text_sha256=hashlib.sha256(text.encode()).hexdigest(),
            response_text=text,
            slot_id=index % 2,
            cost={"calls": 1, "audio_seconds": 1.0},
        )
    recovery = launcher.RecoveryBundle(
        source_attempt_id="attempt-source",
        source_attempt_sha256="b" * 64,
        source_trace_path=Path("/source.trace.jsonl"),
        source_trace_sha256="c" * 64,
        contacts=contacts,
        cost={
            "calls_used": 8,
            "audio_seconds_used": 8.0,
            "latency_seconds_total": 0.0,
            "prompt_tokens_total": 0,
            "completion_tokens_total": 0,
        },
    )
    client = _Client()

    summary = launcher._run_phase(
        root=Path("/data"),
        plan=SimpleNamespace(run_id=launcher.RUN_ID, protocol_hash="c" * 64),
        adapter=_Adapter(),
        client=client,
        surface=surface,
        trace_sink=_Sink(),
        workflow_runner=_synchronous_workflow_runner,
        prompt_fit_measurer=_fake_prompt_fit,
        recovery=recovery,
    )

    assert len(client.contact_ids) == 456
    assert sum(len(row.contacts) for row in summary.results) == 464
    recovered = [
        contact
        for row in summary.results
        for contact in row.contacts
        if contact.recovered
    ]
    assert len(recovered) == 8
    assert {(row.sample_id, row.contact_id) for row in recovered} == set(source_pairs)
