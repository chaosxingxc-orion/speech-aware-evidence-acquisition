"""Source-bound candidate recovery through complete native role trajectories."""

import copy
import hashlib
import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.rails.controllers import seal_phase_response_state
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    build_knowledge_store_supply, load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
    AuthoredSemanticKnowledgeSpec, build_intent_boundary_snapshot,
)
from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import (
    BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
)
from test_candidate_semantic_supply import _config, _context, _store, _write
from test_knowledge_stores_e3b_candidate_and_phase_supply_router import _plain_phase_supply_store
from test_semantic_knowledge_build import _intent
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401


def _program(max_contacts=8):
    from test_native_episode_runner import _program as native_program
    program = native_program(max_contacts=max_contacts)
    return replace(program, phases=tuple(
        replace(phase, knowledge="supplied") if phase.name == "solver" else phase
        for phase in program.phases
    )).validate()


def _document(root, mode="append-selected-exemplars"):
    document, legal = _config(root)
    slot = document["knowledge_stores"]["slot-contracts"]
    spec = slot["candidate_supply"].pop("solve")
    spec.update(
        candidate_state_phase="perception", compact_source_phase="perception",
        projection_policy=BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
        exemplar_candidate_proposal={
            "mode": mode, "exemplar_store_id": "train-exemplars",
            "intent_store_id": "intent-boundaries", "max_candidates": 4,
            "max_added_slot_values": 2,
        },
    )
    slot["candidate_supply"]["solver"] = spec
    sid, store, snapshot = _plain_phase_supply_store(
        root, phase="solver", store_id="train-exemplars", k=2,
        facets=(("one", (1.0, 0.0)), ("two", (0.7, 0.7))),
    )
    snapshot = replace(snapshot, values=tuple(
        replace(value, task_target="gamma") for value in snapshot.values
    )).validate()
    snap_path = root / store["snapshot"]["relpath"]
    snap_path.write_text(json.dumps(snapshot.frozen_json()))
    store["snapshot"]["sha256"] = snapshot.content_hash()
    release_path = root / store["release"]["relpath"]
    release = json.loads(release_path.read_text())
    release["snapshot_sha256"] = snapshot.content_hash()
    store["release"]["sha256"] = _write(release_path, release)
    document["knowledge_stores"][sid] = store
    rows = tuple(_intent(intent_id=intent) for intent in legal)
    intents = build_intent_boundary_snapshot(
        AuthoredSemanticKnowledgeSpec(
            carrier_lock_key="slurp", source_split_identity_hash="a"*64,
            permitted_source_sample_ids=("train-1",),
        ), rows=rows,
    )
    document["knowledge_stores"]["intent-boundaries"] = _store(
        root, "intent-boundaries", "intent-boundaries", intents, {
            "schema": "saea-authored-semantic-knowledge-source-v1",
            "builder_policy_id": intents.builder_policy_id,
            "source_split_identity_hash": "a"*64, "rows": rows,
        },
    )
    return document, legal


def _router(root, mode="append-selected-exemplars"):
    document, legal = _document(root, mode)
    binding = load_knowledge_store_binding(document, data_root=root)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=root, legal_candidate_ids=legal,
    )
    return binding, router


def _raw():
    return json.dumps({"candidates": [
        {"intent_id": label, "distinction": "A speech cue",
         "evidence_refs": [], "unresolved_fields": []}
        for label in ("alpha", "beta", "alpha")
    ]})


def _staged(binding):
    artifact = seal_phase_response_state(
        phase_name="perception", sample_id="s1", state_content=_raw(),
        raw_response_text=_raw(), source_query_state_sha256="b"*64,
        producer_policy_id=_program().program_id,
    )
    context = _context(binding, artifact)
    artifact = replace(artifact, source_query_state_sha256=context.query_state.content_hash())
    return replace(context, agent_states=(artifact,))


