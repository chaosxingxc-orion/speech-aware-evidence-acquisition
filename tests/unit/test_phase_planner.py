"""Exercise bounded review decisions through the shared controller without a model."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json

import pytest

from speech_aware_evidence_acquisition.core import judges as cj
from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails import phase_review as pr
from speech_aware_evidence_acquisition.rails.knowledge import QueryState
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.runner import AgentRuntimeContext
from speech_aware_evidence_acquisition.rails.phase_planner import (
    PhasePlannerError,
    build_phase_planner,
    emit_planner_records,
    load_phase_planner_specs,
    phase_planner_receipt,
)

_NUMERIC = cj.EARNINGS_NUMERIC_FORMAT_JUDGE_V1
_FLAGGED = "the amount was 1234.5.6 exactly"
_CLEAN = "the amount was twelve"


def _program():
    return replace(
        rc.default_phase_program("phase-draft-revise-v1"),
        stop_rule="stop-policy-optional-early-exit",
    )


def _config(**overrides):
    entry = {
        "planner_policy_id": "continue-on-flag-v1",
        "judges": [_NUMERIC],
        "minimum_severity": "warn",
    }
    entry.update(overrides)
    return {
        "phase_review": {"draft": {"judges": [_NUMERIC]}},
        "phase_planner": {"draft": entry},
    }


def _binding(config=None):
    config = _config() if config is None else config
    review_specs = pr.load_phase_review_specs(config, _program())
    reviewer = pr.build_review_for_phase(review_specs)
    specs = load_phase_planner_specs(config, _program(), review_specs)
    return specs, reviewer, build_phase_planner(specs, reviewer)


def _context(sample_id="s1"):
    query = QueryState(
        query_id=f"run:{sample_id}:step0",
        query_sample_id=sample_id,
        speech_packet_id=f"speech/{sample_id}",
        speech_packet_sha256="a" * 64,
        use_split_identity_hash="a" * 64,
        loop_step=0,
    ).validate()
    return AgentRuntimeContext(
        sample_id=sample_id, knowledge_snapshot_sha256="b" * 64,
        catalog_facet_ids=(), catalog_value_ids=(), query_state=query,
        task_contract="transcribe speech", agent_states=(),
        prior_response_sha256s=(), contact_index=0,
    )


def _material(name, context):
    return PhaseMaterial(
        instruction=f"Do {name} for {context.sample_id}",
        response_format=None, contact_id=f"c-{name}-{context.sample_id}",
        purpose=name,
    )


def _advance(response, reviewer, planner, sample_id="s1"):
    controller = rc.EvidenceAgentController(
        program=_program(), material_for_phase=_material,
        review_for_phase=reviewer, stop_policy=planner,
    )
    context = _context(sample_id)
    contact = controller.initial_contact(context)
    advance = controller.advance(context, contact, response)
    sealed = controller.sealed_states["draft"]
    staged = replace(
        context, agent_states=(sealed,),
        prior_response_sha256s=(sealed.source_response_sha256,),
    )
    return controller, advance, staged


def test_empty_config_preserves_historical_behavior():
    for config in ({}, {"phase_planner": {}}, {"phase_planner": None}):
        assert load_phase_planner_specs(config, _program(), {}) == {}
    assert build_phase_planner({}, None) is None
    assert phase_planner_receipt({}) == {}
    assert emit_planner_records(None, TraceBuffer("SAEA-PLANNER-TEST")) == 0


@pytest.mark.parametrize("entry", [
    None, [], "draft", {},
    {"planner_policy_id": "unknown", "judges": [_NUMERIC]},
    {"planner_policy_id": "continue-on-flag-v1", "judges": []},
    {"planner_policy_id": "continue-on-flag-v1", "judges": [_NUMERIC, _NUMERIC]},
    {"planner_policy_id": "continue-on-flag-v1", "judges": _NUMERIC},
    {"planner_policy_id": "continue-on-flag-v1", "judges": [3]},
    {"planner_policy_id": "continue-on-flag-v1", "judges": [_NUMERIC],
     "minimum_severity": "critical"},
    {"planner_policy_id": "continue-on-flag-v1", "judges": [_NUMERIC],
     "replacement": "twelve"},
])
def test_malformed_entry_is_refused(entry):
    config = _config()
    config["phase_planner"]["draft"] = entry
    reviews = pr.load_phase_review_specs(config, _program())
    with pytest.raises(PhasePlannerError):
        load_phase_planner_specs(config, _program(), reviews)


@pytest.mark.parametrize("block", [[], "draft", {"ghost": {}}, {"revise": {}}])
def test_unknown_final_or_invalid_phase_is_refused(block):
    config = _config()
    config["phase_planner"] = block
    reviews = pr.load_phase_review_specs(config, _program())
    with pytest.raises(PhasePlannerError):
        load_phase_planner_specs(config, _program(), reviews)


def test_unreviewed_phase_and_mandatory_full_program_are_refused():
    with pytest.raises(PhasePlannerError, match="review"):
        load_phase_planner_specs(_config(), _program(), {})
    reviews = pr.load_phase_review_specs(_config(), _program())
    with pytest.raises(PhasePlannerError, match="early-exit"):
        load_phase_planner_specs(
            _config(), rc.default_phase_program("phase-draft-revise-v1"), reviews,
        )


def test_flagged_draft_continues_and_only_core_successor_can_answer():
    specs, reviewer, planner = _binding()
    controller, advance, _ = _advance(_FLAGGED, reviewer, planner)
    assert advance.next_contact.contact_id == "c-revise-s1"
    assert advance.final_response_contact_id is None
    assert controller.review_verdicts["draft"][0].flagged
    next_context = replace(
        _context(), query_state=advance.next_query_state,
        agent_states=advance.new_agent_states, contact_index=1,
        prior_response_sha256s=(
            advance.new_agent_states[0].source_response_sha256,
        ),
    )
    final = controller.advance(next_context, advance.next_contact, _CLEAN)
    assert final.next_contact is None
    assert final.final_response_contact_id == "c-revise-s1"
    assert controller.sealed_states["revise"].content == _CLEAN


@pytest.mark.parametrize("response,minimum", [(_CLEAN, "warn"), (_FLAGGED, "block")])
def test_no_eligible_flag_retains_original_core_answer(response, minimum):
    _, reviewer, planner = _binding(_config(minimum_severity=minimum))
    controller, advance, _ = _advance(response, reviewer, planner)
    assert advance.next_contact is None
    assert advance.final_response_contact_id == "c-draft-s1"
    assert controller.sealed_states["draft"].content == response


def test_missing_and_mismatched_reviewer_are_refused():
    specs, _, _ = _binding()
    for reviewer in (None, lambda *args: (), pr.build_review_for_phase(
        pr.load_phase_review_specs(
            {"phase_review": {"draft": {"judges": [_NUMERIC],
              "params": {_NUMERIC: {"different": True}}}}}, _program(),
        ),
    )):
        with pytest.raises(PhasePlannerError, match="review"):
            build_phase_planner(specs, reviewer)


def test_stale_cross_sample_and_wrong_phase_contexts_are_refused():
    _, reviewer, planner = _binding()
    _, _, staged = _advance(_FLAGGED, reviewer, planner)
    state = staged.agent_states[-1]
    bad_contexts = [
        _context("other"),
        replace(staged, sample_id="other"),
        replace(staged, agent_states=(replace(
            state, source_response_sha256="c" * 64),)),
        replace(staged, agent_states=(replace(
            state, source_query_state_sha256="c" * 64),)),
        replace(staged, agent_states=(replace(
            state, state_kind="phase:other"),)),
    ]
    for context in bad_contexts:
        with pytest.raises(PhasePlannerError):
            planner(context, ("draft",))
    with pytest.raises(PhasePlannerError):
        planner(staged, ("ghost", "draft"))
    assert planner(staged, ("draft", "revise")) is False


def test_same_review_is_idempotent_but_changed_source_cannot_overwrite_decision():
    _, reviewer, planner = _binding()
    _, _, staged = _advance(_FLAGGED, reviewer, planner)
    assert planner(staged, ("draft",)) is False
    assert len(planner.decisions()) == 1
    with pytest.raises(PhasePlannerError, match="conflict"):
        _advance(_CLEAN, reviewer, planner)


def test_parallel_samples_keep_independent_decisions_and_hashes():
    _, reviewer, planner = _binding()
    def run(i):
        response = _FLAGGED if i % 2 else _CLEAN
        _, advance, _ = _advance(response, reviewer, planner, f"s{i}")
        return advance.next_contact is not None
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, range(16)))
    assert results == [bool(i % 2) for i in range(16)]
    assert len(planner.decisions()) == 16
    assert sum(row["use_decision"] == "continue" for row in planner.decisions().values()) == 8


def test_trace_and_receipt_are_content_free_and_report_real_decisions():
    specs, reviewer, planner = _binding()
    _, _, staged = _advance(_FLAGGED, reviewer, planner)
    sink = TraceBuffer("SAEA-PLANNER-TEST")
    assert emit_planner_records(planner, sink, record_namespace="example") == 1
    channel, record_id, payload = sink.records[0]
    assert channel == "USE"
    assert record_id == "s1/example/draft/planner"
    assert all(key.startswith("use_") for key in payload)
    assert payload["use_review_response_sha256"] == staged.agent_states[-1].source_response_sha256
    assert payload["use_decision"] == "continue"
    assert _FLAGGED not in json.dumps(payload)
    receipt = phase_planner_receipt(specs, planner)
    assert receipt["phases"][0]["rows_decided"] == 1
    assert receipt["phases"][0]["rows_continued"] == 1
    assert receipt["phases"][0]["rows_stopped"] == 0
    assert _FLAGGED not in json.dumps(receipt)


def test_registered_optional_program_leaves_original_program_identity_unchanged():
    program = rc.default_phase_program("phase-reviewed-repair-v1")
    assert program.phase_names() == ("draft", "revise")
    assert program.max_contacts == 2
    assert program.stop_rule == "stop-policy-optional-early-exit"
    assert rc.default_phase_program("phase-draft-revise-v1").stop_rule == "always-run-full-program"


@pytest.mark.parametrize("policy", ["fixed", "obs-agent-loop-ojw"])
def test_runtime_refuses_inert_planner_before_gate_or_model(tmp_path, policy):
    from test_flight_runtime import _make_runtime, _FakeGate
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntimeError
    gate = _FakeGate()
    runtime = _make_runtime(tmp_path, gate=gate, config_kwargs={
        "policy": policy, "baseline_extra": _config(),
    })
    with pytest.raises(FlightRuntimeError, match="phase_planner"):
        runtime.preflight()
    assert not gate.calls


def test_window_bridge_cannot_silently_accept_planner():
    from speech_aware_evidence_acquisition.reproduction.window_controller import (
        WindowControllerError, validate_window_controller,
    )
    with pytest.raises(WindowControllerError, match="phase_planner"):
        validate_window_controller({
            "policy": "obs-agent-loop-ojw",
            "obs_controller_program": "phase-direct-only-v1",
            "phase_planner": _config()["phase_planner"],
        })



@pytest.mark.parametrize("minimum,expected_calls", [("warn", 4), ("block", 2), (None, 4)])
def test_config_drives_public_runtime_wire_check(minimum, expected_calls, tmp_path):
    from test_flight_runtime import _make_runtime
    from test_rails_frozen_core_client import _World, _speech_feature_world, _binding as payload_binding
    from test_rails_runner import _FakeAdapter, _knowledge_snapshot
    from speech_aware_evidence_acquisition.rails.core_client import FrozenCoreClient
    from speech_aware_evidence_acquisition.rails.phase_runner import run_program

    world = _World(tmp_path)
    feature_root, _, packets = _speech_feature_world(world, tmp_path)
    config = _config(minimum_severity=minimum or "warn")
    if minimum is None:
        config["phase_planner"] = {}
    config["phase_material"] = {
        phase: {"instruction_template": f"probes/{phase}.txt",
                "predecessor_binding": "append-sealed-state" if phase == "revise" else "none"}
        for phase in ("draft", "revise")
    }
    runtime = _make_runtime(
        tmp_path, happy_path=True,
        config_kwargs={
            "arm": "speech-feature-query", "policy": "phase-reviewed-repair-v1",
            "model_extra": {"speech_feature_root": str(feature_root)},
            "baseline_extra": config,
        },
        adapter_cls=lambda _lock, _root: _FakeAdapter(samples=tuple(world.samples)),
        client_factory=FrozenCoreClient, phase_runner=run_program,
        payload_binding_factory=lambda **_kw: payload_binding(world),
    )
    dataset = runtime._repo_root / "configs" / "dataset" / "d.json"
    dataset.write_text(json.dumps({"carrier_lock_key": "fake-carrier", "split_id": "all"}))
    for phase in ("draft", "revise"):
        path = runtime._repo_root / "configs" / "probes" / f"{phase}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"Transcribe the speech during {phase}.")
    # Bind only synthetic media fixtures; all material, review, planning,
    # controller, execution, and wire accounting use the public runtime.
    runtime._load_knowledge_snapshot = _knowledge_snapshot
    runtime.speech_packet_bindings = lambda: packets
    runtime._speech_feature_root = lambda: feature_root
    receipt = runtime.wire_check(seal_and_score=False, response_text=_FLAGGED)
    assert receipt["model_contacts"] == 0
    assert receipt["contact_count"] == expected_calls
    assert len(receipt["request_body_sha256"]) == expected_calls
    dispatch = receipt["dispatch"]
    if minimum is None:
        assert "phase_planner" not in dispatch
        assert receipt["contacts_per_sample"] == 2
    else:
        assert "contacts_per_sample" not in receipt
        assert receipt["contacts_per_sample_ceiling"] == 2
        phase = dispatch["phase_planner"]["phases"][0]
        assert phase["rows_decided"] == 2
        assert phase["rows_continued"] == (2 if minimum == "warn" else 0)
        assert dispatch["contacts_per_sample_observed"] == [
            {"sample_id": "s1", "contacts": expected_calls // 2},
            {"sample_id": "s2", "contacts": expected_calls // 2},
        ]



def test_review_evidence_survives_a_later_stage_failure(tmp_path):
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.rails.phase_runner import run_continuous_program
    specs, reviewer, planner = _binding()
    sink = TraceBuffer("SAEA-PLANNER-FAILURE-TEST")
    def failing_runner(**kwargs):
        controller = kwargs["controller_registry"].resolve(kwargs["controller_policy_id"])("s1")
        context = _context()
        contact = controller.initial_contact(context)
        controller.advance(context, contact, _FLAGGED)
        raise RuntimeError("later phase refused")
    with pytest.raises(RuntimeError, match="later phase refused"):
        run_continuous_program(
            program=_program(),
            adapter=SimpleNamespace(serving_geometry=lambda: {"slots": 1}),
            plan=None, data_root=tmp_path, core_client=None, split_id="all",
            knowledge_snapshot=None, speech_packet_bindings={"s1": {}},
            trace_sink=sink, decoding_params={},
            material_for_phase=lambda phase, context, _sealed: _material(phase, context),
            review_for_phase=reviewer, stop_policy=planner, agent_runner=failing_runner,
        )
    assert len([row for row in sink.records if row[0] == "REVIEW"]) == 1
    assert phase_planner_receipt(specs, planner)["phases"][0]["rows_continued"] == 1
