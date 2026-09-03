"""Model-free tests for the fresh SELECT/FILL flight coordinator.

User journey: a researcher can prepare every exact request in a phase, prove
that all 104 fit the live context contract, and only then release individual
requests to the two-slot server.  One bad row leaves that phase with zero
generation sends and blocks every dependent phase.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import replace
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.a2t_response_schema import (
    A2tResponseSchemaError,
)
from speech_aware_evidence_acquisition.rails.a2t_stage_state import (
    SelectOccurrence,
    build_select_stage_envelope,
)


REPO = Path(__file__).resolve().parents[2]
LAUNCHER = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-select-fill-agentloop-104-v1/launcher/"
    "launch_a2t_select_fill_agentloop_104.py"
)


def _launcher():
    name = "test_a2t_select_fill_agentloop_launcher"
    spec = importlib.util.spec_from_file_location(name, LAUNCHER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sample_ids() -> tuple[str, ...]:
    return tuple(f"fresh:{index:03d}" for index in range(104))


def _body(sample_id: str, packet_id: str, *, max_tokens: int = 32) -> dict[str, object]:
    return {
        "messages": [
            {"role": "system", "content": "Return the exact JSON answer."},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_speech_features",
                        "speech_features": {
                            "packet_id": packet_id,
                            "sha256": "f" * 64,
                            "role": "query",
                        },
                    },
                    {"type": "text", "text": f"Sample binding: {sample_id}"},
                ],
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "exact_calls",
                "strict": True,
                "schema": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 7,
                    "items": {"type": "object"},
                },
            },
        },
        "temperature": 0,
        "top_p": 1,
        "max_tokens": max_tokens,
        "n": 1,
    }


def _requests(module, phase: str, *, max_tokens: int = 32):
    result = []
    for sample_id in _sample_ids():
        packet_id = sample_id.replace(":", "/", 1)
        result.append(
            module.PreparedGenerationRequest.from_body(
                phase=phase,
                sample_id=sample_id,
                packet_id=packet_id,
                body=_body(sample_id, packet_id, max_tokens=max_tokens),
                ground_sha256=(
                    hashlib.sha256(
                        b"Return the exact JSON answer."
                    ).hexdigest()
                    if phase
                    in {
                        module.JOINT_PHASE,
                        module.SELECT_PHASE,
                        module.REVISE_PHASE,
                        module.FILL_PHASE,
                    }
                    else None
                ),
            )
        )
    return tuple(result)


class _LiveChecks:
    def __init__(self, *, overflow_at: int | None = None) -> None:
        self.marker = "<|SPEECH|>"
        self.overflow_at = overflow_at
        self.apply_count = 0
        self.events: list[str] = []
        self.sent: list[bytes] = []

    def get_json(self, endpoint: str):
        self.events.append(endpoint)
        assert endpoint == "/props"
        return {
            "media_marker": self.marker,
            "default_generation_settings": {"n_ctx": 32_768},
        }

    def post_json(self, endpoint: str, payload: object):
        self.events.append(endpoint)
        if endpoint == "/apply-template":
            self.apply_count += 1
            assert isinstance(payload, dict) and "response_format" in payload
            return {"prompt": f"left{self.marker}right"}
        assert endpoint == "/tokenize"
        count = 24_600 if self.apply_count == self.overflow_at else 3
        return {"tokens": list(range(count))}

    def send(self, _url: str, body: bytes) -> bytes:
        self.events.append("send")
        self.sent.append(body)
        return b'{"choices":[{"message":{"content":"[{\\"name\\":\\"ok\\"}]"}}]}'


def test_protocol_freezes_the_fair_six_contact_schedule() -> None:
    module = _launcher()

    assert module.RUN_ID == "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5"
    assert module.SOURCE_RUN_ID == "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V2"
    assert module.PHASE_ORDER == (
        "M0_DIRECT",
        "OBS_SEMANTIC_STATE",
        "EMBED_OBS_TRANSCRIPT",
        "JOINT_ONE_CALL",
        "SELECT",
        "JOINT_DRAFT_REVISE",
        "FILL",
    )
    assert module.GENERATION_PHASES == (
        "JOINT_ONE_CALL",
        "SELECT",
        "JOINT_DRAFT_REVISE",
        "FILL",
    )
    assert module.REUSED_GENERATION_PHASES == (
        "M0_DIRECT",
        "OBS_SEMANTIC_STATE",
    )
    assert module.ALL_GENERATION_PHASES == (
        "M0_DIRECT",
        "OBS_SEMANTIC_STATE",
        "JOINT_ONE_CALL",
        "SELECT",
        "JOINT_DRAFT_REVISE",
        "FILL",
    )
    assert module.SAMPLE_COUNT == 104
    assert module.GENERATION_CONTACTS == 416
    assert module.FULL_FLIGHT_GENERATION_CONTACTS == 624
    assert module.EMBEDDING_LOGICAL_ITEMS == 104
    assert module.EMBEDDING_BATCH_SIZE == 32
    assert module.EMBEDDING_PHYSICAL_REQUESTS == 4
    assert module.TOP_K == 32
    assert module.SLOT_COUNT == 2
    assert module.QUEUE_DEPTH == 4
    assert module.PHYSICAL_CONTEXT_PER_SLOT == 32_768
    assert module.MAX_REQUIRED_WINDOW_TOKENS == 24_576
    assert module.CONTEXT_RESERVE == 8_192
    assert module.FINAL_MANIFEST_ROLES == (
        "direct_m0",
        "joint_one_call",
        "joint_draft_revise",
        "select_then_fill",
    )
    assert module.DIAGNOSTIC_PHASES == (
        "OBS_SEMANTIC_STATE",
        "SELECT",
    )
    assert module.CONFIG_SHA256 == module.sha256_json(module.protocol_config())


def test_visible_walk_allows_public_tool_fields_declared_inside_json_schema() -> None:
    module = _launcher()

    module._walk_visible(
        {
            "response_format": {
                "json_schema": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "reference": {"type": "string"},
                        },
                        "required": ["label", "reference"],
                    }
                }
            }
        }
    )


def test_visible_walk_still_refuses_forbidden_runtime_data_fields() -> None:
    module = _launcher()

    with pytest.raises(RuntimeError, match="forbidden runtime field 'label'"):
        module._walk_visible({"runtime_state": {"label": "hidden answer"}})


def test_transcript_embeddings_are_the_only_four_batches() -> None:
    module = _launcher()
    observations = {
        sample_id: module.ObservationArtifact(
            sample_id=sample_id,
            transcript=f"transcript {index}",
            state_sha256=f"{index + 1:064x}",
            source_response_sha256=f"{index + 201:064x}",
        )
        for index, sample_id in enumerate(_sample_ids())
    }

    batches = module.build_embedding_batches(observations, _sample_ids())

    assert tuple(map(len, batches)) == (32, 32, 32, 8)
    assert [item[0] for batch in batches for item in batch] == [
        f"embed:{sample_id}:transcript" for sample_id in _sample_ids()
    ]
    assert all("retrieval_query" not in item[0] for batch in batches for item in batch)


def test_candidate_identity_binds_scores_and_keeps_names_only_stage_hash() -> None:
    module = _launcher()
    names = tuple(f"tool{index:02d}" for index in range(32))
    first = module.CandidateSet(
        sample_id="fresh:000",
        tool_names=names,
        scores=tuple(float(32 - index) for index in range(32)),
        query_state_sha256="a" * 64,
    )
    second = module.CandidateSet(
        sample_id="fresh:000",
        tool_names=names,
        scores=tuple(float(31 - index) for index in range(32)),
        query_state_sha256="a" * 64,
    )

    assert first.candidate_set_sha256 != second.candidate_set_sha256
    assert first.candidate_order_sha256 == module.sha256_json(list(names))


def test_prepared_bytes_match_adapter_round_trip_and_transport_serialization() -> None:
    module = _launcher()
    packet_id = "fresh/000"
    body = _body("fresh:000", packet_id)
    request = module.PreparedGenerationRequest.from_body(
        phase=module.SELECT_PHASE,
        sample_id="fresh:000",
        packet_id=packet_id,
        body=body,
        ground_sha256=hashlib.sha256(b"Return the exact JSON answer.").hexdigest(),
    )

    # FrozenCoreAdapter first canonicalizes the full payload. The transport
    # then decodes it, rebuilds the two messages, and finally uses stdlib
    # json.dumps in insertion order for the physical HTTP body.
    decoding = {key: value for key, value in body.items() if key != "messages"}
    decoding["id_slot"] = 0
    canonicalized = json.loads(
        json.dumps(
            {
                "decoding_params": decoding,
                "speech_feature_parts": [
                    body["messages"][1]["content"][0]["speech_features"]
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    descriptor = canonicalized["speech_feature_parts"][0]
    messages = [
        body["messages"][0],
        {
            "role": "user",
            "content": [
                {
                    "type": "input_speech_features",
                    "speech_features": dict(descriptor),
                },
                body["messages"][1]["content"][1],
            ],
        },
    ]
    physical = {"messages": messages}
    physical.update(canonicalized["decoding_params"])

    assert request.body_bytes_by_slot[0] == json.dumps(physical).encode("utf-8")


def test_whole_phase_preflight_seals_two_slot_body_allowlist_before_sends() -> None:
    module = _launcher()
    live = _LiveChecks()
    requests = _requests(module, module.SELECT_PHASE)
    gate = module.WholePhaseRequestGate(
        expected_sample_ids=_sample_ids(),
        speech_packet_tokens={request.packet_id: 26 for request in requests},
        get_json=live.get_json,
        post_json=live.post_json,
        send=live.send,
    )

    receipt = gate.preflight_phase(module.SELECT_PHASE, requests)

    assert live.sent == []
    assert receipt.status == "COMPLETE_NO_GENERATION_SENT"
    assert receipt.row_count == 104
    assert tuple(map(len, receipt.allowed_body_hashes_by_slot)) == (104, 104)
    assert len({*receipt.allowed_body_hashes_by_slot[0], *receipt.allowed_body_hashes_by_slot[1]}) == 208
    assert live.events.count("/props") == 1
    assert live.events.count("/apply-template") == 104
    assert live.events.count("/tokenize") == 208
    assert all(audit.required_window_tokens <= 24_576 for audit in receipt.audits)

    responses = gate.dispatch_phase(receipt, requests)

    assert len(responses) == 104
    assert len(live.sent) == 104
    assert all("id_slot" in json.loads(body) for body in live.sent)
    assert {json.loads(body)["id_slot"] for body in live.sent} == {0, 1}

    tampered = replace(receipt, receipt_sha256="f" * 64)
    with pytest.raises(RuntimeError, match="independent recomputation"):
        module.validate_phase_preflight(
            tampered, requests, expected_sample_ids=_sample_ids()
        )


def test_one_late_overflow_means_zero_generation_sends_for_the_phase() -> None:
    module = _launcher()
    live = _LiveChecks(overflow_at=104)
    requests = _requests(module, module.FILL_PHASE)
    gate = module.WholePhaseRequestGate(
        expected_sample_ids=_sample_ids(),
        speech_packet_tokens={request.packet_id: 26 for request in requests},
        get_json=live.get_json,
        post_json=live.post_json,
        send=live.send,
    )

    with pytest.raises(RuntimeError, match="exceeds 24576"):
        gate.preflight_phase(module.FILL_PHASE, requests)

    assert live.sent == []
    assert gate.active_receipt is None


def test_local_schema_failure_is_found_before_any_live_preflight_contact() -> None:
    module = _launcher()
    live = _LiveChecks()
    requests = list(_requests(module, module.SELECT_PHASE))
    invalid = _body(requests[-1].sample_id, requests[-1].packet_id)
    invalid["response_format"] = {}
    requests[-1] = module.PreparedGenerationRequest.from_body(
        phase=module.SELECT_PHASE,
        sample_id=requests[-1].sample_id,
        packet_id=requests[-1].packet_id,
        body=invalid,
        ground_sha256=requests[-1].ground_sha256,
    )
    gate = module.WholePhaseRequestGate(
        expected_sample_ids=_sample_ids(),
        speech_packet_tokens={request.packet_id: 26 for request in requests},
        get_json=live.get_json,
        post_json=live.post_json,
        send=live.send,
    )

    with pytest.raises(RuntimeError, match="response_format"):
        gate.preflight_phase(module.SELECT_PHASE, tuple(requests))

    assert live.events == []
    assert live.sent == []


def test_preflighted_body_or_slot_mutation_is_refused_before_send() -> None:
    module = _launcher()
    live = _LiveChecks()
    requests = _requests(module, module.JOINT_PHASE)
    gate = module.WholePhaseRequestGate(
        expected_sample_ids=_sample_ids(),
        speech_packet_tokens={request.packet_id: 26 for request in requests},
        get_json=live.get_json,
        post_json=live.post_json,
        send=live.send,
    )
    receipt = gate.preflight_phase(module.JOINT_PHASE, requests)
    body = json.loads(requests[0].body_bytes_by_slot[0])
    body["temperature"] = 0.1
    mutated = json.dumps(body, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")

    with pytest.raises(RuntimeError, match="allowlist"):
        gate.send_preflighted(receipt, mutated)

    assert live.sent == []


def test_post_response_validator_rejects_wrong_argument_type() -> None:
    module = _launcher()
    packet_id = "fresh/000"
    body = _body("fresh:000", packet_id)
    body["response_format"] = {
        "type": "json_schema",
        "json_schema": {
            "name": "typed_call",
            "strict": True,
            "schema": {
                "type": "array",
                "minItems": 1,
                "maxItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"const": "setTimer"},
                        "arguments": {
                            "type": "object",
                            "properties": {"seconds": {"type": "integer"}},
                            "required": ["seconds"],
                            "additionalProperties": False,
                        },
                    },
                    "required": ["name", "arguments"],
                    "additionalProperties": False,
                },
            },
        },
    }
    request = module.PreparedGenerationRequest.from_body(
        phase=module.FILL_PHASE,
        sample_id="fresh:000",
        packet_id=packet_id,
        body=body,
        ground_sha256=hashlib.sha256(b"Return the exact JSON answer.").hexdigest(),
    )

    with pytest.raises(RuntimeError, match="wrong JSON type"):
        module.validate_response_against_request(
            b'[{"name":"setTimer","arguments":{"seconds":"five"}}]',
            request,
        )


def test_post_response_validator_rejects_exponent_overflow() -> None:
    module = _launcher()
    packet_id = "fresh/000"
    body = _body("fresh:000", packet_id)
    body["response_format"] = {
        "type": "json_schema",
        "json_schema": {
            "name": "finite_number",
            "strict": True,
            "schema": {"type": "number"},
        },
    }
    request = module.PreparedGenerationRequest.from_body(
        phase=module.FILL_PHASE,
        sample_id="fresh:000",
        packet_id=packet_id,
        body=body,
        ground_sha256=hashlib.sha256(b"Return the exact JSON answer.").hexdigest(),
    )

    with pytest.raises(RuntimeError, match="non-finite"):
        module.validate_response_against_request(b"1e9999", request)


def test_real_stage_barrier_verifies_every_source_hash() -> None:
    module = _launcher()
    sample_ids = _sample_ids()
    requests = _requests(module, module.SELECT_PHASE)
    audits = tuple(
        module.PromptBudgetAudit(
            sample_id=request.sample_id,
            phase=module.SELECT_PHASE,
            prompt_sha256="a" * 64,
            response_format_sha256="b" * 64,
            measured_text_tokens=10,
            speech_feature_tokens=26,
            completion_token_ceiling=32,
            required_window_tokens=70,
        )
        for request in requests
    )
    preflight = module.PhaseRequestPreflightReceipt.create(
        module.SELECT_PHASE, requests, audits
    )
    rows = tuple(
        module.GenerationResponse(
            sample_id=sample_id,
            phase=module.SELECT_PHASE,
            request_body_sha256=request.body_sha256_by_slot[index % 2],
            response_bytes=b'[{"name":"tool00"}]',
            source_query_state_sha256=f"{index + 1200:064x}",
        )
        for index, (sample_id, request) in enumerate(zip(sample_ids, requests, strict=True))
    )
    output = module.GenerationPhaseOutput(module.SELECT_PHASE, rows)
    phase_run = module.GenerationPhaseRun(
        module.SELECT_PHASE, requests, preflight, output
    )
    observations = {
        sample_id: module.ObservationArtifact(
            sample_id=sample_id,
            transcript="turn on the light",
            state_sha256=hashlib.sha256(sample_id.encode("ascii")).hexdigest(),
            source_response_sha256=f"{index + 300:064x}",
        )
        for index, sample_id in enumerate(sample_ids)
    }
    names = tuple(f"tool{index:02d}" for index in range(32))
    candidates = {
        sample_id: module.CandidateSet(
            sample_id=sample_id,
            tool_names=names,
            scores=tuple(1.0 - index / 100 for index in range(32)),
            query_state_sha256=observations[sample_id].state_sha256,
        )
        for sample_id in sample_ids
    }
    packets = {
        sample_id: {
            "packet_id": sample_id.replace(":", "/", 1),
            "sha256": f"{index + 900:064x}",
        }
        for index, sample_id in enumerate(sample_ids)
    }
    states = {
        sample_id: build_select_stage_envelope(
            sample_identity_sha256=hashlib.sha256(sample_id.encode("ascii")).hexdigest(),
            split_identity_sha256=module.SPLIT_IDENTITY_HASH,
            speech_packet_sha256=packets[sample_id]["sha256"],
            source_query_state_sha256=rows[index].source_query_state_sha256,
            source_response_sha256=rows[index].response_sha256,
            observation_state_sha256=observations[sample_id].state_sha256,
            observation_source_response_sha256=observations[
                sample_id
            ].source_response_sha256,
            source_request_body_sha256=rows[index].request_body_sha256,
            candidate_tool_names=names,
            ground_sha256=requests[index].ground_sha256,
            response_schema_sha256=module.sha256_json(
                requests[index].base_body["response_format"]
            ),
            predecessor_envelope_sha256=None,
            occurrences=(SelectOccurrence("occurrence-000", "tool00"),),
        )
        for index, sample_id in enumerate(sample_ids)
    }

    verified = module.validate_stage_barrier(
        states,
        expected_stage="SELECT",
        phase_run=phase_run,
        observations=observations,
        candidates=candidates,
        packet_bindings=packets,
        sample_ids=sample_ids,
    )

    assert tuple(verified) == sample_ids


def test_cli_is_zero_contact_by_default(capsys) -> None:
    module = _launcher()

    assert module.main(["--preflight-only"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "PREFLIGHT_ONLY_NO_CONTACT"
    assert report["contacts_made"] == {
        "generation": 0,
        "embedding": 0,
        "template": 0,
        "tokenizer": 0,
        "scorer": 0,
    }
    with pytest.raises(SystemExit, match="No contact is the default"):
        module.main([])


def _authority_document(module) -> dict[str, object]:
    return {
        "status": "CONTACT_AUTHORIZED",
        "run_id": module.RUN_ID,
        "config_sha256": module.CONFIG_SHA256,
        "roster_sha256": module.ROSTER_SHA256,
        "split_name": module.SPLIT_ID,
        "split_identity_hash": module.SPLIT_IDENTITY_HASH,
        "bundle_split_identity_hash": module.BUNDLE_SPLIT_IDENTITY_HASH,
        "bundle_protocol_sha256": module.BUNDLE_PROTOCOL_SHA256,
        "one_shot": True,
        "generation_contact_ceiling": module.GENERATION_CONTACTS,
        "embedding_physical_request_ceiling": 4,
        "hashes": {
            "coordinator_launcher_sha256": "a" * 64,
            "local_runtime_factory_sha256": "c" * 64,
        },
    }


def test_contact_ready_cli_loads_only_hash_bound_runtime_without_execution(
    tmp_path, monkeypatch, capsys
) -> None:
    module = _launcher()
    authority_path = tmp_path / "authority.json"
    authority_path.write_text(json.dumps(_authority_document(module)), encoding="utf-8")
    runtime = SimpleNamespace(
        assert_contact_ready_preflight=lambda: {
            "status": "CONTACT_READY_NO_CONTACT",
            "contacts_made": 0,
        }
    )
    monkeypatch.setattr(
        module,
        "sha256_file",
        lambda path: "b" * 64 if Path(path) == authority_path else "a" * 64,
    )
    monkeypatch.setattr(
        module,
        "_load_runtime_factory",
        lambda *_args, **_kwargs: lambda **_factory_kwargs: runtime,
    )

    assert module.main(
        [
            "--preflight-contact-ready",
            "--authority",
            str(authority_path),
            "--authority-sha256",
            "b" * 64,
            "--runtime-factory",
            "pinned.py:build_runtime",
        ]
    ) == 0
    assert json.loads(capsys.readouterr().out)["contacts_made"] == 0


def test_execute_cli_passes_runtime_owned_roster_and_packets(
    tmp_path, monkeypatch, capsys
) -> None:
    module = _launcher()
    authority_path = tmp_path / "authority.json"
    authority_path.write_text(json.dumps(_authority_document(module)), encoding="utf-8")
    runtime = SimpleNamespace(
        sample_ids=_sample_ids(),
        packet_bindings={
            sample_id: {
                "packet_id": sample_id.replace(":", "/", 1),
                "sha256": "f" * 64,
            }
            for sample_id in _sample_ids()
        },
        assert_contact_ready_preflight=lambda: {
            "status": "CONTACT_READY_NO_CONTACT"
        },
    )
    monkeypatch.setattr(
        module,
        "sha256_file",
        lambda path: "b" * 64 if Path(path) == authority_path else "a" * 64,
    )
    monkeypatch.setattr(
        module,
        "_load_runtime_factory",
        lambda *_args, **_kwargs: lambda **_factory_kwargs: runtime,
    )
    monkeypatch.setattr(
        module,
        "execute_contact_ready_flight",
        lambda **kwargs: {
            "status": "SEALED",
            "sample_count": len(kwargs["sample_ids"]),
            "packet_count": len(kwargs["packet_bindings"]),
        },
    )

    assert module.main(
        [
            "--execute",
            "--authority",
            str(authority_path),
            "--authority-sha256",
            "b" * 64,
            "--runtime-factory",
            "pinned.py:build_runtime",
        ]
    ) == 0
    assert json.loads(capsys.readouterr().out) == {
        "packet_count": 104,
        "sample_count": 104,
        "status": "SEALED",
    }


def test_authority_separates_core_and_bundle_split_identities() -> None:
    module = _launcher()
    authority = _authority_document(module)

    assert module._validate_execution_authority(authority) is authority
    authority["bundle_split_identity_hash"] = module.SPLIT_IDENTITY_HASH
    with pytest.raises(RuntimeError, match="identity or budget drift"):
        module._validate_execution_authority(authority)


def test_runtime_factory_loader_rejects_unpinned_paths() -> None:
    module = _launcher()

    with pytest.raises(RuntimeError, match="PATH.py:callable"):
        module._load_runtime_factory("missing-colon", expected_sha256="a" * 64)
    with pytest.raises(RuntimeError, match="path, hash, or callable"):
        module._load_runtime_factory(
            "elsewhere.py:build_runtime", expected_sha256="a" * 64
        )


def test_runtime_factory_loader_imports_the_exact_authorized_bytes(
    tmp_path, monkeypatch
) -> None:
    module = _launcher()
    factory_path = tmp_path / "runtime.py"
    factory_path.write_text(
        "def build_runtime(**kwargs):\n    return kwargs\n", encoding="ascii"
    )
    monkeypatch.setattr(module, "LOCAL_RUNTIME_FACTORY_PATH", factory_path)

    factory = module._load_runtime_factory(
        f"{factory_path}:build_runtime",
        expected_sha256=module.sha256_file(factory_path),
    )

    assert factory(marker="contact-free") == {"marker": "contact-free"}


class _CoordinatorRuntime:
    agent_executor_id = "openjiuwen-workflow-v1"
    slot_count = 2
    queue_depth = 4

    def __init__(self, module) -> None:
        self.module = module
        self.sample_ids = _sample_ids()
        self.events: list[str] = []
        self.outputs: dict[str, object] = {}

    def assert_attempt_unopened(self):
        self.events.append("unopened")

    def rehydrate_completed_prefix(self):
        self.events.append("rehydrate-prefix")
        runs = {}
        for phase in self.module.REUSED_GENERATION_PHASES:
            requests = _requests(self.module, phase)
            receipt = self.preflight_generation_phase(phase, requests)
            output = self.dispatch_generation_phase(phase, requests, receipt)
            runs[phase] = self.module.GenerationPhaseRun(
                phase, requests, receipt, output
            )
        observations = self.parse_observations(runs[self.module.OBS_PHASE].output)
        return self.module.RecoveredPrefixArtifacts(
            m0=runs[self.module.M0_PHASE],
            obs=runs[self.module.OBS_PHASE],
            observations=observations,
            source_report_sha256="d" * 64,
        )

    def start_generation(self, window):
        self.events.append(f"start-generation:{window}")

    def stop_generation(self, window):
        self.events.append(f"stop-generation:{window}")

    def start_embedding(self):
        self.events.append("start-embedding")

    def stop_embedding(self):
        self.events.append("stop-embedding")

    def generation_send_accounting(self):
        return {phase: 104 for phase in self.module.GENERATION_PHASES}

    def persist_post_embedding_checkpoint(self, observations, candidates):
        self.events.append("persist-post-embedding-checkpoint")
        assert len(observations) == len(candidates) == 104
        self.checkpoint_candidates = candidates
        return {"checkpoint_sha256": "e" * 64}

    def rehydrate_post_embedding_checkpoint(self, receipt, observations):
        self.events.append("rehydrate-post-embedding-checkpoint")
        assert receipt["checkpoint_sha256"] == "e" * 64
        assert len(observations) == 104
        return self.checkpoint_candidates

    def prepare_generation_phase(self, phase, **context):
        self.events.append(f"prepare:{phase}")
        if phase == self.module.REVISE_PHASE:
            assert len(context["predecessor_states"]) == 104
            assert {state.stage for state in context["predecessor_states"].values()} == {"JOINT_DRAFT"}
        if phase == self.module.FILL_PHASE:
            assert len(context["predecessor_states"]) == 104
            assert {state.stage for state in context["predecessor_states"].values()} == {"SELECT"}
        return _requests(self.module, phase)

    def preflight_generation_phase(self, phase, requests):
        self.events.append(f"preflight:{phase}")
        audits = tuple(
            self.module.PromptBudgetAudit(
                sample_id=request.sample_id,
                phase=phase,
                prompt_sha256="a" * 64,
                response_format_sha256="b" * 64,
                measured_text_tokens=10,
                speech_feature_tokens=26,
                completion_token_ceiling=32,
                required_window_tokens=70,
            )
            for request in requests
        )
        return self.module.PhaseRequestPreflightReceipt.create(phase, requests, audits)

    def dispatch_generation_phase(self, phase, requests, receipt):
        self.events.append(f"dispatch:{phase}")
        rows = tuple(
            self.module.GenerationResponse(
                sample_id=request.sample_id,
                phase=phase,
                request_body_sha256=request.body_sha256_by_slot[index % 2],
                response_bytes=b'[{"name":"ok"}]',
            )
            for index, request in enumerate(requests)
        )
        output = self.module.GenerationPhaseOutput(phase=phase, rows=rows)
        self.outputs[phase] = output
        return output

    def parse_observations(self, output):
        self.events.append("parse-observations")
        return {
            sample_id: self.module.ObservationArtifact(
                sample_id=sample_id,
                transcript="turn on the light",
                state_sha256=hashlib.sha256(sample_id.encode("ascii")).hexdigest(),
                source_response_sha256="c" * 64,
            )
            for sample_id in self.sample_ids
        }

    def embed_batch(self, batch):
        self.events.append(f"embed:{len(batch)}")
        return {contact_id: (0.1, 0.2) for contact_id, _text in batch}

    def retrieve_candidates(self, observations, vectors, *, top_k):
        self.events.append(f"retrieve:k{top_k}")
        names = tuple(f"tool{index:02d}" for index in range(32))
        return {
            sample_id: self.module.CandidateSet(
                sample_id=sample_id,
                tool_names=names,
                scores=tuple(1.0 - index / 100 for index in range(32)),
                query_state_sha256=observations[sample_id].state_sha256,
            )
            for sample_id in self.sample_ids
        }

    def parse_stage_states(self, stage, phase_run, observations, candidates, packets):
        self.events.append(f"seal-stage:{stage}")
        return {
            sample_id: SimpleNamespace(
                stage=stage,
                envelope_sha256=hashlib.sha256(
                    f"{stage}:{sample_id}".encode("ascii")
                ).hexdigest(),
            )
            for sample_id in self.sample_ids
        }

    def prompt_budget_audits(self):
        return tuple(
            audit
            for phase in self.module.GENERATION_PHASES
            for audit in self.preflight_generation_phase(
                phase, _requests(self.module, phase)
            ).audits
        )

    def seal_manifest(self, role, phase_run, extras):
        self.events.append(f"manifest:{role}")
        return {"role": role, "status": "COMPLETE", "complete_rows": 104}

    def seal_recovered_direct_manifest(self, role, phase_run, extras):
        return self.seal_manifest(role, phase_run, extras)

    def seal_flight(self, manifests, extras):
        self.events.append("seal-flight")
        return {
            "status": "SEALED",
            "manifests": manifests,
            "generation_contacts": 624,
            "embedding_logical_items": 104,
            "embedding_physical_requests": 4,
        }


def test_coordinator_enforces_both_barriers_and_only_four_final_manifests(monkeypatch) -> None:
    module = _launcher()
    runtime = _CoordinatorRuntime(module)
    packets = {
        sample_id: {
            "packet_id": sample_id.replace(":", "/", 1),
            "sha256": f"{index + 900:064x}",
        }
        for index, sample_id in enumerate(_sample_ids())
    }
    monkeypatch.setattr(
        module,
        "validate_stage_barrier",
        lambda states, **kwargs: states,
    )

    receipt = module.execute_contact_ready_flight(
        runtime=runtime,
        sample_ids=_sample_ids(),
        packet_bindings=packets,
    )

    assert receipt["status"] == "SEALED"
    assert tuple(item["role"] for item in receipt["manifests"]) == module.FINAL_MANIFEST_ROLES
    assert "start-generation:pre-embedding" not in runtime.events
    assert runtime.events.count(f"dispatch:{module.M0_PHASE}") == 1
    assert runtime.events.count(f"dispatch:{module.OBS_PHASE}") == 1
    assert runtime.events.index("stop-embedding") < runtime.events.index(
        "persist-post-embedding-checkpoint"
    )
    assert runtime.events.index("persist-post-embedding-checkpoint") < runtime.events.index(
        f"prepare:{module.JOINT_PHASE}"
    )
    assert runtime.events.index("rehydrate-post-embedding-checkpoint") < runtime.events.index(
        f"prepare:{module.JOINT_PHASE}"
    )
    assert runtime.events.index("seal-stage:JOINT_DRAFT") < runtime.events.index(
        f"prepare:{module.REVISE_PHASE}"
    )
    assert runtime.events.index("seal-stage:SELECT") < runtime.events.index(
        f"prepare:{module.FILL_PHASE}"
    )
    assert [event for event in runtime.events if event.startswith("manifest:")] == [
        f"manifest:{role}" for role in module.FINAL_MANIFEST_ROLES
    ]
    assert "manifest:obs_semantic_state" not in runtime.events
    assert "manifest:select" not in runtime.events


def test_recovery_coordinator_dispatches_only_the_416_remaining_generation_contacts(
    monkeypatch,
) -> None:
    module = _launcher()
    runtime = _CoordinatorRuntime(module)
    packets = {
        sample_id: {
            "packet_id": sample_id.replace(":", "/", 1),
            "sha256": f"{index + 900:064x}",
        }
        for index, sample_id in enumerate(_sample_ids())
    }
    monkeypatch.setattr(module, "validate_stage_barrier", lambda states, **kwargs: states)

    module.execute_contact_ready_flight(
        runtime=runtime,
        sample_ids=_sample_ids(),
        packet_bindings=packets,
    )

    dispatched_after_rehydration = [
        event.removeprefix("dispatch:")
        for event in runtime.events[runtime.events.index("start-embedding") :]
        if event.startswith("dispatch:")
    ]
    assert dispatched_after_rehydration == [
        module.JOINT_PHASE,
        module.SELECT_PHASE,
        module.REVISE_PHASE,
        module.FILL_PHASE,
    ]


def test_malformed_select_barrier_prevents_both_second_stage_phases(monkeypatch) -> None:
    module = _launcher()
    runtime = _CoordinatorRuntime(module)
    packets = {
        sample_id: {
            "packet_id": sample_id.replace(":", "/", 1),
            "sha256": f"{index + 900:064x}",
        }
        for index, sample_id in enumerate(_sample_ids())
    }

    def barrier(states, *, expected_stage, **_kwargs):
        if expected_stage == "SELECT":
            raise RuntimeError("SELECT barrier is incomplete")
        return states

    monkeypatch.setattr(module, "validate_stage_barrier", barrier)

    with pytest.raises(RuntimeError, match="SELECT barrier"):
        module.execute_contact_ready_flight(
            runtime=runtime,
            sample_ids=_sample_ids(),
            packet_bindings=packets,
        )

    assert f"prepare:{module.REVISE_PHASE}" not in runtime.events
    assert f"prepare:{module.FILL_PHASE}" not in runtime.events


@pytest.mark.parametrize(
    "failure",
    (
        A2tResponseSchemaError("local response schema is malformed"),
        ValueError("local recovered artifact is malformed"),
    ),
)
def test_execute_mode_aborts_open_attempts_for_local_value_failures(
    tmp_path,
    monkeypatch,
    failure,
) -> None:
    module = _launcher()
    authority_path = tmp_path / "authority.json"
    authority_path.write_text("{}\n", encoding="ascii")
    runtime = SimpleNamespace(
        sample_ids=(),
        packet_bindings={},
        aborted=[],
        assert_contact_ready_preflight=lambda: {
            "status": "CONTACT_READY_NO_CONTACT"
        },
    )
    runtime.abort_open_attempts = runtime.aborted.append
    authority = {
        "hashes": {
            "coordinator_launcher_sha256": module.sha256_file(module.Path(module.__file__)),
            "local_runtime_factory_sha256": "a" * 64,
        }
    }
    monkeypatch.setattr(module, "_validate_execution_authority", lambda _value: authority)
    monkeypatch.setattr(module, "_load_runtime_factory", lambda *_args, **_kwargs: (
        lambda **_kwargs: runtime
    ))
    monkeypatch.setattr(
        module,
        "execute_contact_ready_flight",
        lambda **_kwargs: (_ for _ in ()).throw(failure),
    )

    with pytest.raises(SystemExit, match="flight refused"):
        module.main(
            (
                "--execute",
                "--authority",
                str(authority_path),
                "--authority-sha256",
                module.sha256_file(authority_path),
                "--runtime-factory",
                "unused.py:factory",
            )
        )

    assert len(runtime.aborted) == 1
    assert type(failure).__name__ in runtime.aborted[0]


def test_execute_mode_aborts_once_for_an_arbitrary_framework_exception(
    tmp_path,
    monkeypatch,
) -> None:
    module = _launcher()
    authority_path = tmp_path / "authority.json"
    authority_path.write_text("{}\n", encoding="ascii")
    runtime = SimpleNamespace(
        sample_ids=(),
        packet_bindings={},
        aborted=[],
        assert_contact_ready_preflight=lambda: {
            "status": "CONTACT_READY_NO_CONTACT"
        },
    )
    runtime.abort_open_attempts = runtime.aborted.append
    authority = {
        "hashes": {
            "coordinator_launcher_sha256": module.sha256_file(
                module.Path(module.__file__)
            ),
            "local_runtime_factory_sha256": "a" * 64,
        }
    }
    monkeypatch.setattr(module, "_validate_execution_authority", lambda _value: authority)
    monkeypatch.setattr(
        module,
        "_load_runtime_factory",
        lambda *_args, **_kwargs: (lambda **_kwargs: runtime),
    )
    monkeypatch.setattr(
        module,
        "execute_contact_ready_flight",
        lambda **_kwargs: (_ for _ in ()).throw(Exception("framework escaped")),
    )

    with pytest.raises(SystemExit, match="flight refused: framework escaped"):
        module.main(
            (
                "--execute",
                "--authority",
                str(authority_path),
                "--authority-sha256",
                module.sha256_file(authority_path),
                "--runtime-factory",
                "unused.py:factory",
            )
        )

    assert runtime.aborted == ["Exception('framework escaped')"]