@pytest.mark.parametrize("mode,expected", [
    ("original-only", ("alpha", "beta")),
    ("append-selected-exemplars", ("alpha", "beta", "gamma")),
])
def test_router_binds_actual_selection_and_preserves_proposal_through_revision(tmp_path, mode, expected):
    binding, router = _router(tmp_path, mode)
    staged = _staged(binding)
    raw = staged.agent_states[0]
    supply = router.automatic_for_phase("solver", staged)
    values = supply.fusion_decision.selected_value_ids
    assert values[:2] == ("train-exemplars::v-one", "train-exemplars::v-two")
    assert "slot-contracts::slot-contract:alpha_one" in values
    assert "slot-contracts::slot-contract:beta_one" in values
    assert ("slot-contracts::slot-contract:gamma_one" in values) == (mode != "original-only")
    for label in expected:
        assert "intent-boundaries::intent-boundary:" + label in values
    visible = replace(staged, query_state=replace(
        staged.query_state, retrieved_value_ids=values, agent_state_ids=(raw.state_id,),
    ).validate())
    proposal = router.candidate_proposal_for_context(visible)
    assert proposal.candidate_ids == expected
    assert proposal.original_state_sha256 == raw.content_hash()
    before = proposal.content_hash()
    router.automatic_for_phase("solver", visible)
    assert router.candidate_proposal_for_context(visible).content_hash() == before
    assert staged.agent_states[0].content == _raw()
    with pytest.raises(Exception, match="visible"):
        router.candidate_proposal_for_context(replace(
            visible, query_state=replace(visible.query_state, retrieved_value_ids=()),
        ))
    audits = router.receipt["candidate_proposals"]
    assert len(audits) == 1
    assert next(iter(audits.values()))["proposal_sha256"] == before


@pytest.mark.parametrize("change", [
    {"mode": "unknown"}, {"max_candidates": True}, {"max_added_slot_values": 0},
    {"exemplar_store_id": "missing"}, {"intent_store_id": "slot-contracts"},
])
def test_invalid_proposal_configuration_refuses_before_dispatch(tmp_path, change):
    document, legal = _document(tmp_path)
    document["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solver"][
        "exemplar_candidate_proposal"
    ].update(change)
    with pytest.raises(Exception):
        binding = load_knowledge_store_binding(document, data_root=tmp_path)
        build_knowledge_store_supply(
            binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal,
        )


