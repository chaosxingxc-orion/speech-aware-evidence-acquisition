"""Whole-system summaries use verified sources and the existing request path."""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.preparation import load_artifact
from speech_aware_evidence_acquisition.core.roster import split_identity_hash
from speech_aware_evidence_acquisition.data.splits import prefixed
from speech_aware_evidence_acquisition.rails.prepared_feedback import (
    PreparedFeedbackError, load_prepared_feedback,
)
from speech_aware_evidence_acquisition.rails.system_summary_context import (
    PREPARED_SUMMARY_SCHEMA, build_system_summary_contexts,
    prepare_system_summary_contexts,
)
from test_system_semantic_trajectory import source


def pin(root, name, document):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(document).encode()
    path.write_bytes(raw)
    return {"relpath": name, "sha256": hashlib.sha256(raw).hexdigest()}


@pytest.fixture
def summary_world(tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.rails.system_summary_context as module

    data = tmp_path / "data"
    value = source()
    sid = "slurp:train:1"
    def renamed(item):
        if isinstance(item, str):
            return item.replace("s1", sid)
        if isinstance(item, list):
            return [renamed(v) for v in item]
        if isinstance(item, dict):
            return {renamed(k): renamed(v) for k, v in item.items()}
        return item
    value.bundle.trace_records = renamed(value.bundle.trace_records)
    value = replace(value, sample_ids=(sid,), phase_results=renamed(value.phase_results),
                    output_rows=renamed(value.output_rows))
    identity = split_identity_hash(prefixed("slurp", (sid,)))
    value.plan.split_identity_hash = identity
    value.plan.carrier_lock_key = "slurp"
    roster = {"schema": "saea-roster-receipt-v1", "carrier_lock_key": "slurp",
              "split_role": "discovery", "roster_role": "construction",
              "split_identity_hash": identity, "items": [{"sample_id": sid, "stratum": "all"}]}
    binding = {
        "schema": "saea-system-summary-source-v1", "round_id": "round-1",
        "source_repo_root": str(tmp_path / "frozen-source"),
        "manifest": pin(data, "run/manifest.json", value.bundle.manifest),
        "phases": pin(data, "run/phases.json", {}),
        "construction_roster": pin(data, "roster.json", roster),
    }
    calls = []
    def verified(**kwargs):
        calls.append(kwargs)
        return value
    monkeypatch.setattr(module, "verify_native_episode_source", verified)
    source_pin = pin(data, "source.json", binding)
    return data, value, binding, source_pin, calls


def prepared(world):
    data, _value, binding, source_pin, _calls = world
    path = data / "prepared/summary.json"
    receipt = prepare_system_summary_contexts(source_pin, path, data_root=data)
    spec = {"schema": PREPARED_SUMMARY_SCHEMA,
            "artifact": {"relpath": "prepared/summary.json", "sha256": receipt["sha256"]},
            "source_bindings": source_pin, "language": "en", "max_context_bytes": 2000000}
    return spec, receipt


def load(world, spec, **changes):
    data, value, binding, _, _ = world
    options = dict(repo_root=Path(__file__).resolve().parents[2], data_root=data,
                   sample_ids=value.sample_ids,
                   construction_roster_sha256=binding["construction_roster"]["sha256"],
                   result_kind="artifact", artifact_role="training-feedback-proposal")
    options.update(changes)
    return load_prepared_feedback(spec, **options)


def test_whole_episode_is_rebuilt_on_cold_and_warm_reads(summary_world):
    spec, receipt = prepared(summary_world)
    states, custody = load(summary_world, spec)
    data, value, binding, source_pin, calls = summary_world
    text = next(iter(states.values())).content
    episode = json.loads(text)["trajectory"]
    assert len(episode["contacts"]) == 5
    assert len(episode["tool_records"]) == 2
    assert episode["delivered_text"] == value.output_rows[value.sample_ids[0]]["text"]
    assert [v["stage"] for v in episode["trajectory"]["role_visits"]] == [
        "perception", "solver", "review", "planner"]
    assert custody["input_stage"] == "complete-system-trajectory-summary"
    assert custody["runtime_input_contract"] == "shared-speech-feature-artifact"
    assert custody["source_bindings_sha256"] == source_pin["sha256"]
    assert calls[-1]["repo_root"] == Path(binding["source_repo_root"])
    before = (data / "prepared/summary.json").read_bytes()
    warm = prepare_system_summary_contexts(source_pin, data / "prepared/summary.json", data_root=data)
    assert warm["cache"] == "warm"
    assert len(calls) == 3
    assert (data / "prepared/summary.json").read_bytes() == before
    document = json.loads(before)
    assert load_artifact(data / "prepared/summary.json", expected_sha256=receipt["sha256"],
                         kind="system-summary-contexts", inputs=document["inputs"])


@pytest.mark.parametrize("change", ["role", "cohort", "roster", "maximum", "language", "source", "artifact"])
def test_wrong_authority_or_incomplete_context_is_refused(summary_world, change):
    spec, _ = prepared(summary_world)
    options = {}
    if change == "role":
        options["result_kind"] = "task-answer"
    elif change == "cohort":
        options["sample_ids"] = ("slurp:train:999",)
    elif change == "roster":
        options["construction_roster_sha256"] = "f" * 64
    elif change == "maximum":
        spec["max_context_bytes"] = 5
    elif change == "language":
        spec["language"] = "zh"
    else:
        key = "source_bindings" if change == "source" else "artifact"
        spec[key]["sha256"] = "f" * 64
    with pytest.raises(PreparedFeedbackError):
        load(summary_world, spec, **options)


@pytest.mark.parametrize("change", ["evaluation", "partial", "wrong-split", "not-train", "outside-data"])
def test_source_must_match_complete_train_construction(summary_world, change):
    data, value, binding, source_pin, _calls = summary_world
    if change == "evaluation":
        value.plan.split_role = "confirmatory"
    elif change == "partial":
        object.__setattr__(value, "sample_ids", value.sample_ids + ("slurp:train:2",))
    elif change == "wrong-split":
        value.plan.split_identity_hash = "f" * 64
    elif change == "not-train":
        doc = json.loads((data / "roster.json").read_text())
        doc["items"][0]["sample_id"] = "slurp:devel:1"
        doc["split_identity_hash"] = split_identity_hash(prefixed("slurp", ("slurp:devel:1",)))
        binding["construction_roster"] = pin(data, "other-roster.json", doc)
        source_pin = pin(data, "other-source.json", binding)
    else:
        binding["manifest"]["relpath"] = "../outside.json"
        source_pin = pin(data, "other-source.json", binding)
    with pytest.raises(PreparedFeedbackError):
        build_system_summary_contexts(source_pin, data_root=data)


def test_gold_and_terminal_feedback_are_separate_from_summary(summary_world):
    data, value, _, source_pin, _ = summary_world
    value.bundle.manifest["scores"] = {"reference": "GOLD-SENTINEL", "reward": 91}
    value.phase_results[value.sample_ids[0]]["private_annotation"] = "GOLD-SENTINEL"
    value.bundle.trace_records["private-score"] = {"value": "REWARD-SENTINEL"}
    document = build_system_summary_contexts(source_pin, data_root=data)
    text = json.dumps(document["contexts"])
    assert "GOLD-SENTINEL" not in text and "REWARD-SENTINEL" not in text
    assert "correct_answer" not in text
    assert document["model_contacts_added"] == document["scorer_contacts_added"] == 0


def test_warm_source_refusal_precedes_cached_artifact(summary_world, monkeypatch):
    import speech_aware_evidence_acquisition.rails.system_summary_context as module
    spec, _ = prepared(summary_world)
    def aborted(**_kwargs):
        raise ValueError("source is ABORTED")
    monkeypatch.setattr(module, "verify_native_episode_source", aborted)
    with pytest.raises(PreparedFeedbackError, match="ABORTED"):
        load(summary_world, spec)


@pytest.mark.parametrize("text_only", [False, True])
def test_prepared_complete_episode_reaches_actual_shared_fit_and_send(summary_world, tmp_path, text_only):
    exercise_shared_fit_and_send(summary_world, tmp_path, text_only)


def exercise_shared_fit_and_send(world_inputs, tmp_path, text_only, *, prepared_spec=None,
                                 baseline=None, comparison=False, group_update=False, batch_update=False, wire_view=False, knowledge_edit=False,
                                 baseline_overrides=None,
                                 output_text="The whole episode ends in ACCEPT."):
    """Exercise the production binding, executor, request gate and artifact output."""
    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    from speech_aware_evidence_acquisition.core.preparation_fit import boundary_identity
    from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.phase_material import (
        build_material_for_phase, load_phase_material_specs, render_static_instruction,
        resolve_response_formats,
    )
    from speech_aware_evidence_acquisition.rails.phase_runner import run_continuous_program
    from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
    from test_artifact_result_kind import _plan as artifact_plan
    from test_rails_frozen_core_client import (
        _CapturingTransport, _World, _client, _plan, _speech_feature_world,
    )
    from test_rails_runner import _FakeAdapter, _knowledge_snapshot

    if not openjiuwen_available():
        pytest.skip("OpenJiuwen unavailable")
    data, value, binding, _, _ = world_inputs
    spec = prepared_spec if prepared_spec is not None else prepared(world_inputs)[0]
    repo = tmp_path / "updater-repo"
    roster_path = repo / "docs/receipts/rosters/construction.json"
    roster_path.parent.mkdir(parents=True)
    roster_path.write_bytes((data / binding["construction_roster"]["relpath"]).read_bytes())
    project = Path(__file__).resolve().parents[2]
    values = json.loads((project / "configs/baseline/system-trajectory-summary-v1.json").read_text())
    if text_only:
        values = json.loads((project / "configs/baseline/system-trajectory-summary-text-v1.json").read_text())
    if baseline is not None:
        values = json.loads((project / "configs/baseline" / (baseline + ".json")).read_text())
    if baseline_overrides is not None:
        values.update(baseline_overrides)
    values.update(
        carrier_lock_key="slurp", prepared_training_feedback=spec,
        artifact_result={"schema": "saea-artifact-result-binding-v1",
                         "role": "training-feedback-proposal", "construction_roster": {
                             "repo_relpath": "docs/receipts/rosters/construction.json",
                             "sha256": binding["construction_roster"]["sha256"]}},
        live_phase_fit={"run_id": "summary-fit-fixture", "attempt_id": "fixture", "contact_cap": 4},
    )
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values=values)
    runtime._samples = tuple(SimpleNamespace(sample_id=s) for s in value.sample_ids)
    runtime._plan = artifact_plan(value.plan.split_identity_hash)
    runtime._repo_root, runtime._data_root = repo, data
    program = default_phase_program(values["policy"])
    states, receipt = runtime._prepared_feedback_binding(program)
    assert receipt["state_bindings"][0]["sample_id"] == value.sample_ids[0]
    materials = load_phase_material_specs(values, program)
    formats = resolve_response_formats(materials, {}, data)
    text = render_static_instruction(materials["direct"], project, {}, data)
    material = build_material_for_phase(
        materials, program_id=program.program_id,
        static_text_by_phase={"direct": text}, response_format_by_phase=formats,
    )
    world = _World(tmp_path / "consumer")
    world.samples = world.samples[:1]
    feature_root, _packet, packets = (
        (None, None, {}) if text_only
        else _speech_feature_world(world, tmp_path / "consumer")
    )
    sid = value.sample_ids[0]
    world.samples = [replace(world.samples[0], sample_id=sid)]
    packets = ({sid: {"packet_id": world.samples[0].audio_ref.path,
                      "sha256": world.samples[0].audio_ref.sha256}}
               if text_only else {sid: packets["s1"]})
    transport = _CapturingTransport(lambda _payload: output_text)
    plan = _plan(planned_model_calls=1)
    client, _, _ = _client(world, tmp_path / "consumer", plan=plan, transport=transport,
                          arm=values["arm"], **({} if text_only else {
                              "speech_feature_root": feature_root,
                              "speech_packet_bindings": packets}))
    fitted, trace = [], TraceBuffer(plan.run_id)
    adapter = _FakeAdapter(samples=tuple(world.samples))
    if text_only:
        def forbidden(*_args, **_kwargs):
            raise AssertionError("Text summaries must not load a fresh task prompt or ontology")
        adapter.assemble_prompt = forbidden
        adapter.build_task_contract = forbidden
    if text_only:
        template_rel = "configs/" + values["phase_material"]["direct"]["instruction_template"]
        template = repo / template_rel
        template.parent.mkdir(parents=True)
        template.write_bytes((project / template_rel).read_bytes())
        runtime._lock = {}
        runtime._adapter = adapter
        runtime._split_id = "all"
        runtime.execution_unit_roster = lambda: None
        runtime._load_knowledge_snapshot = _knowledge_snapshot
        runtime._phase_tool_trace_sink = None
        bound = runtime._default_phase_program_binding(program, client)
        assert bound["query_source"] == "speech_audio"
        assert bound["speech_packet_bindings"] == packets
        assert bound["initial_feedback_states"] == states
        material = bound["material_for_phase"]
    def fit(phase, requests):
        assert phase == "direct" and not transport.calls
        fitted.extend(r.as_payload() for r in requests)
    try:
        summary = run_continuous_program(
            program=program, adapter=adapter,
            plan=plan, data_root=world.data_root, core_client=client, split_id="all",
            knowledge_snapshot=_knowledge_snapshot(), speech_packet_bindings=packets,
            trace_sink=trace, decoding_params={"max_tokens": 512}, material_for_phase=material,
            query_source="speech_audio" if text_only else "speech_features",
            result_kind="artifact", whole_roster_wave_barrier=True,
            request_batch_gate=fit, slot_count=1, queue_depth=1, initial_feedback_states=states,
        )
        assert len(transport.calls) == len(fitted) == 1
        sent = transport.calls[0]
        assert boundary_identity((fitted[0],)) == boundary_identity((sent,))
        assert sent["history"][0]["content"] == states[sid].content
        assert text == sent["history"][-1]["content"]
        if text_only:
            assert sent["prepared_text"] == "saea-prepared-text-v1"
            assert "speech_feature_parts" not in sent and "raw_speech_query" not in sent
            assert receipt["runtime_input_contract"] == "shared-prepared-text-artifact"
            assert "Task contract:" not in sent["task_instruction"]
        else:
            assert sent["speech_feature_parts"]
        context = json.loads(sent["history"][0]["content"])
        if knowledge_edit:
            assert context["stage"] == "complete-system-knowledge-edit"
            assert receipt["input_stage"] == "complete-system-knowledge-edit"
        elif batch_update:
            assert context["stage"] == "complete-system-batch-update"
            assert context["group_operations"] and context["existing_experiences"] == []
            assert receipt["input_stage"] == "complete-system-batch-update"
        elif group_update:
            assert context["stage"] == "complete-system-group-update"
            assert context["new_experiences"] and context["existing_experiences"] == []
            assert receipt["input_stage"] == "complete-system-group-update"
        elif comparison:
            assert context["stage"] == "complete-system-semantic-comparison"
            assert [a["terminal_feedback"]["fp"] for a in context["attempts"]] == [0, 2]
            assert [a["terminal_feedback"]["utility"] for a in context["attempts"]] == [0, -1]
            assert receipt["input_stage"] == "complete-system-semantic-comparison"
        else:
            episode = context["trajectory"]
            if wire_view:
                from speech_aware_evidence_acquisition.analysis.shared_json import restore_json

                assert episode["schema"] == "saea-complete-episode-wire-view-v1"
                restored = restore_json(episode["context"])
                assert len(restored["contacts"]) == 5 and len(restored["actual_tool_records"]) == 2
            else:
                assert len(episode["contacts"]) == 5 and len(episode["tool_records"]) == 2
        assert all(row.metrics == {} for row in summary.results)
        assert not any(kind == "SCORE" for kind, _, _ in trace.records)
        runtime._output_rows = FlightRuntime._rows_from_phase_summaries(
            (summary,), policy=program.program_id)
        runtime._artifact_result_binding = {"role": "training-feedback-proposal"}
        runtime._artifact_content_validator = None
        runtime._plan = plan
        runtime._composed = SimpleNamespace(values={**values, "carrier_lock_key": "fake-carrier"})
        rows = runtime._canonical_output_rows(client)
        assert rows[0]["text"] == output_text
        assert rows[0]["sample_id"] == sid
        return {"sent": sent, "fitted": fitted[0], "canonical": rows}
    finally:
        client.close()


