"""Configured candidate lookup follows the shared native execution and custody path."""
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime, FlightRuntimeError
from speech_aware_evidence_acquisition.core.model.native_history import project_native_history
from speech_aware_evidence_acquisition.core.model.transport import _speech_history_texts
from speech_aware_evidence_acquisition.rails.candidate_contract_lookup import (
    CandidateContractEvidence, CandidateContractLookupResult, CandidateContractRequest,
    MAX_CANDIDATE_IDS, TOOL_ID,
)
from speech_aware_evidence_acquisition.rails.core_client import _agent_history
from speech_aware_evidence_acquisition.rails.phase_tools import PhaseToolError, build_phase_tools
from test_phase_native_tools import NativeProgram, call, native_config, staged_native, Custody
from test_rails_runner import _knowledge_snapshot
from test_flight_native_tool_runtime import _runtime


class Provider:
    source_sha256 = "a" * 64
    candidate_ids = ("iot_hue_lightdim", "general_greet", "weather_query", "transport_taxi")

    def __init__(self):
        self.calls = []

    def lookup(self, candidate_ids):
        self.calls.append(candidate_ids)
        return CandidateContractLookupResult(
            request=CandidateContractRequest(candidate_ids),
            source_sha256=self.source_sha256,
            candidates=tuple(CandidateContractEvidence(
                candidate_id=key, operation=key, schema=(),
                contrast="No differentiating slot is recorded in this fixture.",
            ) for key in candidate_ids),
        ).validate()


def config(limit=3):
    result = native_config(TOOL_ID)
    for spec in result["phase_tools"].values():
        spec["candidate_limit"] = limit
    return result


def dispatcher(provider, *, limit=3, custody=None):
    return build_phase_tools(config(limit), NativeProgram(), snapshot=_knowledge_snapshot(),
                             candidate_contracts=provider, tool_contact=custody or Custody())


def test_candidate_schema_exposes_only_ids_and_registered_limit():
    tool = dispatcher(Provider())
    parameters = tool.native_tool_schemas()[0]["function"]["parameters"]
    assert parameters["required"] == ["candidate_ids"]
    assert set(parameters["properties"]) == {"candidate_ids"}
    ids = parameters["properties"]["candidate_ids"]
    assert ids["maxItems"] == 3 and ids["minItems"] == 1 and ids["uniqueItems"]
    assert "source_sha256" not in json.dumps(parameters)


# 33 was replaced by MAX_CANDIDATE_IDS + 1 on 2026-09-16: commit d3b8a767
# ("rails: make SLURP candidate width configurable") raised MAX_CANDIDATE_IDS
# from 32 to 64, so a limit of 33 is now legal and no longer documents a bad
# input; the parametrization must track the live ceiling, not a stale literal.
@pytest.mark.parametrize("bad", [None, 0, True, MAX_CANDIDATE_IDS + 1, "3"])
def test_candidate_limit_must_be_an_explicit_positive_integer(bad):
    bad_config = config(bad)
    if bad is None:
        for spec in bad_config["phase_tools"].values():
            del spec["candidate_limit"]
    with pytest.raises(PhaseToolError, match="candidate"):
        build_phase_tools(bad_config, NativeProgram(), snapshot=_knowledge_snapshot(),
                          candidate_contracts=Provider(), tool_contact=Custody())


def test_candidate_native_phases_cannot_change_the_limit_mid_run():
    values = config()
    values["phase_tools"]["decision-2"]["candidate_limit"] = 2
    with pytest.raises(PhaseToolError, match="identical"):
        build_phase_tools(values, NativeProgram(), snapshot=_knowledge_snapshot(),
                          candidate_contracts=Provider(), tool_contact=Custody())


@pytest.mark.parametrize("ids", [
    ["weather_query", "transport_taxi", "iot_hue_lightdim", "general_greet"],
    ["weather_query", "weather_query"], ["unknown"], [],
])
def test_invalid_or_unknown_candidates_return_bound_rejection_without_lookup(ids):
    provider, custody = Provider(), Custody()
    tool = dispatcher(provider, custody=custody)
    context = staged_native(call(TOOL_ID, {"candidate_ids": ids}))
    step = tool("decision-1", "decision-2", context)
    assert json.loads(step.state.content)["schema"] == "saea-phase-tool-error-v1"
    assert provider.calls == custody.calls == []