@pytest.mark.usefixtures("_spawn_live_matching_process")
@pytest.mark.parametrize("mode", ["original-only", "append-selected-exemplars"])
def test_all_downstream_roles_consume_one_source_bound_proposal_and_keep_raw_perception(tmp_path, monkeypatch, mode):
    import test_native_episode_runner as episode
    binding, router = _router(tmp_path / "stores", mode)
    monkeypatch.setattr(episode, "_knowledge_snapshot", lambda: binding.composite_snapshot)
    monkeypatch.setattr(episode, "_program", lambda **kwargs: _test_program(**kwargs))
    original_run = episode.run_speech_native_agent_loop
    captured = []
    harness = episode._ActualEpisodeHarness(
        tmp_path / "runtime", sample_count=1, max_revisions=1, max_contacts=8,
        planner_actions=("REVISE", "ACCEPT"),
    )
    original_output = harness._output
    harness._output = lambda key: _raw() if key[1] == "perception" else original_output(key)
    gate = harness.request_gate

    def request_gate(request):
        captured.append(request.as_payload())
        return gate(request)

    harness.request_gate = request_gate

    def run(**kwargs):
        native = kwargs["native_episode_binding"]
        kwargs["native_episode_binding"] = replace(
            native, supply_for_phase=router.automatic_for_phase,
            candidate_proposal_for_context=router.candidate_proposal_for_context,
        )
        return original_run(**kwargs)

    monkeypatch.setattr(episode, "run_speech_native_agent_loop", run)
    try:
        summary = harness.run()
    finally:
        closed = harness.close()
    assert closed["request_count"] == 7
    assert summary.results[0].final_response_text == "solver-answer:s1:visit:2"
    assert not any(part["evidence_id"].startswith("candidate-proposal:")
                   for part in captured[0]["supplied_evidence"])
    proposal_texts = []
    for request in captured[1:]:
        blocks = [part for part in request["supplied_evidence"]
                  if part["evidence_id"].startswith("candidate-proposal:")]
        assert len(blocks) == 1
        proposal_texts.append(blocks[0]["content"])
        assert ("gamma" in blocks[0]["content"]) == (mode != "original-only")
        assert any(part["evidence_id"] == "slot-contracts::slot-contract:gamma_one"
                   for part in request["supplied_evidence"]) == (mode != "original-only")
        assert any(part["evidence_id"] == "intent-boundaries::intent-boundary:gamma"
                   for part in request["supplied_evidence"]) == (mode != "original-only")
    assert len(set(proposal_texts)) == 1
    result = summary.results[0]
    receipt = result.native_episode_receipt["candidate_proposal"]
    assert len(receipt["contacts"]) == 6
    assert {row["role_kind"] for row in receipt["contacts"]} == {"solver", "reviewer", "planner"}
    assert all(row["request_sha256"] for row in receipt["contacts"])
    records = {record_id: payload for _channel, record_id, payload in harness.trace.records}
    original_states = [state for payload in records.values()
                       for state in payload.get("org_agent_states", ())
                       if state["state_kind"] == "phase:perception"]
    assert len(original_states) == 1 and original_states[0]["content"] == _raw()
    from speech_aware_evidence_acquisition.rails.slurp_candidate_proposal import (
        validate_candidate_proposal_consumption,
    )
    validate_candidate_proposal_consumption(
        result.native_episode_receipt, sample_id="s1", trace_records=records,
    )
    from speech_aware_evidence_acquisition.core.bundle.outputs import _verify_outputs_trace_binding
    from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
        validate_native_episode_delivery_receipt,
    )
    delivery = validate_native_episode_delivery_receipt(result.native_episode_receipt)
    final = delivery.final_contact
    row = {
        "sample_id": "s1", "text": result.final_response_text,
        "response_text_sha256": hashlib.sha256(result.final_response_text.encode()).hexdigest(),
        "request_id": final["request_id"], "request_sha256": final["request_sha256"],
        "response_sha256": final["response_sha256"],
        "native_episode_receipt": result.native_episode_receipt,
    }
    _verify_outputs_trace_binding((row,), records)
    projected = _export_candidate_result(harness, result, row, records)
    assert projected["candidate_proposal"]["receipt"] == receipt
    assert projected["candidate_proposal"]["claim_scope"] == "verified-supply-not-semantic-use"
    assert len(projected["candidate_proposal"]["receipt"]["contacts"]) == 6
    missing = copy.deepcopy(row)
    del missing["native_episode_receipt"]["candidate_proposal"]
    with pytest.raises(ValueError, match="differs"):
        _export_candidate_result(harness, result, missing, records)
    mutations = []
    changed = copy.deepcopy(result.native_episode_receipt)
    changed["candidate_proposal"]["contacts"].pop()
    mutations.append((changed, records))
    changed = copy.deepcopy(result.native_episode_receipt)
    changed["candidate_proposal"]["contacts"][0]["request_sha256"] = "f"*64
    mutations.append((changed, records))
    changed = copy.deepcopy(result.native_episode_receipt)
    digest = next(iter(changed["candidate_proposal"]["proposals"]))
    changed["candidate_proposal"]["proposals"][digest]["candidate_ids"] = ["delta"]
    mutations.append((changed, records))
    changed_records = copy.deepcopy(records)
    request_id = receipt["contacts"][0]["request_id"]
    request_record = changed_records[request_id + "/request"]
    request_record["payload"]["supplied_evidence"] = [
        block for block in request_record["payload"]["supplied_evidence"]
        if not block["evidence_id"].startswith("candidate-proposal:")
    ]
    mutations.append((result.native_episode_receipt, changed_records))
    for episode_receipt, raw_records in mutations:
        with pytest.raises(ValueError):
            validate_candidate_proposal_consumption(
                episode_receipt, sample_id="s1", trace_records=raw_records,
            )


# Preserve the original fixture callable before monkeypatching its module.
from test_native_episode_runner import _program as _base_program

def _test_program(**kwargs):
    program = _base_program(**kwargs)
    return replace(program, phases=tuple(
        replace(phase, knowledge="supplied") if phase.name == "solver" else phase
        for phase in program.phases
    )).validate()


