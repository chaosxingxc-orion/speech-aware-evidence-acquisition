"""Model-free coverage for live whole-roster phase request fitting."""

from __future__ import annotations
import json
from dataclasses import dataclass
from types import SimpleNamespace
import pytest
from speech_aware_evidence_acquisition.contracts.plan import ExecutionPlan
from speech_aware_evidence_acquisition.core.preparation import (
    PreparationError,
    canonical_bytes,
)
from speech_aware_evidence_acquisition.core.preparation_fit import (
    build_live_phase_fit_gate,
    validate_live_phase_fit_config,
)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.core_client import PreparedCoreRequest

SHA = "a" * 64


def plan(**overrides):
    values = dict(
        run_id="SAEA-G6-LIVE-GENERATION-V1",
        attempt_id="attempt-g6-generation-v1",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="slurp",
        split_role="discovery",
        split_identity_hash=SHA,
        planned_model_calls=4,
        planned_gpu_hours=0.5,
        planned_speech_audio_seconds=100,
        protocol_hash="b" * 64,
    )
    values.update(overrides)
    return ExecutionPlan(**values).validate()


@dataclass(frozen=True)
class Sample:
    sample_id: str


class Transport:
    def render_request(self, raw):
        return {
            "messages": [{"role": "user", "content": "prompt <media>"}],
            "max_tokens": 4,
            "sample_id": json.loads(raw)["sample_id"],
        }


class Tokenizer:
    def __init__(self, **_kwargs):
        self.calls = []

    def request_json(self, method, path, payload):
        self.calls.append((method, path, payload))
        if (method, path) == ("GET", "/props"):
            return {"media_marker": "<media>"}
        if path == "/apply-template":
            return {"prompt": "text <media> tail"}
        if path == "/tokenize":
            return {"tokens": [1]}
        raise AssertionError((method, path))


class Runtime:
    def __init__(self, tmp_path, values):
        self._composed = SimpleNamespace(values=values)
        self._data_root = self._repo_root = self._runtime_root = tmp_path
        self._samples = (Sample("s1"), Sample("s2"))
        self._transport = Transport()
        self._session = SimpleNamespace(
            host="127.0.0.1",
            port=9999,
            session_id="serving-g6-test",
            model_files=(SimpleNamespace(path="decoder.gguf", sha256="c" * 64),),
        )
        self._adapter = SimpleNamespace(serving_geometry=lambda: {"slot_tokens": 128})
        self._gate = object()
        self.touches, self.unconsumed, self.lease_checks = [], [], 0

    def uses_speech_feature_packets(self):
        return True

    def assert_generation_lease(self):
        self.lease_checks += 1

    def _gate_touch(self, gate, fit_plan):
        assert gate is self._gate
        self.touches.append(fit_plan)

    def _require_exposure_row_unconsumed(self, run_id):
        self.unconsumed.append(run_id)

    def session_required_identity(self):
        return {"session": "serving-g6-test", "decoder": "c" * 64}

    def request_fit_inputs(self, payloads):
        return {
            "config_sha256": "d" * 64,
            "split_identity_hash": SHA,
            "sources": {"payloads": payloads},
        }


def values(**overrides):
    result = {
        "whole_roster_wave_barrier": True,
        "live_phase_fit": {
            "run_id": "SAEA-G6-LIVE-FIT-V1",
            "attempt_id": "attempt-g6-fit-v1",
            "contact_cap": 14,
        },
        "speech_feature_root": "/feature-root",
    }
    result.update(overrides)
    return result


def prepared(sample_id, phase):
    return PreparedCoreRequest(
        canonical_bytes(
            {
                "sample_id": sample_id,
                "history": [{"role": "control", "content": phase}],
                "speech_feature_parts": [
                    {"packet_id": sample_id, "sha256": SHA, "role": "query"}
                ],
                "decoding_params": {"max_tokens": 4},
            }
        ),
        object(),
    )


