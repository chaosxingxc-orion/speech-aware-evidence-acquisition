"""Synthetic construction through real custody, finalization and release.

Only model transport and the environment gate are test doubles. No live model,
annotation corpus, credential, queue or official task scorer is contacted.
"""
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.base import RunResult
from speech_aware_evidence_acquisition.core.bundle import build_manifest, finalize_bundle, verify_bundle, BundleError
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.core.split_receipt import VerifiedSplit
from speech_aware_evidence_acquisition.data.splits import prefixed
from speech_aware_evidence_acquisition.rails import build_payload_binding
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_construction import materialize_slot_construction, verify_released_slot_construction
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import prepare_semantic_knowledge_store
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import SLOT_CONTRACT_BUILD_POLICY_ID
from test_flight_runtime import _make_repo, _git
from test_rails_frozen_core_client import _World, _client, _plan, _CapturingTransport, _speech_feature_world, _speech_feature_messages
from test_semantic_knowledge_edits import rows, contract, proposal
from test_semantic_knowledge_preparation import _write, _roster
from test_system_text_construction import INSTRUCTION
from test_bundle import _HUMAN_LEDGER_CELLS


def _pin(path, root):
    return {"relpath": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _sealed_generation(tmp_path):
    world = _World(tmp_path / "client")
    feature_root, packet, packets = _speech_feature_world(world, tmp_path / "client")
    sample = replace(world.samples[0], sample_id="slurp:train:new")
    world.samples = [sample]
    world.run_dir = world.data_root / "runs" / "synthetic-construction"
    roster = _roster((sample.sample_id,), roster_id="synthetic-construction")
    run_id = "SAEA-TEST-SYSTEM-TEXT-CONSTRUCTION"
    repo = _make_repo(tmp_path, run_id, arm="speech-feature-query", policy="phase-direct-only-v1",
        carrier_lock_key="slurp", baseline_extra={"scorers": [], "result_kind": "artifact",
        "artifact_result": {"schema": "saea-artifact-result-binding-v1", "role": "training-feedback-proposal",
            "construction_roster": {"repo_relpath": "construction.json", "sha256": "0" * 64}}})
    roster_pin = _write(repo / "construction.json", roster)
    baseline_path = repo / "configs/baseline/b.json"
    baseline = json.loads(baseline_path.read_text())
    baseline["artifact_result"]["construction_roster"]["sha256"] = roster_pin["sha256"]
    _write(baseline_path, baseline)
    _git(repo, "add", "construction.json", "configs/baseline/b.json")
    _git(repo, "commit", "-qm", "Freeze synthetic construction source")
    composed = compose(repo, model="m", dataset="d", baseline="b", experiment="e")
    plan = _plan(run_id=run_id, carrier_lock_key="slurp", split_identity_hash=roster["split_identity_hash"],
        protocol_hash=protocol_hash(composed.config_hash, "speech-feature-query", roster["split_identity_hash"]))
    binding = build_payload_binding(carrier_lock_key="slurp", samples=world.samples,
        data_root=world.data_root, carrier_root=world.carrier_root)
    transport = _CapturingTransport(responder=lambda _: json.dumps(proposal(rows())))
    client, _, _ = _client(world, tmp_path, plan=plan, binding=binding, transport=transport,
        arm="speech-feature-query", speech_feature_root=feature_root,
        speech_packet_bindings={sample.sample_id: packets["s1"]})
    response = client.complete(_speech_feature_messages(packet), speech_feature_sample_id=sample.sample_id,
        key_representation_id="key-fixture", matcher_policy_id="matcher-fixture", agent_state=(),
        agent_contact_id="direct", contact_instruction=INSTRUCTION)
    close = client.close()
    timing, = close["timings"]
    output = {"request_id": timing["request_id"], "sample_id": sample.sample_id,
        "carrier_lock_key": "slurp", "arm": "speech-feature-query", "text": response, "admitted": True,
        **{k: timing[k] for k in ("request_sha256", "response_sha256", "response_text_sha256")},
        "result_kind": "artifact", "artifact_role": "training-feedback-proposal"}
    outputs = world.run_dir / (run_id + ".outputs.jsonl")
    outputs.write_text(json.dumps(output) + "\n")
    result = RunResult(run_id=run_id, arm=close["arm"], outputs_path=outputs,
        trace_manifest_hash=close["trace_manifest_hash"], cost=close["cost"])
    split = VerifiedSplit(name="synthetic-construction", carrier_lock_key="slurp", split_role="discovery",
        ids=(sample.sample_id,), prefixed_ids=tuple(prefixed("slurp", [sample.sample_id])),
        identity_hash=roster["split_identity_hash"])
    manifest = build_manifest(repo_root=repo, data_root=world.data_root, composed=composed, plan=plan,
        verified_split=split, session_receipt_path=None, run_dir=world.run_dir, status="COMPLETED", result=result)
    kwargs = dict(base_rows=rows(), contract=contract(rows()), generation_pin=_pin(manifest, world.data_root),
        instruction=INSTRUCTION, data_root=world.data_root)
    # A COMPLETED generation flag cannot substitute for real finalization.
    assert verify_bundle(manifest).attempt_state == "OPENED"
    with pytest.raises(PolicyError, match="finalized"):
        materialize_slot_construction(**kwargs)
    cells = {**_HUMAN_LEDGER_CELLS, "speech task/carrier": "slurp discovery"}
    finalized = finalize_bundle(manifest, {}, world.data_root, repo_root=repo, ledger_cells=cells)
    assert finalized.attempt_state == "FINALIZED" and finalized.scores_path is None
    verified = verify_bundle(manifest)
    assert verified.attempt_state == "FINALIZED" and verified.manifest["scores"] is None
    assert verified.manifest["cost"]["calls_used"] == len(transport.calls) == 1
    return repo, world.data_root, manifest, kwargs, cells


def _release(repo, data, kwargs):
    materialized = materialize_slot_construction(**kwargs)
    support = _roster(tuple(materialized["rows"][0]["source_support"]["source_sample_ids"]), roster_id="support")
    support_pin = _write(repo / "support.json", support)
    forbidden = _write(repo / "forbidden.json", _roster(("slurp:train:held",), roster_id="held", roster_role="evaluation"))
    authored = _write(data / "authored.json", {"schema": "saea-authored-semantic-knowledge-source-v1",
        "builder_policy_id": SLOT_CONTRACT_BUILD_POLICY_ID,
        "source_split_identity_hash": support["split_identity_hash"], "rows": materialized["rows"]})
    registration = {"schema": "saea-authored-semantic-knowledge-preparation-v1",
        "registration_id": "SYNTHETIC-TEXT-CONSTRUCTION-V1", "carrier_lock_key": "slurp",
        "source_partition_role": "train", "source_split_identity_hash": support["split_identity_hash"],
        "builder_policy_id": SLOT_CONTRACT_BUILD_POLICY_ID, "store_id": "slot-contracts", "store_role": "slot-contracts",
        "authored_source": authored, "construction_scope": support_pin, "permitted_roster": support_pin,
        "forbidden_rosters": [forbidden], "output_namespace": "knowledge/semantic/synthetic-slot-contracts-v1"}
    registration_pin = _write(repo / "registration.json", registration)
    prepared = prepare_semantic_knowledge_store(repo / "registration.json", repo_root=repo, data_root=data)
    link = {"schema": "saea-system-text-construction-link-v1", "instruction_sha256": content_hash(INSTRUCTION),
        "knowledge": {k: prepared["completion"][k] for k in ("snapshot", "release")},
        "base_rows": _write(data / "base.json", kwargs["base_rows"]),
        "edit_contract": _write(data / "contract.json", kwargs["contract"]), "generation": kwargs["generation_pin"],
        "registration": registration_pin, "completion": prepared["completion_pin"]}
    assert verify_released_slot_construction(link, instruction=INSTRUCTION, data_root=data, repo_root=repo) == materialized
    return materialized, link


def test_real_artifact_finalization_to_semantic_release(tmp_path):
    repo, data, manifest, kwargs, _ = _sealed_generation(tmp_path)
    before = manifest.read_bytes()
    result, link = _release(repo, data, kwargs)
    assert result["rows"][0]["extraction_cues"] == proposal(rows())["edits"][0]["replacement"]
    assert result["optimizer_construction_sample_ids"] == ["slurp:train:new", "slurp:train:tie"]
    assert manifest.read_bytes() == before
    from speech_aware_evidence_acquisition.rails.knowledge_stores import load_knowledge_store_binding
    binding = load_knowledge_store_binding({"knowledge_stores": {"slot-contracts": {
        "store_role": "slot-contracts", **link["knowledge"]}}}, data_root=data)
    assert {sid for value in binding.snapshot_for("slot-contracts").values for sid in value.source_sample_ids} == {
        "slurp:train:base", "slurp:train:new", "slurp:train:tie"}


def test_real_finalized_artifact_refuses_replay(tmp_path):
    repo, data, manifest, _, cells = _sealed_generation(tmp_path)
    with pytest.raises(BundleError, match="FINALIZED"):
        finalize_bundle(manifest, {}, data, repo_root=repo, ledger_cells=cells)


@pytest.mark.parametrize("artifact", ["outputs", "raw_trace", "trace_manifest"])
def test_real_construction_join_rejects_changed_sealed_artifact(tmp_path, artifact):
    _, _, manifest, kwargs, _ = _sealed_generation(tmp_path)
    path = Path(json.loads(manifest.read_text())[artifact]["path"])
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(BundleError, match="hash|SHA|sha256"):
        materialize_slot_construction(**kwargs)


def _compiler_seed(repo, data):
    """Use the production module graph with synthetic fixed-store pins."""
    import shutil
    from test_system_text_policy import ROOT, BASE, seed_document
    from test_knowledge_stores import _store_snapshot
    from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (
        LOCK_BASELINE_FRAGMENT, LOCK_V2_0_REVIEWER_TEMPLATE, LOCK_V2_1_REVIEWER_TEMPLATE,
    )
    from speech_aware_evidence_acquisition.rails.system_text_policy import SystemTextPolicyBundle
    baseline = json.loads((ROOT / BASE).read_text())
    lock = json.loads((ROOT / "configs/baseline" / (LOCK_BASELINE_FRAGMENT + ".json")).read_text())
    fixed_ids = []
    for store_id in ("intent-boundaries", "train-exemplars"):
        sid = "slurp:train:fixed-" + store_id
        fixed_ids.append(sid)
        source = _store_snapshot(store_id)
        snapshot = replace(source, source_sample_ids=(sid,),
            facets=tuple(replace(f, source_sample_ids=(sid,)) for f in source.facets),
            values=tuple(replace(v, source_sample_ids=(sid,)) for v in source.values)).validate()
        prefix = "knowledge/" + store_id + "/"
        _write(data / (prefix + "snapshot.json"), snapshot.frozen_json(), root=data)
        source_pin = _write(data / (prefix + "source.json"), {"sample_ids": [sid]}, root=data)
        release_pin = _write(data / (prefix + "release.json"), {
            "schema": "saea-knowledge-store-release-v1", "store_id": store_id, "store_role": store_id,
            "snapshot_sha256": snapshot.content_hash(), "source_split_identity_hash": snapshot.source_split_identity_hash,
            "builder_policy_id": snapshot.builder_policy_id, "source": source_pin}, root=data)
        pins = {"snapshot": {"relpath": prefix + "snapshot.json", "sha256": snapshot.content_hash()}, "release": release_pin}
        baseline["knowledge_stores"][store_id].update(pins)
        lock["knowledge_stores"][store_id].update(pins)
        if store_id == "train-exemplars":
            for component in baseline["native_episode"]["consumption_module"]["components"]:
                if component["component_id"] == "construction-store-binding":
                    component["params"].update(pins)
    _write(repo / "configs/baseline" / (LOCK_BASELINE_FRAGMENT + ".json"), lock)
    for relpath, _ in (LOCK_V2_0_REVIEWER_TEMPLATE, LOCK_V2_1_REVIEWER_TEMPLATE):
        dest = repo / "configs" / relpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "configs" / relpath, dest)
    for component in baseline["native_episode"]["consumption_module"]["components"]:
        if "record" in component:
            record = repo / component["record"]
            record.parent.mkdir(parents=True, exist_ok=True)
            record.write_text("Synthetic module-compilation fixture; no scientific result or runtime admission.\n")
    doc = seed_document()
    doc["seed_config_sha256"] = content_hash(baseline)
    doc["cumulative_sources"] = [{"kind": "knowledge", "sha256": "a" * 64,
        "sample_ids": fixed_ids + ["slurp:train:base"]}]
    return baseline, SystemTextPolicyBundle.from_json(doc)