@pytest.mark.usefixtures("_spawn_live_matching_process")
@pytest.mark.parametrize("phase,contacts", [
    ("perception", 1), ("solver", 2), ("reviewer", 3), ("planner", 4),
])
def test_finite_completion_retains_candidate_custody_and_whole_row(tmp_path, monkeypatch, phase, contacts):
    import test_native_episode_runner as episode
    from test_native_finite_outcome_integration import _canonical_runtime
    from speech_aware_evidence_acquisition.core.bundle.outputs import _verify_outputs_trace_binding

    binding, router = _router(tmp_path / "stores")
    monkeypatch.setattr(episode, "_knowledge_snapshot", lambda: binding.composite_snapshot)
    monkeypatch.setattr(episode, "_program", lambda **kwargs: _test_program(**kwargs))
    original_run, original_wire = episode.run_speech_native_agent_loop, episode._wire_response
    harness = episode._ActualEpisodeHarness(
        tmp_path / "runtime", sample_count=1, max_revisions=0, max_contacts=5,
        planner_actions=("ACCEPT",),
    )
    harness.config = replace(harness.config, finite_completion_policy="deliver-latest-or-abstain")
    original_output = harness._output
    harness._output = lambda key: _raw() if key[1] == "perception" else original_output(key)

    def wire(text):
        output = json.loads(original_wire(text))
        target = (
            text == _raw() if phase == "perception" else
            text == "ACCEPT" if phase == "planner" else text.startswith(phase + "-")
        )
        if target:
            output["choices"][0]["finish_reason"] = "length"
        return json.dumps(output, separators=(",", ":")).encode()

    monkeypatch.setattr(episode, "_wire_response", wire)

    def run(**kwargs):
        kwargs["native_episode_binding"] = replace(
            kwargs["native_episode_binding"], supply_for_phase=router.automatic_for_phase,
            candidate_proposal_for_context=router.candidate_proposal_for_context,
        )
        return original_run(**kwargs)

    monkeypatch.setattr(episode, "run_speech_native_agent_loop", run)
    try:
        summary = harness.run()
        runtime = _canonical_runtime(harness, summary)
        runtime._composed.values["knowledge_stores"] = {
            "slot-contracts": {"candidate_supply": {"solver": {
                "exemplar_candidate_proposal": {"mode": "append-selected-exemplars"},
            }}},
        }
        output = runtime._canonical_output_rows(harness.client)
    finally:
        closed = harness.close()
    assert closed["request_count"] == contacts
    assert len(summary.results) == len(output) == 1
    receipt = summary.results[0].native_episode_receipt
    assert receipt["terminal_disposition"]["finish_reason"] == "length"
    assert len(receipt["candidate_proposal"]["contacts"]) == contacts - 1
    records = {rid: payload for _, rid, payload in harness.trace.records}
    _verify_outputs_trace_binding(tuple(output), records)
    exported = _export_candidate_result(harness, summary.results[0], output[0], records)
    block = exported["candidate_proposal"]["receipt"]
    assert len(block["contacts"]) == contacts - 1
    assert len(block["proposals"]) == (0 if phase == "perception" else 1)
    assert exported["delivery"]["kind"] == ("abstention" if phase in {"perception", "solver"} else "finite")


