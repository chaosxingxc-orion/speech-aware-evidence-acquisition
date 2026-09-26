# ruff: noqa: F811
"""Registered complete actor rounds and disjoint cumulative memory construction."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_system_summary_preparation import summary_world, pin  # noqa: F401
from test_system_comparison_preparation import comparison_world  # noqa: F401
from test_system_group_update import update_world, prepared, load  # noqa: F401
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401

from speech_aware_evidence_acquisition.analysis import system_update_round as verification
from speech_aware_evidence_acquisition.rails import system_group_update_context as module
from speech_aware_evidence_acquisition.rails.experience_consolidation import initialize_candidate_snapshot
from speech_aware_evidence_acquisition.core.preparation import prepare_artifact
from speech_aware_evidence_acquisition.rails.prepared_feedback import PreparedFeedbackError


@pytest.fixture
def round_world(update_world, comparison_world):  # noqa: F811
    w = update_world
    actors = list(comparison_world["actors"].values())
    policy = {"schema": "saea-system-update-round-policy-v1", "round_id": "round-1",
              "base_memory_snapshot_sha256": None, "actors": [
                  {"label": member["label"], "run_id": actor.plan.run_id,
                   "attempt_id": actor.plan.attempt_id, "config_hash": actor.composed.config_hash,
                   "study_commit": actor.bundle.manifest["study_commit"], "protocol_hash": actor.plan.protocol_hash}
                  for member, actor in zip(comparison_world["binding"]["members"], actors)]}
    binding = dict(w["binding"], schema=module.ROUND_SOURCE_SCHEMA,
                   cumulative_construction_roster=w["binding"]["source_construction_roster"],
                   round_policy=pin(w["data"], "round-policy.json", policy))
    return {**w, "actors": actors, "policy": policy, "binding": binding,
            "source_pin": pin(w["data"], "round-source.json", binding)}


def refresh(w):
    w["binding"]["round_policy"] = pin(w["data"], "round-policy.json", w["policy"])
    w["source_pin"] = pin(w["data"], "round-source.json", w["binding"])


def document(w):
    return module.build_system_group_update_contexts(w["source_pin"], data_root=w["data"])


def test_initial_round_binds_registered_complete_actors_without_changing_model_context(round_world):
    w = round_world
    doc = document(w)
    assert doc["round_policy_receipt"]["base_snapshot_sha256"] is None
    assert [r["run_id"] for r in doc["round_policy_receipt"]["actors"]] == ["actor-0", "actor-1"]
    assert "round_policy_receipt" not in doc["contexts"][0]["model_context"]
    spec, _ = prepared(w)
    states, receipt = load(w, spec)
    assert len(states) == 1 and receipt["base_snapshot_sha256"] == doc["base_snapshot"]["content_sha256"]


@pytest.mark.parametrize("mutation", ["config", "protocol", "commit", "actor-count", "round", "base", "unexpected-memory", "other-memory"])
def test_round_policy_mismatch_refuses_before_update_contact(round_world, mutation):
    w = round_world
    if mutation in {"config", "protocol", "commit"}:
        field = {"config": "config_hash", "protocol": "protocol_hash", "commit": "study_commit"}[mutation]
        w["policy"]["actors"][0][field] = "f"*(40 if mutation == "commit" else 64)
    elif mutation == "actor-count":
        w["policy"]["actors"].pop()
    elif mutation == "round":
        w["policy"]["round_id"] = "foreign-round"
    elif mutation == "base":
        w["policy"]["base_memory_snapshot_sha256"] = "f"*64
    else:
        w["actors"][0].composed.values["candidate_experience_memory" if mutation == "unexpected-memory" else "experience_memory"] = {}
    refresh(w)
    with pytest.raises(PreparedFeedbackError):
        document(w)


def previous_memory(w, monkeypatch):
    """Replace only legacy materializer authority and actor-loader return with synthetic verified inputs."""
    from test_candidate_experience_memory import _record, _write_roster
    previous_id = "slurp:train:construct-1"
    path = w["data"] / "prior-roster.json"
    prior_sha = _write_roster(path, roster_id="PRIOR", role="construction", sample_ids=(previous_id,))
    record = _record(1, prior_sha)
    base = initialize_candidate_snapshot(memory_id=w["binding"]["memory_id"],
        train_construction_sha256=prior_sha, expected_train_sample_ids=(previous_id,), records=(record,))
    output = {"schema": "saea-provisional-consolidated-experience-candidates-v1", "status": "provisional",
              "provenance": {"construction_roster_sha256": prior_sha},
              "samples": [{"source_sample_id": previous_id, "records": [record.as_json()]}],
              "candidate_snapshot": base}
    artifact = prepare_artifact(w["data"] / "previous-candidates.json", kind=module.ARTIFACT_KIND,
                               inputs={"fixture": "replayed-prior"}, producer=lambda: output, contact_class="model-free")
    config_pin = pin(w["data"], "previous-config.json", {"fixture": "prior-memory"})
    base_pin = {"materialization_config": config_pin, "candidate_artifact": {
        "relpath": "previous-candidates.json", "sha256": artifact["sha256"]}, "snapshot_sha256": base["content_sha256"]}
    monkeypatch.setattr(module, "prepare_provisional_candidates", lambda **kwargs: artifact)
    expected = SimpleNamespace(records=(record,))
    calls = []
    def load_memory(*args, **kwargs):
        calls.append(kwargs)
        return expected
    monkeypatch.setattr(verification, "load_candidate_experience_memory", load_memory)
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    monkeypatch.setattr(verification, "default_phase_program",
                        lambda _name: default_phase_program("phase-native-review-revise-v1"))
    for actor in w["actors"]:
        actor.composed.values["candidate_experience_memory"] = {
            "artifact": {"sha256": artifact["sha256"]}}
    cumulative_path = w["data"] / "cumulative-roster.json"
    full = tuple(sorted((previous_id, *w["actor"].sample_ids)))
    cumulative_sha = _write_roster(cumulative_path, roster_id="CUMULATIVE", role="construction", sample_ids=full)
    w["binding"].update(base_memory=base_pin, cumulative_construction_roster={
        "relpath": "cumulative-roster.json", "sha256": cumulative_sha})
    w["policy"]["base_memory_snapshot_sha256"] = base["content_sha256"]
    refresh(w)
    return base, record, calls, expected


def test_next_round_keeps_sampling_memory_separate_from_updated_exposure(round_world, monkeypatch):
    w = round_world
    base, old, calls, _ = previous_memory(w, monkeypatch)
    before = copy.deepcopy(base)
    doc = document(w)
    assert doc["round_policy_receipt"]["base_snapshot_sha256"] == base["content_sha256"]
    assert doc["base_snapshot"]["content_sha256"] != base["content_sha256"]
    assert doc["base_snapshot"]["parent_snapshot_sha256"] == base["content_sha256"]
    assert doc["base_snapshot"]["records"] == [old.as_json()] and base == before
    assert len(doc["full_construction_sample_ids"]) == 1
    assert len(doc["memory_construction"]["sample_ids"]) == 2 and len(calls) == 2
    assert doc["contexts"][0]["model_context"]["existing_experiences"][0]["guidance"] == old.guidance


@pytest.mark.parametrize("mutation", ["foreign-artifact", "no-memory", "pack-order", "drop-prior", "extra-exposure", "overlap"])
def test_wrong_memory_and_shrunken_or_fabricated_exposure_refuse(round_world, monkeypatch, mutation):
    from test_candidate_experience_memory import _write_roster
    w = round_world
    base, _, _, expected = previous_memory(w, monkeypatch)
    if mutation == "foreign-artifact":
        w["actors"][0].composed.values["candidate_experience_memory"]["artifact"]["sha256"] = "f"*64
    elif mutation == "no-memory":
        w["actors"][0].composed.values.pop("candidate_experience_memory")
    elif mutation == "pack-order":
        expected.records = ()
    else:
        ids = list(w["actor"].sample_ids)
        if mutation == "extra-exposure":
            ids += base["train_sample_ids"] + ["slurp:train:unobserved"]
        elif mutation == "overlap":
            # Replace the replayed base with one claiming the current cohort;
            # the legacy reader still checks the fully bound snapshot identity.
            w["binding"]["source_construction_roster"] = {"relpath": "prior-roster.json",
                "sha256": base["train_construction_sha256"]}
        path = w["data"] / "bad-cumulative.json"
        sha = _write_roster(path, roster_id="BAD", role="construction", sample_ids=tuple(ids))
        w["binding"]["cumulative_construction_roster"] = {"relpath": path.name, "sha256": sha}
        refresh(w)
    with pytest.raises(ValueError):
        document(w)


def test_second_round_batch_replay_preserves_old_provenance_and_reaches_native_runtime(round_world, tmp_path, monkeypatch):
    from test_system_batch_update import batch_world as make_batch
    from test_system_semantic_memory import semantic_world as make_semantic, execute, attested
    import test_provisional_candidate_materialization as fixtures
    from speech_aware_evidence_acquisition.rails.candidate_experience_memory import _records
    w = round_world
    base, old, _, _ = previous_memory(w, monkeypatch)
    batch = make_batch.__wrapped__(w, tmp_path / "round-two", monkeypatch)
    semantic = make_semantic.__wrapped__(batch, tmp_path / "round-two", monkeypatch)
    result = execute(semantic)
    proof = attested(semantic, result)
    output = json.loads(Path(result["path"]).read_text())["output"]
    full_sha = w["binding"]["cumulative_construction_roster"]["sha256"]
    rows = _records(output, full_sha)
    assert len(rows) == 2 and old.as_json() in [r.as_json() for r in rows]
    assert {r.train_construction_sha256 for r in rows} == {base["train_construction_sha256"], full_sha}
    source = {"data_root": w["data"], "receipt": result, "attestation": proof,
              "roster_path": w["data"] / "cumulative-roster.json"}
    monkeypatch.setattr(fixtures, "_real_materialized_source", lambda *a, **k: source)
    used = fixtures._connected_candidate_native_source(None, None, tmp_path / "connected", monkeypatch)
    assert len(used["memory"].records) == 2
    assert set(used["memory"].records) == set(rows)
    # The actual runtime loader, not the substituted offline actor loader,
    # checked a later roster disjoint from the entire cumulative scope.
    assert not set(used["world"]["evaluation_ids"]) & set(output["candidate_snapshot"]["train_sample_ids"])

def test_deleted_guidance_does_not_erase_prior_exposure_or_allow_self_evaluation(round_world, tmp_path, monkeypatch):
    from dataclasses import replace
    from test_system_batch_update import batch_world as make_batch
    from test_system_semantic_memory import semantic_world as make_semantic, execute, attested, operation
    from test_system_group_update import response
    from test_candidate_experience_memory import _write_roster, _load, CandidateExperienceMemoryError
    import test_provisional_candidate_materialization as fixtures
    from speech_aware_evidence_acquisition.data.splits import split_identity_hash, prefixed
    w = round_world
    _, old, _, _ = previous_memory(w, monkeypatch)
    batch = make_batch.__wrapped__(w, tmp_path / "round-two", monkeypatch)
    semantic = make_semantic.__wrapped__(batch, tmp_path / "round-two", monkeypatch)
    response({"stage": semantic["stage"]}, json.dumps({"operations": [
        operation("DELETE", old.record_id), operation()]}))
    result = execute(semantic)
    proof = attested(semantic, result)
    output = json.loads(Path(result["path"]).read_text())["output"]
    assert len(output["candidate_snapshot"]["records"]) == 1
    assert old.source.source_sample_id in output["candidate_snapshot"]["train_sample_ids"]
    assert next(row for row in output["samples"] if row["source_sample_id"] == old.source.source_sample_id)["records"] == []
    source = {"data_root": w["data"], "receipt": result, "attestation": proof,
              "roster_path": w["data"] / "cumulative-roster.json"}
    monkeypatch.setattr(fixtures, "_real_materialized_source", lambda *a, **k: source)
    used = fixtures._connected_candidate_native_source(None, None, tmp_path / "connected", monkeypatch)
    world = used["world"]
    world["data_root"] = w["data"]
    ids = (old.source.source_sample_id, world["evaluation_ids"][1])
    world["evaluation_ids"] = ids
    world["plan"] = replace(used["plan"], split_identity_hash=split_identity_hash(prefixed("slurp", ids)))
    path = world["repo_root"] / "exposed-evaluation.json"
    sha = _write_roster(path, roster_id="EXPOSED", role="evaluation", sample_ids=ids)
    world["config"]["candidate_experience_memory"]["evaluation_roster"] = {
        "repo_relpath": path.name, "sha256": sha}
    with pytest.raises(CandidateExperienceMemoryError, match="overlap"):
        _load(world)