def test_live_gate_derives_registered_plan_and_fits_every_actual_wave(
    tmp_path, monkeypatch
):
    import speech_aware_evidence_acquisition.core.preparation_fit as fitting

    tokenizer = Tokenizer()
    monkeypatch.setattr(fitting, "packet_token_counts", lambda *_a, **_k: (1,))
    runtime = Runtime(tmp_path, values())
    program = default_phase_program("phase-direct-then-slots-v1")
    gate = build_live_phase_fit_gate(
        runtime, program, plan(), client_factory=lambda **_k: tokenizer
    )
    fit_plan = gate.execution_plan
    assert (fit_plan.run_id, fit_plan.attempt_id, fit_plan.planned_model_calls) == (
        "SAEA-G6-LIVE-FIT-V1",
        "attempt-g6-fit-v1",
        14,
    )
    assert fit_plan.protocol_hash == plan().protocol_hash
    assert fit_plan.split_identity_hash == plan().split_identity_hash
    assert fit_plan.planned_gpu_hours == plan().planned_gpu_hours
    assert fit_plan.planned_speech_audio_seconds == plan().planned_speech_audio_seconds
    assert runtime.touches == [fit_plan]
    assert runtime.unconsumed == [fit_plan.run_id]
    gate("direct", (prepared("s1", "direct"), prepared("s2", "direct")))
    gate(
        "slots",
        (prepared("s1", "slots actual state"), prepared("s2", "slots actual state")),
    )
    assert [receipt["phase"] for receipt in gate.receipts] == ["direct", "slots"]
    assert len(tokenizer.calls) == 14
    for phase in ("direct", "slots"):
        artifact = (
            tmp_path
            / "prepared"
            / fit_plan.run_id
            / fit_plan.attempt_id
            / f"{phase}.request-fit.json"
        )
        journal = artifact.with_name(artifact.name + ".contacts.jsonl")
        output = json.loads(artifact.read_text())["output"]
        assert output["every_request_fits"] is True
        assert output["contacts"] == 7
        assert output["generation_contacts"] == 0
        assert len(journal.read_text().splitlines()) == 7


def test_live_gate_refuses_wrong_order_or_incomplete_roster_before_contact(
    tmp_path, monkeypatch
):
    import speech_aware_evidence_acquisition.core.preparation_fit as fitting

    monkeypatch.setattr(fitting, "packet_token_counts", lambda *_a, **_k: (1,))
    tokenizer = Tokenizer()
    gate = build_live_phase_fit_gate(
        Runtime(tmp_path, values()),
        default_phase_program("phase-direct-then-slots-v1"),
        plan(),
        client_factory=lambda **_k: tokenizer,
    )
    with pytest.raises(PreparationError, match="order"):
        gate("slots", (prepared("s1", "slots"), prepared("s2", "slots")))
    with pytest.raises(PreparationError, match="full registered roster"):
        gate("direct", (prepared("s1", "direct"),))
    assert not tokenizer.calls
    assert not list(tmp_path.rglob("*.contacts.jsonl"))


@pytest.mark.parametrize(
    ("config", "error"),
    [
        (
            {"live_phase_fit": {"run_id": "fit", "attempt_id": "a", "contact_cap": 1}},
            "requires whole",
        ),
        ({"whole_roster_wave_barrier": True}, "requires run_id"),
        ({"whole_roster_wave_barrier": "true"}, "must be a boolean"),
        (
            {
                "whole_roster_wave_barrier": True,
                "live_phase_fit": {
                    "run_id": "fit",
                    "attempt_id": "a",
                    "contact_cap": 1,
                },
                "prepared_request_fit": {"relpath": "old", "sha256": SHA},
            },
            "cannot reuse",
        ),
    ],
)
def test_live_config_requires_explicit_unshared_barrier(config, error):
    with pytest.raises(PreparationError, match=error):
        validate_live_phase_fit_config(
            config, default_phase_program("phase-direct-then-slots-v1")
        )