def test_actual_candidate_lookup_preserves_native_call_result_and_source():
    ids = ["general_greet", "iot_hue_lightdim"]
    provider = Provider()
    context = staged_native(call(TOOL_ID, {"candidate_ids": ids}))
    debits = []
    custody_runtime = SimpleNamespace(
        _samples=[SimpleNamespace(sample_id=context.sample_id)],
        _live_speech_source_bindings={context.sample_id: {
            "packet_id": context.query_state.speech_packet_id,
            "packet_sha256": context.query_state.speech_packet_sha256,
        }},
        _live_speech_units=lambda: None,
        _client=SimpleNamespace(record_tool_call=lambda **facts: debits.append(facts)),
        assert_generation_lease=lambda: None,
    )
    tool = dispatcher(provider, custody=lambda **facts:
                      FlightRuntime._record_phase_tool_contact(custody_runtime, **facts))
    step = tool("decision-1", "decision-2", context)
    assert provider.calls == [tuple(ids)] and debits == [{"count": 1}]
    document = json.loads(step.state.content)
    assert document["result"]["source_sha256"] == provider.source_sha256
    assert [x["candidate_id"] for x in document["result"]["candidates"]] == ids
    assert all(x["schema"] == [] for x in document["result"]["candidates"])
    states = (*context.agent_states, step.state)
    history = _agent_history(agent_state=[state.as_json() for state in states],
                             agent_contact_id="decision-2",
                             contact_instruction="Choose the final intent and entities.")
    texts = _speech_history_texts(history)
    packet = {"packet_id": context.query_state.speech_packet_id,
              "sha256": context.query_state.speech_packet_sha256, "role": "query"}
    payload = {
        "sample_id": context.sample_id, "speech_feature_parts": [packet],
        "speech_packet_sha256": packet["sha256"], "history": history,
        "tool_schemas": list(tool.native_tool_schemas()), "supplied_evidence": [],
        "decoding_params": {"tool_choice": "none", "parallel_tool_calls": False},
    }
    messages = [{"role": "system", "content": "Solve the speech task."},
                {"role": "user", "content": [
                    {"type": "input_speech_features", "speech_features": packet},
                    *({"type": "text", "text": text} for text in texts),
                ]}]
    rendered, _ = project_native_history(payload=payload, messages=messages, state_texts=texts)
    assert [x["role"] for x in rendered] == ["system", "user", "assistant", "tool", "user"]
    assert rendered[2]["tool_calls"] == call(TOOL_ID, {"candidate_ids": ids})
    result = json.loads(rendered[3]["content"])["result"]
    assert result == document["result"]
    assert rendered[3]["tool_call_id"] == rendered[2]["tool_calls"][0]["id"]
    assert "candidates" not in json.dumps(rendered[1])
    assert tool.receipt()["candidate_contracts"]["source_sha256"] == provider.source_sha256