def test_public_preparation_entrypoint_uses_same_artifact(summary_world, capsys):
    from speech_aware_evidence_acquisition.rails.system_summary_context import main

    data, _, _, source_pin, _ = summary_world
    args = ["--data-root", str(data), "--source-relpath", source_pin["relpath"],
            "--source-sha256", source_pin["sha256"], "--output-relpath", "prepared/cli.json"]
    assert main(args) == 0
    cold = json.loads(capsys.readouterr().out)
    assert main(args) == 0
    warm = json.loads(capsys.readouterr().out)
    assert cold["sha256"] == warm["sha256"]
    assert cold["cache"] == "cold" and warm["cache"] == "warm"


def test_rehashed_prepared_output_substitution_is_rejected(summary_world):
    from speech_aware_evidence_acquisition.core.preparation import digest

    spec, _ = prepared(summary_world)
    data = summary_world[0]
    path = data / spec["artifact"]["relpath"]
    envelope = json.loads(path.read_text())
    envelope["output"]["contexts"][0]["model_context"]["trajectory"]["delivered_text"] = "Injected"
    envelope["output_sha256"] = digest(envelope["output"])
    raw = json.dumps(envelope).encode()
    path.write_bytes(raw)
    spec["artifact"]["sha256"] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(PreparedFeedbackError, match="differs"):
        load(summary_world, spec)