def test_live_gate_refuses_wrong_registered_cap_before_lease_or_gate(tmp_path):
    runtime = Runtime(
        tmp_path,
        values(
            live_phase_fit={
                "run_id": "SAEA-G6-LIVE-FIT-V1",
                "attempt_id": "attempt-g6-fit-v1",
                "contact_cap": 13,
            }
        ),
    )
    with pytest.raises(PreparationError, match="cap must equal"):
        build_live_phase_fit_gate(
            runtime, default_phase_program("phase-direct-then-slots-v1"), plan()
        )
    assert not runtime.touches and not runtime.unconsumed and runtime.lease_checks == 0


def test_dispatch_forwards_live_optin_and_callback_to_continuous_runner(monkeypatch):
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    import speech_aware_evidence_acquisition.core.bundle.delivery_replay as delivery

    program = default_phase_program("phase-direct-then-slots-v1")
    monkeypatch.setattr(
        delivery, "validate_phase_delivery_sources", lambda *_a, **_k: None
    )
    captured = {}
    callback = SimpleNamespace(receipts=[])

    def factory(runtime, actual_program, actual_plan):
        assert runtime is instance
        assert actual_program is program
        assert actual_plan == plan()
        return callback

    def continuous(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            results=(object(), object()), controller_policy_id="program"
        )

    instance = object.__new__(FlightRuntime)
    instance._composed = SimpleNamespace(values=values())
    instance._live_phase_fit_factory = factory
    instance._phase_program_material = {
        "trace_sink": SimpleNamespace(),
        "supply_for_phase": None,
        "supply_specs": {},
        "review_for_phase": None,
        "review_specs": {},
        "knowledge_snapshot": object(),
        "speech_packet_bindings": {"s1": {}, "s2": {}},
        "material_for_phase": lambda *_a: None,
    }
    instance._phase_supply_seeds = lambda *_a, **_k: ({}, {})
    instance._continuous_phase_runner = continuous
    instance._phase_decoding_params = lambda: {"temperature": 0}
    instance._rows_from_phase_summaries = lambda *_a, **_k: [{"sample_id": "s1"}]
    instance._phase_summary_contacts = lambda _summary: 2
    instance._model = "model"
    instance._dataset = "dataset"
    instance._baseline = "baseline"
    instance._adapter = object()
    instance._data_root = object()
    instance._split_id = "split"
    instance._phase_program_material = dict(instance._phase_program_material)
    rows, contacts, kind, dispatch, _receipt = instance._dispatch_phase_program(
        object(), plan(), "phase-direct-then-slots-v1"
    )
    assert rows == [{"sample_id": "s1"}]
    assert contacts == 2 and kind == "phase-program"
    assert captured["whole_roster_wave_barrier"] is True
    assert captured["request_batch_gate"] is callback
    assert dispatch["whole_roster_wave_barrier"] is True
    assert dispatch["live_phase_fit_receipts"] == []


def test_live_gate_nonfit_second_phase_persists_receipt_and_refuses_retry(
    tmp_path, monkeypatch
):
    import speech_aware_evidence_acquisition.core.preparation_fit as fitting

    tokenizer = Tokenizer()
    monkeypatch.setattr(fitting, "packet_token_counts", lambda *_a, **_k: (1,))
    runtime = Runtime(tmp_path, values())
    gate = build_live_phase_fit_gate(
        runtime,
        default_phase_program("phase-direct-then-slots-v1"),
        plan(),
        client_factory=lambda **_k: tokenizer,
    )
    direct = (prepared("s1", "direct"), prepared("s2", "direct"))
    slots = (prepared("s1", "slots"), prepared("s2", "slots"))
    gate("direct", direct)
    runtime._adapter = SimpleNamespace(serving_geometry=lambda: {"slot_tokens": 1})
    with pytest.raises(PreparationError, match="exceed"):
        gate("slots", slots)
    calls_after_failure = len(tokenizer.calls)
    artifact = (
        tmp_path
        / "prepared"
        / gate.execution_plan.run_id
        / gate.execution_plan.attempt_id
        / "slots.request-fit.json"
    )
    assert json.loads(artifact.read_text())["output"]["every_request_fits"] is False
    assert artifact.with_name(artifact.name + ".contacts.jsonl").exists()
    with pytest.raises(PreparationError, match="already has contact or result"):
        gate("slots", slots)
    assert len(tokenizer.calls) == calls_after_failure