def test_preparation_envelope_includes_added_cards_and_proposal_without_capacity_claim(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    from speech_aware_evidence_acquisition.rails import native_episode_config

    document, legal = _document(tmp_path)
    binding = load_knowledge_store_binding(document, data_root=tmp_path)
    monkeypatch.setattr(native_episode_config, "load_native_episode_config",
                        lambda *_args: SimpleNamespace(max_candidate_refreshes=0))
    inventory = SimpleNamespace(candidate_ids=legal)
    inventory.validate = lambda: inventory
    runtime = SimpleNamespace(
        _composed=SimpleNamespace(values=document), _knowledge_store_binding=binding,
        _load_knowledge_snapshot=lambda: binding.composite_snapshot,
        _adapter=SimpleNamespace(candidate_inventory=lambda: inventory),
    )
    envelope = FlightRuntime._phase_supply_prompt_bound(runtime, _test_program(max_contacts=8))
    for role in ("solver", "reviewer", "planner"):
        texts = [text for text, _kind in envelope[role]]
        assert sum("[evidence slot-contracts::" in text for text in texts) == 5
        assert sum("[evidence intent-boundaries::" in text for text in texts) == 4
        assert any("Additional exemplar-supported" in text for text in texts)


def _export_candidate_result(harness, result, output, records):
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.analysis.native_episode_source import VerifiedNativeEpisodeSource
    from speech_aware_evidence_acquisition.analysis.system_trajectory import export_system_trajectories
    source = VerifiedNativeEpisodeSource(
        bundle=SimpleNamespace(trace_records=records, manifest={"outputs": {"sha256": "a"*64}}),
        composed=SimpleNamespace(config_hash="c"*64, values={"policy": harness.program.program_id}),
        plan=harness.plan, sample_ids=("s1",),
        phase_results={"s1": result.as_json()}, output_rows={"s1": output},
        phase_artifact_sha256="b"*64, diagnostics={},
    )
    row = export_system_trajectories(source)["trajectories"][0]
    from speech_aware_evidence_acquisition.analysis.system_semantic_trajectory import (
        materialize_semantic_trajectories, tfgrpo_summary_fields,
    )
    materialized = materialize_semantic_trajectories(source, round_id="synthetic-round")["episodes"][0]
    fields = tfgrpo_summary_fields(materialized)
    visible = json.loads(json.loads(fields["trajectories"])[0]["trajectory"])
    assert visible["trajectory"]["candidate_proposal"] == row["candidate_proposal"]
    assert len(visible["contacts"]) == sum(len(v["contacts"]) for v in row["role_visits"])
    assert visible["delivered_text"] == output["text"]
    return row


@pytest.mark.usefixtures("_spawn_live_matching_process")
@pytest.mark.parametrize("mode", ["original-only", "append-selected-exemplars"])
@pytest.mark.parametrize("labels", [
    ("gamma", "gamma", "gamma"),
    ("alpha", "gamma", "alpha"),
    ("alpha", "beta", "gamma"),
    ("gamma",),
])
def test_seal_keeps_raw_position_bound_when_authority_labels_collapse(
    tmp_path, monkeypatch, mode, labels,
):
    import test_native_episode_runner as episode
    from test_native_finite_outcome_integration import _canonical_runtime
    from speech_aware_evidence_acquisition.core.bundle.outputs import _verify_outputs_trace_binding

    binding, router = _router(tmp_path / "stores", mode)
    monkeypatch.setattr(episode, "_knowledge_snapshot", lambda: binding.composite_snapshot)
    monkeypatch.setattr(episode, "_program", lambda **kwargs: _test_program(**kwargs))
    original_run = episode.run_speech_native_agent_loop
    harness = episode._ActualEpisodeHarness(
        tmp_path / "runtime", sample_count=1, max_revisions=0, max_contacts=5,
        planner_actions=("ACCEPT",),
    )
    raw = json.dumps({"candidates": [
        {"intent_id": label, "distinction": "A speech cue",
         "evidence_refs": [], "unresolved_fields": []}
        for label in labels
    ]})
    original_output = harness._output
    harness._output = lambda key: raw if key[1] == "perception" else original_output(key)

    def run(**kwargs):
        kwargs["native_episode_binding"] = replace(
            kwargs["native_episode_binding"], supply_for_phase=router.automatic_for_phase,
            candidate_proposal_for_context=router.candidate_proposal_for_context,
        )
        return original_run(**kwargs)

    monkeypatch.setattr(episode, "run_speech_native_agent_loop", run)
    try:
        summary = harness.run()
        runtime = _canonical_runtime(harness, summary)
        runtime._composed.values["knowledge_stores"] = {
            "slot-contracts": {"candidate_supply": {"solver": {
                "exemplar_candidate_proposal": {"mode": mode},
            }}},
        }
        outputs = runtime._canonical_output_rows(harness.client)
    finally:
        closed = harness.close()
    assert closed["request_count"] == 4
    records = {rid: payload for _, rid, payload in harness.trace.records}
    _verify_outputs_trace_binding(tuple(outputs), records)
    proposal = next(iter(summary.results[0].native_episode_receipt["candidate_proposal"]["proposals"].values()))
    assert proposal["original_candidate_ids"] == list(dict.fromkeys(labels))
    raw_states = [
        state["content"] for payload in records.values()
        for state in payload.get("org_agent_states", ())
        if state["state_kind"] == "phase:perception"
    ]
    assert raw_states == [raw]