def test_summary_baseline_replaces_original_slu_answer_instruction(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.instructions import resolve_active_task_instruction
    from speech_aware_evidence_acquisition.core.flight.runtime import phase_program_system_text
    from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpSample
    from speech_aware_evidence_acquisition.rails.adapters.slurp_runtime import RuntimeSlurpAdapter
    from speech_aware_evidence_acquisition.rails.obs import AudioRef
    import speech_aware_evidence_acquisition.rails.adapters.slurp as slurp

    project = Path(__file__).resolve().parents[2]
    values = json.loads((project / "configs/baseline/system-trajectory-summary-v1.json").read_text())
    text = resolve_active_task_instruction(values, project, {}, tmp_path)
    assert text and "summary" in text
    monkeypatch.setattr(slurp, "load_cached_slurp_contract", lambda *_: "Legal task ontology.")
    sample = SlurpSample(
        sample_id="slurp:train:1", audio_ref=AudioRef(path="audio/a.wav", sha256="a"*64),
        audio_seconds=1., utterance_id="1", media_relpath="audio/a.wav",
        scenario="", action="", intent="", entities=(),
    )
    adapter = RuntimeSlurpAdapter(
        {}, tmp_path, repo_root=project, split_id="discovery", samples=(sample,),
        instruction_text=text, split_role="discovery", registered_population_bound=True,
    )
    message = phase_program_system_text(adapter, sample)
    assert text in message and "Legal task ontology." in message
    assert "Respond with ONLY a JSON" not in message