def test_live_gate_tokenizer_exception_leaves_journal_and_refuses_retry(
    tmp_path, monkeypatch
):
    import speech_aware_evidence_acquisition.core.preparation_fit as fitting

    class FailingTokenizer(Tokenizer):
        def request_json(self, method, path, payload):
            if (method, path) == ("GET", "/props"):
                self.calls.append((method, path, payload))
                raise RuntimeError("tokenizer unavailable")
            return super().request_json(method, path, payload)

    monkeypatch.setattr(fitting, "packet_token_counts", lambda *_a, **_k: (1,))
    tokenizer = FailingTokenizer()
    gate = build_live_phase_fit_gate(
        Runtime(tmp_path, values()),
        default_phase_program("phase-direct-then-slots-v1"),
        plan(),
        client_factory=lambda **_k: tokenizer,
    )
    direct = (prepared("s1", "direct"), prepared("s2", "direct"))
    with pytest.raises(RuntimeError, match="unavailable"):
        gate("direct", direct)
    calls_after_failure = len(tokenizer.calls)
    artifact = (
        tmp_path
        / "prepared"
        / gate.execution_plan.run_id
        / gate.execution_plan.attempt_id
        / "direct.request-fit.json"
    )
    assert not artifact.exists()
    assert artifact.with_name(artifact.name + ".contacts.jsonl").exists()
    with pytest.raises(PreparationError, match="already has contact or result"):
        gate("direct", direct)
    assert len(tokenizer.calls) == calls_after_failure


