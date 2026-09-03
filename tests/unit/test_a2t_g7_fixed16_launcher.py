"""Contact-free tests for the G7 fixed16 launcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.contracts.gate_exposure import (
    _parse_ledger_tables,
)


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g7-exhaustive-example-ground-fixed16-v1/launcher/"
    "launch_a2t_g7_fixed16.py"
)
SPEC = importlib.util.spec_from_file_location("g7_launcher", LAUNCHER)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def test_openjiuwen_runtime_version_is_frozen_to_installed_receipt() -> None:
    assert module.OPENJIUWEN_VERSION == "0.1.16.post2"


def _ground():
    bundles = []
    for family in range(28):
        tools = tuple(
            SimpleNamespace(
                tool_name=f"t_{family}_{index}",
                operation="Operate.",
                types=(),
                legal_key_skeletons=((),),
                patterns=(),
            )
            for index in range(6 if family < 12 else 5)
        )
        bundles.append(
            SimpleNamespace(
                family_tag=f"f-{family}",
                family_label=f"F {family}",
                tools=tools,
                tool_names=tuple(tool.tool_name for tool in tools),
                text=f"Family {family} examples.",
                sha256=f"{family:064x}",
                ascii_bytes=24,
            )
        )
    return SimpleNamespace(
        bundles=tuple(bundles),
        bundles_by_family={bundle.family_tag: bundle for bundle in bundles},
        tool_names=tuple(name for bundle in bundles for name in bundle.tool_names),
        sha256=module.GROUND_SHA256,
        receipt={"schema": "saea-a2t-construction-example-ground-receipt-v1"},
    )


def test_preflight_binds_identity_builder_and_exact_protocol() -> None:
    report = module.preflight_ground(_ground(), speech_feature_tokens_max=100)

    assert report["split_identity_hash"] == (
        "94a10c359dfe9e6a96cd63940c4dcb52fc7206e4c0e7d855733b21b69b987212"
    )
    assert report["contacts"] == 480
    assert report["family_count"] == 28
    assert report["tool_count"] == 152
    assert report["slots"] == report["max_concurrent_model_requests"] == 2
    assert report["queue_depth"] == 4
    assert report["audio_contacts_per_sample"] == 30
    assert report["text_only_contacts_per_sample"] == 0
    assert report["builder_commit"] == "7046ce6e7fbbba67ddbae5f122748e2158761e23"


def test_committed_structured_ground_round_trips_without_construction_rows() -> None:
    ground = module.load_ground()

    assert ground.sha256 == module.GROUND_SHA256
    assert len(ground.bundles) == 28
    assert len(ground.tool_names) == 152


def test_byte_upper_bound_preflight_measures_all_static_prompts() -> None:
    report = module.preflight_ground(_ground(), speech_feature_tokens_max=100)

    assert report["token_counter"] == "utf8-byte-construction-upper-bound"
    assert report["worst_observation_ascii_bytes"] == 1_024
    assert report["obs_prompt"]["completion_tokens"] == 512
    assert len(report["evidence_prompts"]) == 28
    assert all(row["remaining_tokens"] >= 8192 for row in report["evidence_prompts"])
    assert report["resolve_empty_assessment_base_prompt"]["remaining_tokens"] >= 8192
    assert report["resolve_worst_normalized_assessment_prompt"]["remaining_tokens"] >= 8192
    assert report["resolve_measurement"] == "dynamic-after-152-assessments-seal"


def test_committed_ground_worst_case_uses_full_observation_and_keeps_headroom() -> None:
    report = module.preflight_ground(module.load_ground(), speech_feature_tokens_max=182)

    assert report["worst_observation_ascii_bytes"] == 1_024
    assert max(row["total_tokens"] for row in report["evidence_prompts"]) == 13_040
    assert report["resolve_worst_normalized_assessment_prompt"] == {
        "completion_tokens": 1_024,
        "contact_id": "g7-resolve",
        "prompt_tokens": 23_070,
        "remaining_tokens": 8_674,
        "total_tokens": 24_094,
    }


def test_execution_plan_binds_exact_population_and_budget() -> None:
    plan = module.execution_plan("attempt-g7-unit")

    assert plan.split_identity_hash == module.SPLIT_IDENTITY_HASH
    assert plan.protocol_hash == module.PROTOCOL_SHA256
    assert plan.planned_model_calls == 480
    assert plan.planned_speech_audio_seconds == 2769


def test_exposure_table_pre_registers_exact_execution_plan() -> None:
    rows = _parse_ledger_tables(
        (ROOT / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    )
    matches = [
        row
        for row in rows
        if row["run/experiment id"] == module.RUN_ID
    ]

    assert len(matches) == 1
    row = matches[0]
    assert row["execution profile"] == "bounded-discovery-probe"
    assert row["split role"] == "discovery"
    assert row["split identity hash"] == module.SPLIT_IDENTITY_HASH
    assert row["consumed"] == "no"
    assert (row["calls"], row["speech audio seconds"], row["gpu hours"]) == (
        "480",
        "2769",
        "1.0",
    )


def test_exact_evidence_render_names_schema_once_and_resolve_is_official_array() -> None:
    ground = _ground()
    core = module.G7ExampleGround(ground.bundles)
    observation = module.parse_observation("A device action is requested.", core.tool_names)
    context = core.build_evidence_contexts(observation)[0]
    state = SimpleNamespace(
        stage="EVIDENCE", packet_binding={"packet_id": "p", "sha256": "a" * 64}
    )
    messages = module._contact_messages(state, context)

    assert "assessments" in messages[0]["content"]
    assert "tool_name" in messages[0]["content"]
    assert messages[0]["content"] not in str(messages[1])
    assert '"agent_control"' not in module._exact_request(
        messages, context, with_control=False
    )


def test_openjiuwen_phase_has_480_packet_bearing_contacts() -> None:
    ids = tuple(f"sample-{index}" for index in range(16))
    surface = module.RuntimeSurface(
        samples=tuple(SimpleNamespace(sample_id=value) for value in ids),
        packet_bindings={value: {"packet_id": value, "sha256": "b" * 64} for value in ids},
        speech_feature_tokens_by_sample={value: 10 for value in ids},
    )

    class Client:
        def __init__(self) -> None:
            self.calls = []
            self.messages = []

        def complete(self, messages, **kwargs):
            self.calls.append(kwargs)
            self.messages.append(messages)
            if kwargs.get("agent_contact_id") == "g7-obs":
                return "The speaker requests a device action."
            if str(kwargs.get("agent_contact_id", "")).startswith("g7-evidence-"):
                return "{}"
            return '{"calls":[]}'

    class Sink:
        def __init__(self) -> None:
            self.rows = []

        def emit(self, *args):
            self.rows.append(args)

    def runner(states, **kwargs):
        for state in states:
            while kwargs["should_continue"](state):
                count = kwargs["prepare_wave"](state, object())
                responses = tuple(
                    kwargs["invoke_contact"](state, index, 0) for index in range(count)
                )
                kwargs["aggregate_wave"](state, responses, object())
        return states

    client = Client()
    sink = Sink()
    summary = module.run_openjiuwen_phase(
        surface=surface,
        ground=_ground(),
        client=client,
        trace_sink=sink,
        workflow_runner=runner,
    )

    assert len(summary.results) == 16
    assert sum("speech_feature_sample_id" in call for call in client.calls) == 480
    assert sum("text_only_sample_id" in call for call in client.calls) == 0
    evidence_calls = [
        call
        for call in client.calls
        if str(call.get("agent_contact_id", "")).startswith("g7-evidence-")
    ]
    assert len(evidence_calls) == 448
    assert all(
        call["key_representation_id"] == "g7-example-ground:evidence"
        and call["matcher_policy_id"]
        == "saea-a2t-g7-exhaustive-example-ground-v1"
        for call in evidence_calls
    )
    assert all("speech_feature_sample_id" in call for call in evidence_calls)
    assert len(client.calls) == 480
    assert len(sink.rows) == 64
    for offset in range(0, 480, 30):
        row_calls = client.calls[offset : offset + 30]
        row_messages = client.messages[offset : offset + 30]
        sample_id = row_calls[0]["speech_feature_sample_id"]
        assert [call["agent_contact_id"] for call in row_calls][0] == "g7-obs"
        assert [call["agent_contact_id"] for call in row_calls][-1] == "g7-resolve"
        family_ids = [call["agent_contact_id"] for call in row_calls[1:29]]
        assert len(family_ids) == len(set(family_ids)) == 28
        for call, messages in zip(row_calls, row_messages, strict=True):
            assert call["speech_feature_sample_id"] == sample_id
            packets = [
                part["speech_features"]
                for part in messages[1]["content"]
                if part["type"] == "input_speech_features"
            ]
            assert packets == [
                {"packet_id": sample_id, "sha256": "b" * 64, "role": "query"}
            ]
        for messages in row_messages[1:29]:
            text_parts = [
                part for part in messages[1]["content"] if part["type"] == "text"
            ]
            assert len(text_parts) == 1
            assert text_parts[0]["text"].count("FAMILY CONSTRUCTION EXAMPLES") == 1


def test_recovery_reuses_bound_response_without_recontact() -> None:
    ground = _ground()
    sample_id = "sample-0"
    surface = module.RuntimeSurface(
        samples=(SimpleNamespace(sample_id=sample_id),),
        packet_bindings={sample_id: {"packet_id": sample_id, "sha256": "b" * 64}},
        speech_feature_tokens_by_sample={sample_id: 10},
    )
    obs_context = SimpleNamespace(contact_id="g7-obs", instruction=module._render_obs())
    state = SimpleNamespace(
        stage="OBS", packet_binding=surface.packet_bindings[sample_id]
    )
    messages = module._contact_messages(state, obs_context)
    recovered_text = "The speaker requests a device action."
    source = module.RecoveryContact(
        request_id="old-1",
        sample_id=sample_id,
        contact_id="g7-obs",
        semantic_sha256=module._message_semantic_sha256(
            sample_id, obs_context, messages
        ),
        response_text=recovered_text,
        response_sha256=module.hashlib.sha256(recovered_text.encode()).hexdigest(),
        slot_id=0,
        cost={},
    )
    recovery = module.RecoveryBundle(
        trace_path=Path("old.jsonl"),
        trace_sha256="c" * 64,
        contacts={(sample_id, "g7-obs"): source},
        cost={},
    )

    class Client:
        def __init__(self) -> None:
            self.count = 0

        def complete(self, _messages, **_kwargs):
            self.count += 1
            return "{}" if self.count <= 28 else '{"calls":[]}'

    class Sink:
        def emit(self, *_args):
            return None

    def runner(states, **kwargs):
        for current in states:
            while kwargs["should_continue"](current):
                count = kwargs["prepare_wave"](current, object())
                responses = tuple(
                    kwargs["invoke_contact"](current, index, 0)
                    for index in range(count)
                )
                kwargs["aggregate_wave"](current, responses, object())
        return states

    client = Client()
    with pytest.raises(RuntimeError, match="exactly 480"):
        module.run_openjiuwen_phase(
            surface=surface,
            ground=ground,
            client=client,
            trace_sink=Sink(),
            workflow_runner=runner,
            recovery=recovery,
        )

    assert client.count == 29


def test_recovery_reuses_four_obs_and_new_request_namespace_cannot_collide() -> None:
    ground = _ground()
    ids = tuple(f"sample-{index}" for index in range(16))
    surface = module.RuntimeSurface(
        samples=tuple(SimpleNamespace(sample_id=value) for value in ids),
        packet_bindings={value: {"packet_id": value, "sha256": "b" * 64} for value in ids},
        speech_feature_tokens_by_sample={value: 10 for value in ids},
    )
    contacts = {}
    for index, sample_id in enumerate(ids[:4], start=1):
        context = SimpleNamespace(contact_id="g7-obs", instruction=module._render_obs())
        state = SimpleNamespace(stage="OBS", packet_binding=surface.packet_bindings[sample_id])
        messages = module._contact_messages(state, context)
        response = "The speaker requests a device action."
        contacts[(sample_id, "g7-obs")] = module.RecoveryContact(
            request_id=f"g7fixed16-{index:04d}",
            sample_id=sample_id,
            contact_id="g7-obs",
            semantic_sha256=module._message_semantic_sha256(sample_id, context, messages),
            response_text=response,
            response_sha256=module.hashlib.sha256(response.encode()).hexdigest(),
            slot_id=0,
            cost={"calls": 1},
        )
    recovery = module.RecoveryBundle(
        trace_path=Path("old.jsonl"),
        trace_sha256=module.RECOVERY_TRACE_SHA256,
        contacts=contacts,
        cost={"calls_used": 4},
    )

    class Client:
        def __init__(self) -> None:
            self.count = 0

        def complete(self, _messages, **kwargs):
            self.count += 1
            if str(kwargs.get("agent_contact_id", "")).startswith("g7-evidence-"):
                return "{}"
            if kwargs.get("agent_contact_id") == "g7-obs":
                return "The speaker requests a device action."
            return '{"calls":[]}'

    class Sink:
        def emit(self, *_args):
            return None

    def runner(states, **kwargs):
        for current in states:
            while kwargs["should_continue"](current):
                count = kwargs["prepare_wave"](current, object())
                responses = tuple(
                    kwargs["invoke_contact"](current, index, 0)
                    for index in range(count)
                )
                kwargs["aggregate_wave"](current, responses, object())
        return states

    client = Client()
    summary = module.run_openjiuwen_phase(
        surface=surface,
        ground=ground,
        client=client,
        trace_sink=Sink(),
        workflow_runner=runner,
        recovery=recovery,
    )

    assert client.count == 476
    assert sum(contact.recovered for state in summary.results for contact in state.contacts) == 4
    assert all(
        not contact.request_id.startswith(module.RECOVERY_REQUEST_ID_PREFIX)
        for contact in contacts.values()
    )


def test_generated_manifest_is_bound_to_the_frozen_official_scorer(tmp_path: Path) -> None:
    manifest = tmp_path / "run-manifest.json"
    manifest.write_text('{"scorers": []}\n', encoding="utf-8")

    module._bind_official_scorers(manifest)

    assert json.loads(manifest.read_text(encoding="utf-8"))["scorers"] == [
        "a2t-toolcall"
    ]


def test_reseal_transport_validation_requires_complete_hash_bound_triples(
    tmp_path: Path,
) -> None:
    trace = tmp_path / "trace.jsonl"
    payload = {
        "request_id": "g7fixed16r-0001",
        "sample_id": "sample-1",
        "history": [{"contact_id": "g7-evidence-family-1"}],
    }
    request_hash = module._canonical_sha256(payload)
    response = "opaque response bytes"
    response_hash = module.hashlib.sha256(response.encode()).hexdigest()
    rows = [
        {
            "channel": "MODEL_REQUEST",
            "record_id": "g7fixed16r-0001/request",
            "payload": {"payload": payload, "payload_sha256": request_hash},
        },
        {
            "channel": "MODEL_RESPONSE",
            "record_id": "g7fixed16r-0001/response",
            "payload": {"text": response, "response_text_sha256": response_hash},
        },
        {
            "channel": "COST",
            "record_id": "g7fixed16r-0001/cost",
            "payload": {"calls": 1},
        },
    ]
    trace.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )

    contacts = module._validate_transport_triples(trace, expected_count=1)
    assert contacts == {("sample-1", "g7-evidence-family-1")}

    rows[1]["payload"]["response_text_sha256"] = "0" * 64
    trace.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="response hash"):
        module._validate_transport_triples(trace, expected_count=1)

    rows[1]["payload"]["response_text_sha256"] = response_hash
    rows[0]["payload"]["payload_sha256"] = "0" * 64
    trace.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="request payload hash"):
        module._validate_transport_triples(trace, expected_count=1)

    rows[0]["payload"]["payload_sha256"] = request_hash
    rows[2]["payload"]["calls"] = 2
    trace.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="cost triple"):
        module._validate_transport_triples(trace, expected_count=1)


def test_scorer_binding_refuses_a_different_scorer(tmp_path: Path) -> None:
    manifest = tmp_path / "run-manifest.json"
    manifest.write_text('{"scorers": ["asr-wer"]}\n', encoding="utf-8")

    with pytest.raises(RuntimeError, match="unexpected scorer"):
        module._bind_official_scorers(manifest)


def test_local_reseal_binds_exact_sources_and_makes_no_external_contact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "data"
    flight = root / "runs" / module.RUN_ID / module.RESEAL_FLIGHT_NAME
    run_dir = flight / "g7"
    trace_dir = run_dir / "transport-trace"
    trace_dir.mkdir(parents=True)
    outputs = run_dir / f"{module.RUN_ID}.outputs.jsonl"
    outputs.write_text(
        "".join(json.dumps({"sample_id": sample_id}) + "\n" for sample_id in ("a", "b")),
        encoding="utf-8",
    )
    trace = trace_dir / f"{module.RUN_ID}.trace.jsonl"
    trace.write_text("placeholder\n", encoding="utf-8")
    manifest = run_dir / f"{module.RUN_ID}.run-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "run_id": module.RUN_ID,
                "status": "COMPLETED",
                "scorers": [],
                "outputs": {"path": str(outputs), "sha256": module._sha256(outputs)},
                "attempt": {
                    "attempt_id": module.RESEAL_ATTEMPT_ID,
                    "state_path": "unused-in-unit-test",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    failure = flight / "failure-receipt.json"
    failure.write_text(
        json.dumps(
            {
                "run_id": module.RUN_ID,
                "attempt_id": module.RESEAL_ATTEMPT_ID,
                "error": "BundleError('run manifest scorers must be non-empty')",
                "transport_trace": str(trace),
                "transport_trace_sha256": module._sha256(trace),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    attempt = root / "attempts" / module.RUN_ID / f"{module.RESEAL_ATTEMPT_ID}.json"
    attempt.parent.mkdir(parents=True)
    attempt.write_text(
        json.dumps(
            {
                "run_id": module.RUN_ID,
                "attempt_id": module.RESEAL_ATTEMPT_ID,
                "state": "ABORTED",
                "actual": {"calls": 1},
                "failure_reason": "BundleError('run manifest scorers must be non-empty')",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    expected_hashes = {
        "failure-receipt.json": module._sha256(failure),
        f"g7/{module.RUN_ID}.outputs.jsonl": module._sha256(outputs),
        f"g7/{module.RUN_ID}.run-manifest.json": module._sha256(manifest),
        f"g7/transport-trace/{module.RUN_ID}.trace.jsonl": module._sha256(trace),
    }
    recovery = SimpleNamespace(contacts={("b", "g7-obs"): object()})
    monkeypatch.setattr(module, "MODEL_CONTACTS", 2)
    monkeypatch.setattr(module, "RESEAL_CURRENT_CONTACTS", 1)
    monkeypatch.setattr(module, "_verified_split", lambda: SimpleNamespace(ids=("a", "b")))
    monkeypatch.setattr(
        module,
        "_validate_transport_triples",
        lambda _path, *, expected_count: {("a", "g7-resolve")},
    )
    monkeypatch.setattr(module, "load_recovery_bundle", lambda _root, _path: recovery)
    monkeypatch.setattr(
        module,
        "verify_bundle",
        lambda path: SimpleNamespace(
            manifest=json.loads(path.read_text(encoding="utf-8")),
            outputs_rows=({}, {}),
            attempt_state="ABORTED",
        ),
    )

    receipt = module.reseal_failed_flight(
        root,
        flight,
        expected_hashes=expected_hashes,
        expected_attempt_sha256=module._sha256(attempt),
        recovery_trace=Path("old-trace.jsonl"),
    )

    assert receipt["status"] == "EXTERNALLY_RESEALED_COMPLETE_UNSCORED"
    assert receipt["contacts"] == {"current": 1, "recovered": 1, "total": 2}
    assert receipt["contacts_during_reseal"] == {
        "model": 0,
        "service": 0,
        "scorer": 0,
        "network": 0,
    }
    assert json.loads(manifest.read_text(encoding="utf-8"))["scorers"] == [
        "a2t-toolcall"
    ]