def runtime_for_candidate(tmp_path, *, configured=True, source_sha256="a" * 64):
    runtime = _runtime(tmp_path)
    runtime._live_speech_config = None
    runtime._speech_observations = None
    runtime._experience_memory = None
    runtime._composed = SimpleNamespace(values=(
        {"candidate_contracts": {"source_sha256": source_sha256}} if configured else {}
    ))
    runtime._phase_tool_specs = lambda _policy: {
        "decision-1": {"mode": "native-tools",
                       "allowed_tools": (TOOL_ID,) if configured else ("knowledge",)}
    }
    runtime._phase_knowledge_catalog = lambda _snapshot: None
    calls, captured = [], {}
    provider = Provider()
    runtime._adapter = SimpleNamespace(candidate_contract_provider=lambda:
                                       (calls.append("prepare") or provider))
    def builder(values, program, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(native_enabled=True)
    runtime._phase_tool_builder = builder
    return runtime, provider, calls, captured


@pytest.mark.parametrize("configured", [False, True])
def test_runtime_prepares_candidate_provider_only_when_tool_is_configured(tmp_path, configured):
    runtime, provider, calls, captured = runtime_for_candidate(tmp_path, configured=configured)
    runtime._build_phase_tool_dispatcher("native-answer-or-tool-v1",
        SimpleNamespace(stop_rule="native-answer-or-tool"),
        binding={"knowledge_snapshot": object()}, sink=None, client=None)
    assert calls == (["prepare"] if configured else [])
    if configured:
        assert captured["candidate_contracts"] is provider
    else:
        assert "candidate_contracts" not in captured


def test_runtime_refuses_wrong_canonical_source_pin_before_dispatch(tmp_path):
    runtime, _provider, _calls, captured = runtime_for_candidate(tmp_path, source_sha256="b" * 64)
    with pytest.raises(FlightRuntimeError, match="candidate.*source"):
        runtime._build_phase_tool_dispatcher("native-answer-or-tool-v1",
            SimpleNamespace(stop_rule="native-answer-or-tool"),
            binding={"knowledge_snapshot": object()}, sink=None, client=None)
    assert captured == {}


def _construction_roster_pin(tmp_path, name, sample_ids, *, carrier="slurp"):
    import hashlib

    from speech_aware_evidence_acquisition.core.roster import write_roster
    from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash

    path = tmp_path / name
    document = {
        "carrier_lock_key": carrier,
        "items": [{"sample_id": item} for item in sample_ids],
        "split_identity_hash": split_identity_hash(prefixed(carrier, sample_ids)),
    }
    write_roster(document, path)
    return {"relpath": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _train_candidate_runtime(tmp_path, pins=None):
    runtime, provider, calls, captured = runtime_for_candidate(tmp_path)
    runtime._repo_root = tmp_path
    runtime._samples = (SimpleNamespace(sample_id="slurp:train:000301:audio-other"),)
    runtime._composed.values["carrier_lock_key"] = "slurp"
    spec = runtime._composed.values["candidate_contracts"]
    if pins is not None:
        spec["excluded_construction_rosters"] = pins
    runtime._adapter = SimpleNamespace(
        candidate_contract_provider=lambda **kwargs: (calls.append(kwargs) or provider)
    )
    return runtime, provider, calls, captured


def _dispatch_candidate(runtime):
    return runtime._build_phase_tool_dispatcher(
        "native-answer-or-tool-v1",
        SimpleNamespace(stop_rule="native-answer-or-tool"),
        binding={"knowledge_snapshot": object()}, sink=None, client=None,
    )


def test_train_contract_dispatch_excludes_siblings_and_both_pinned_folds(tmp_path):
    pins = [
        _construction_roster_pin(tmp_path, "a.json", [
            "slurp:train:000301:audio-a", "slurp:train:000301:audio-b",
        ]),
        _construction_roster_pin(tmp_path, "b.json", ["slurp:train:000302:audio-c"]),
    ]
    runtime, provider, calls, captured = _train_candidate_runtime(tmp_path, pins)
    _dispatch_candidate(runtime)
    assert calls == [{"excluded_construction_ids": (
        "slurp:train:000301", "slurp:train:000302",
    )}]
    assert captured["candidate_contracts"] is provider


@pytest.mark.parametrize("mode", ["absent", "empty", "uncovered", "duplicate", "tampered", "other"])
def test_train_contract_refuses_unbound_construction_before_provider_read(tmp_path, mode):
    pins = [_construction_roster_pin(tmp_path, "a.json", [
        "slurp:train:000302:audio-c" if mode == "uncovered" else "slurp:train:000301:audio-a"
    ], carrier="other" if mode == "other" else "slurp")]
    if mode == "absent":
        pins = None
    elif mode == "empty":
        pins = []
    elif mode == "duplicate":
        pins *= 2
    elif mode == "tampered":
        (tmp_path / "a.json").write_text("{}")
    runtime, _, calls, captured = _train_candidate_runtime(tmp_path, pins)
    with pytest.raises(FlightRuntimeError):
        _dispatch_candidate(runtime)
    assert calls == []
    assert captured == {}


def test_devel_contract_dispatch_preserves_legacy_no_argument_provider(tmp_path):
    runtime, provider, calls, captured = runtime_for_candidate(tmp_path)
    runtime._composed.values["carrier_lock_key"] = "slurp"
    runtime._samples = (SimpleNamespace(sample_id="slurp:devel:000001:audio-a"),)
    _dispatch_candidate(runtime)
    assert calls == ["prepare"]
    assert captured["candidate_contracts"] is provider