def test_each_phase_uses_fresh_client_after_idle_connection_expires(tmp_path, monkeypatch):
    import http.client
    import speech_aware_evidence_acquisition.core.preparation_fit as fitting

    class IdleConnectionTokenizer(Tokenizer):
        expired = False
        def request_json(self, method, path, payload):
            if self.expired:
                raise http.client.RemoteDisconnected("idle keep-alive closed")
            return super().request_json(method, path, payload)

    clients = []
    def factory(**kwargs):
        client = IdleConnectionTokenizer(**kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(fitting, "packet_token_counts", lambda *_a, **_k: (1,))
    runtime = Runtime(tmp_path, values())
    gate = build_live_phase_fit_gate(runtime, default_phase_program("phase-direct-then-slots-v1"), plan(), client_factory=factory)
    gate("direct", (prepared("s1", "direct"), prepared("s2", "direct")))
    clients[0].expired = True
    gate("slots", (prepared("s1", "actual direct result"), prepared("s2", "actual direct result")))
    assert len(clients) == 2
    assert [len(client.calls) for client in clients] == [7, 7]
    assert [row["phase"] for row in gate.receipts] == ["direct", "slots"]



def test_live_fit_uses_planner_active_roster_and_retains_full_budget_ceiling(tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.core.preparation_fit as fitting
    from test_phase_planner import _binding, _program, _advance, _FLAGGED, _CLEAN
    from speech_aware_evidence_acquisition.rails.phase_planner import PhasePlannerError

    tokenizer = Tokenizer()
    monkeypatch.setattr(fitting, "packet_token_counts", lambda *_a, **_k: (1,))
    runtime = Runtime(tmp_path, values())
    program = _program()
    _, reviewer, planner = _binding()
    def active(phase):
        return planner.active_sample_ids(
            phase, program.phase_names(), ("s1", "s2")
        )
    gate = build_live_phase_fit_gate(
        runtime, program, plan(), client_factory=lambda **_k: tokenizer,
        active_roster=active,
    )
    gate("draft", (prepared("s1", "draft"), prepared("s2", "draft")))
    with pytest.raises(PhasePlannerError, match="decision"):
        gate("revise", (prepared("s1", "revise"),))
    assert len(tokenizer.calls) == 7
    _advance(_FLAGGED, reviewer, planner, "s1")
    _advance(_CLEAN, reviewer, planner, "s2")
    with pytest.raises(PreparationError, match="roster"):
        gate("revise", (prepared("s1", "revise"), prepared("s2", "revise")))
    assert len(tokenizer.calls) == 7
    gate("revise", (prepared("s1", "revise"),))
    assert len(tokenizer.calls) == 11
    assert gate.execution_plan.planned_model_calls == 14
    artifact = tmp_path / "prepared" / gate.execution_plan.run_id / gate.execution_plan.attempt_id / "revise.request-fit.json"
    document = json.loads(artifact.read_text())
    assert document["output"]["contacts"] == 4
    assert document["output"]["generation_contacts"] == 0
    assert document["inputs"]["active_sample_ids"] == ["s1"]


def test_live_fit_native_active_roster_shrinks_monotonically(tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.core.preparation_fit as fitting

    tokenizer = Tokenizer()
    monkeypatch.setattr(fitting, "packet_token_counts", lambda *_a, **_k: (1,))
    runtime = Runtime(
        tmp_path,
        values(
            live_phase_fit={
                "run_id": "SAEA-G6-LIVE-FIT-V1",
                "attempt_id": "attempt-g6-fit-v1",
                "contact_cap": 21,
            }
        ),
    )
    gate = build_live_phase_fit_gate(
        runtime,
        default_phase_program("native-answer-or-tool-v1"),
        plan(),
        client_factory=lambda **_k: tokenizer,
        native_active_roster=True,
    )

    gate("decision-1", (prepared("s1", "first"), prepared("s2", "first")))
    gate("decision-2", (prepared("s2", "second"),))
    gate("final", (prepared("s2", "final"),))

    assert gate.execution_plan.planned_model_calls == 21
    assert len(tokenizer.calls) == 15
    fit_root = (
        tmp_path
        / "prepared"
        / gate.execution_plan.run_id
        / gate.execution_plan.attempt_id
    )
    assert [
        json.loads((fit_root / f"{phase}.request-fit.json").read_text())["inputs"][
            "active_sample_ids"
        ]
        for phase in ("decision-1", "decision-2", "final")
    ] == [["s1", "s2"], ["s2"], ["s2"]]


@pytest.mark.parametrize(
    "first_batch",
    [
        (prepared("s1", "first"),),
        (prepared("s2", "first"), prepared("s1", "first")),
        (prepared("s1", "first"), prepared("s1", "first")),
    ],
)
def test_live_fit_native_active_roster_requires_exact_unique_first_wave(
    tmp_path, monkeypatch, first_batch
):
    import speech_aware_evidence_acquisition.core.preparation_fit as fitting

    tokenizer = Tokenizer()
    monkeypatch.setattr(fitting, "packet_token_counts", lambda *_a, **_k: (1,))
    runtime = Runtime(
        tmp_path,
        values(
            live_phase_fit={
                "run_id": "SAEA-G6-LIVE-FIT-V1",
                "attempt_id": "attempt-g6-fit-v1",
                "contact_cap": 21,
            }
        ),
    )
    gate = build_live_phase_fit_gate(
        runtime,
        default_phase_program("native-answer-or-tool-v1"),
        plan(),
        client_factory=lambda **_k: tokenizer,
        native_active_roster=True,
    )

    with pytest.raises(PreparationError, match="exact registered roster"):
        gate("decision-1", first_batch)
    assert not tokenizer.calls


def test_live_fit_native_active_roster_refuses_resurrection(tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.core.preparation_fit as fitting

    tokenizer = Tokenizer()
    monkeypatch.setattr(fitting, "packet_token_counts", lambda *_a, **_k: (1,))
    runtime = Runtime(
        tmp_path,
        values(
            live_phase_fit={
                "run_id": "SAEA-G6-LIVE-FIT-V1",
                "attempt_id": "attempt-g6-fit-v1",
                "contact_cap": 21,
            }
        ),
    )
    gate = build_live_phase_fit_gate(
        runtime,
        default_phase_program("native-answer-or-tool-v1"),
        plan(),
        client_factory=lambda **_k: tokenizer,
        native_active_roster=True,
    )
    gate("decision-1", (prepared("s1", "first"), prepared("s2", "first")))
    gate("decision-2", (prepared("s2", "second"),))

    with pytest.raises(PreparationError, match="cannot grow or resurrect"):
        gate("final", (prepared("s1", "final"), prepared("s2", "final")))
    assert len(tokenizer.calls) == 11


def test_live_fit_native_active_roster_is_limited_to_native_program(tmp_path):
    with pytest.raises(PreparationError, match="native-answer-or-tool"):
        build_live_phase_fit_gate(
            Runtime(tmp_path, values()),
            default_phase_program("phase-direct-then-slots-v1"),
            plan(),
            native_active_roster=True,
        )


def test_dispatch_enables_native_active_roster_only_for_native_dispatcher(monkeypatch):
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    import speech_aware_evidence_acquisition.core.bundle.delivery_replay as delivery

    program = default_phase_program("native-answer-or-tool-v1")
    monkeypatch.setattr(
        delivery, "validate_phase_delivery_sources", lambda *_a, **_k: None
    )
    captured = {}
    callback = SimpleNamespace(receipts=[])
    dispatcher = SimpleNamespace(native_enabled=True, receipt=lambda: {})

    def factory(runtime, actual_program, actual_plan, **options):
        assert runtime is instance
        assert actual_program is program
        assert actual_plan == plan()
        captured["fit_options"] = options
        return callback

    def continuous(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            results=(
                SimpleNamespace(sample_id="s1", contacts=(object(),)),
                SimpleNamespace(sample_id="s2", contacts=(object(), object())),
            ),
            controller_policy_id="program",
        )

    instance = object.__new__(FlightRuntime)
    instance._composed = SimpleNamespace(
        values=values(
            live_phase_fit={
                "run_id": "SAEA-G6-LIVE-FIT-V1",
                "attempt_id": "attempt-g6-fit-v1",
                "contact_cap": 21,
            }
        )
    )
    instance._live_phase_fit_factory = factory
    instance._phase_tool_dispatcher = dispatcher
    instance._phase_program_material = {
        "trace_sink": SimpleNamespace(),
        "supply_for_phase": None,
        "supply_specs": {},
        "review_for_phase": None,
        "review_specs": {},
        "knowledge_snapshot": object(),
        "speech_packet_bindings": {"s1": {}, "s2": {}},
        "material_for_phase": lambda *_a: None,
    }
    instance._phase_supply_seeds = lambda *_a, **_k: ({}, {})
    instance._continuous_phase_runner = continuous
    instance._phase_decoding_params = lambda: {"temperature": 0}
    instance._rows_from_phase_summaries = lambda *_a, **_k: [{"sample_id": "s1"}]
    instance._phase_summary_contacts = lambda _summary: 2
    instance._result_kind = lambda: "task-answer"
    instance._model = "model"
    instance._dataset = "dataset"
    instance._baseline = "baseline"
    instance._adapter = object()
    instance._data_root = object()
    instance._split_id = "split"

    instance._dispatch_phase_program(
        object(), plan(), "native-answer-or-tool-v1"
    )

    assert captured["fit_options"] == {"native_active_roster": True}
    assert captured["request_batch_gate"] is callback