def test_finalized_construction_compiles_joint_policy_with_cumulative_sources(tmp_path):
    from speech_aware_evidence_acquisition.rails.system_text_policy import (
        TextPolicyUpdateProposal, apply_text_proposal, compile_system_text_policy, assert_roster_disjoint,
    )
    from speech_aware_evidence_acquisition.rails.consumption_module import verify_declared_module
    from speech_aware_evidence_acquisition.rails.knowledge_stores import load_knowledge_store_binding
    repo, data, manifest, kwargs, _ = _sealed_generation(tmp_path)
    result, link = _release(repo, data, kwargs)
    link_pin = _write(data / "construction-link.json", link)
    baseline, parent = _compiler_seed(repo, data)
    proposal_doc = {"schema": "saea-text-policy-update-proposal-v1", "branch": "L", "round": 2, "slot": 1,
        "parent_ids": [parent.bundle_id], "changes": {
            "construction_instruction": INSTRUCTION, "slot_value_edits": result["generated_proposal"],
            "role_text": {"solver": "Use source-supported slot boundaries and preserve uncertainty."}},
        "rationale": "Test the complete generated-knowledge and role-text join.", "hypotheses": [], "evidence": []}
    proposal_object = TextPolicyUpdateProposal.from_json(proposal_doc)
    sources = [{"kind": "construction", "sha256": link_pin["sha256"],
        "sample_ids": result["optimizer_construction_sample_ids"]}]
    child = apply_text_proposal(proposal_object, parents=[parent], added_sources=sources,
        knowledge=link["knowledge"], construction_receipt=link_pin)
    before = {p: p.read_bytes() for p in manifest.parent.iterdir() if p.is_file()}
    compiled = compile_system_text_policy(baseline, child, repo_root=repo, output_root=tmp_path / "candidate", data_root=data)
    verify_declared_module(compiled["native_episode"]["consumption_module"], compiled, repo_root=repo)
    loaded = load_knowledge_store_binding(compiled, data_root=data)
    assert loaded.snapshot_for("slot-contracts").values[0].source_sample_ids == ("slurp:train:base", "slurp:train:new", "slurp:train:tie")
    assert compiled["policy"] == baseline["policy"] and compiled["scorers"] == baseline["scorers"]
    assert compiled["phase_tools"]["planner"]["max_calls_per_sample"] == 1
    assert compiled["native_episode"]["max_revisions"] == 1
    for role, text in child.as_json()["role_text"].items():
        assert (tmp_path / "candidate/configs" / compiled["phase_material"][role]["instruction_template"]).read_text() == text
    assert compile_system_text_policy(baseline, child, repo_root=repo, output_root=tmp_path / "off", enabled=False) == baseline
    assert not (tmp_path / "off").exists()
    assert_roster_disjoint(child.as_json()["cumulative_sources"], ["slurp:train:held"])
    with pytest.raises(PolicyError, match="overlap"):
        assert_roster_disjoint(child.as_json()["cumulative_sources"], ["slurp:train:tie:another-recording"])
    assert all(p.read_bytes() == original for p, original in before.items())
    # Omitting feedback with no selected edit still fails before publishing text.
    incomplete = [{**sources[0], "sample_ids": ["slurp:train:new"]}]
    bad = apply_text_proposal(proposal_object, parents=[parent], added_sources=incomplete,
        knowledge=link["knowledge"], construction_receipt=link_pin)
    with pytest.raises(PolicyError, match="ancestry"):
        compile_system_text_policy(baseline, bad, repo_root=repo, output_root=tmp_path / "rejected", data_root=data)
    assert not (tmp_path / "rejected").exists()
