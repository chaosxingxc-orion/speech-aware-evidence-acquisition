# ruff: noqa: F811
"""Test model-authored synthesis, atomic memory lineage and actual shared runtime use."""
import copy
import hashlib
import json
from pathlib import Path

import pytest
from test_system_summary_preparation import summary_world, pin  # noqa: F401
from test_system_comparison_preparation import comparison_world  # noqa: F401
from test_system_group_update import update_world, response  # noqa: F401
from test_system_batch_update import batch_world, prepared  # noqa: F401
from test_system_summary_source import make_text_stage_source
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401

from speech_aware_evidence_acquisition.core import system_semantic_memory as module
from speech_aware_evidence_acquisition.core.provisional_candidate_materialization import (
    MaterializationError, prepare_provisional_candidates)
from speech_aware_evidence_acquisition.rails.system_batch_update_context import build_system_batch_update_contexts
from speech_aware_evidence_acquisition.rails.candidate_experience_memory import (
    _records, prepare_candidate_experience_source_attestation)


def proposal():
    return {"kind": "corrective-experience",
            "diagnosis": "Supported repairs can be lost across later roles.",
            "guidance": "At review, compare the proposed correction against its evidence; retain it only while that evidence remains valid through delivery.",
            "limitations": ["Construction evidence is provisional and does not establish causal role credit."],
            "applicability": {"task_ids": ["slurp"], "phases": ["reviewer"], "component_tags": ["org"],
                              "required_conditions": ["state:prior-response-present"], "excluded_conditions": []},
            "primary_option": "group-1", "supporting_options": ["group-1"], "contradicting_options": []}


def operation(kind="ADD", target=None):
    return {"operation": kind, "record_id": target, "proposal": None if kind == "DELETE" else proposal()}


@pytest.fixture
def semantic_world(batch_world, tmp_path, monkeypatch):  # noqa: F811
    return make_semantic_world(batch_world, tmp_path, monkeypatch)


def make_semantic_world(w, tmp_path, monkeypatch, baseline="system-batch-update-text-v1"):
    """Keep sealed-stage setup shared across source contract versions."""
    spec, _ = prepared(w)
    inputs = (w["data"], w["actor"], {"construction_roster": w["binding"]["batch_roster"]}, w["source_pin"], [])
    stage = make_text_stage_source(inputs, tmp_path, monkeypatch, prepared_spec=spec,
                                  baseline=baseline, stage_name="batch")
    response({"stage": stage}, json.dumps({"operations": [operation()]}))
    config = {"schema": module.CONFIG_SCHEMA, "materialization_id": "synthetic-semantic-memory",
              "max_candidates": 8,
              "batch_manifest": {"path": str(w["data"] / stage["pin"]["relpath"]), "sha256": stage["pin"]["sha256"]},
              "batch_repo_root": str(stage["repo"])}
    config_path = w["data"] / "semantic-config.json"
    config_path.write_text(json.dumps(config))
    return {"batch": w, "data": w["data"], "stage": stage, "config": config, "config_path": config_path}


def execute(w):
    return prepare_provisional_candidates(config_path=w["config_path"],
        expected_config_sha256=hashlib.sha256(w["config_path"].read_bytes()).hexdigest(), data_root=w["data"])


def attested(w, receipt):
    return prepare_candidate_experience_source_attestation(
        config_path=w["config_path"], expected_config_sha256=hashlib.sha256(w["config_path"].read_bytes()).hexdigest(),
        data_root=w["data"], candidate_artifact_relpath=str(Path(receipt["path"]).relative_to(w["data"])),
        expected_candidate_sha256=receipt["sha256"], output_relpath="prepared/semantic-attestation.json")


def test_synthesis_can_create_new_content_and_replay_whole_system_provenance(semantic_world):
    w = semantic_world
    before = copy.deepcopy(w["stage"]["response"])
    result = execute(w)
    output = json.loads(Path(result["path"]).read_text())["output"]
    roster_sha = output["provenance"]["construction_roster_sha256"]
    records = _records(output, roster_sha)
    assert len(records) == 1 and records[0].guidance == proposal()["guidance"]
    assert proposal()["guidance"] not in w["batch"]["stage"]["response"]["text"]
    assert records[0].supporting_source_refs[0].ref_id.startswith("complete-system-group:")
    assert records[0].validation.status == "provisional"
    assert records[0].validation.protocol_sha256 == w["stage"]["bundle"].manifest["plan"]["protocol_hash"]
    assert output["candidate_snapshot"]["train_sample_ids"] == list(w["batch"]["actor"].sample_ids)
    assert w["stage"]["response"] == before
    again = execute(w)
    assert again["cache"] == "warm" and again["sha256"] == result["sha256"]
    receipt = attested(w, result)
    assert receipt["sha256"]


def test_source_attested_new_content_reaches_reviewer_tool_and_solver_revision(semantic_world, tmp_path, monkeypatch):
    import test_provisional_candidate_materialization as fixtures
    w = semantic_world
    result = execute(w)
    proof = attested(w, result)
    source = {"data_root": w["data"], "receipt": result, "attestation": proof,
              "roster_path": w["data"] / w["batch"]["binding"]["batch_roster"]["relpath"]}
    monkeypatch.setattr(fixtures, "_real_materialized_source", lambda *a, **k: source)
    used = fixtures._connected_candidate_native_source(None, None, tmp_path / "connected", monkeypatch)
    assert len(used["memory"].records) == 1
    assert used["memory"].records[0].guidance == proposal()["guidance"]
    assert all(row["text"].endswith(":visit:2") for row in used["canonical"])


@pytest.mark.parametrize("mutation", ["foreign-group", "model-id", "scope", "duplicate-target", "too-many", "malformed", "duplicate-key", "capped", "candidate-cap"])
def test_invalid_synthesis_is_retained_without_publishing_any_candidate(semantic_world, mutation):
    w = semantic_world
    value = {"operations": [operation()]}
    count = 20
    if mutation == "foreign-group":
        value["operations"][0]["proposal"]["primary_option"] = "group-unknown"
    elif mutation == "model-id":
        value["operations"][0]["record_id"] = "invented"
    elif mutation == "scope":
        value["operations"][0]["proposal"]["applicability"]["phases"] = ["foreign-role"]
    elif mutation == "duplicate-target":
        value["operations"] = [operation("DELETE", "unknown")]*2
    elif mutation == "too-many":
        value["operations"] *= 9
    elif mutation == "capped":
        count = 128
    elif mutation == "candidate-cap":
        w["config"]["max_candidates"] = 0
        w["config_path"].write_text(json.dumps(w["config"]))
    raw = json.dumps(value)
    if mutation == "malformed":
        raw = "not JSON"
    if mutation == "duplicate-key":
        raw = '{"operations":[],"operations":[]}'
    response({"stage": w["stage"]}, raw, count)
    with pytest.raises(MaterializationError, match="retained"):
        execute(w)
    target = w["data"] / "provisional/experience-candidates/synthetic-semantic-memory.json"
    assert not target.exists()
    rejection = json.loads((w["data"] / "provisional/system-semantic-rejections/synthetic-semantic-memory.json").read_text())["output"]
    assert rejection["snapshot"] is None and rejection["batch_response"]["text"] == raw
    assert rejection["runtime_authorized"] is False


def test_unmodified_upstream_sources_are_required_on_warm_replay(semantic_world):
    w = semantic_world
    result = execute(w)
    before = Path(result["path"]).read_bytes()
    response({"stage": w["batch"]["stage"]}, '[{"operation":"ADD","id":null,"content":"Changed group proposal."}]')
    with pytest.raises(ValueError):
        execute(w)
    assert Path(result["path"]).read_bytes() == before


def test_new_content_with_update_delete_and_add_preserves_atomic_stable_ids(batch_world):
    from speech_aware_evidence_acquisition.rails.experience_consolidation import consolidate_experience_candidates
    w = batch_world
    doc = build_system_batch_update_contexts(w["source_pin"], data_root=w["data"])
    args = dict(manifest_sha="a"*64, protocol_sha="b"*64, response_sha="c"*64, config_sha="d"*64)
    first_ops = module.parse_batch_operations(json.dumps({"operations": [operation(), operation()]}), doc, w["actor"].sample_ids[0])
    first_ops[1]["proposal"]["guidance"] += " Check evidence freshness."
    records, plan = module.synthesize_records(first_ops, doc, **args)
    bindings = {"complete_system_feedback_sha256": "a"*64, "proposal_artifact_sha256": "b"*64, "consolidation_response_sha256": "c"*64}
    first = consolidate_experience_candidates(doc["base_snapshot"], plan, records, round_id="one", source_bindings=bindings)
    assert first["status"] == "applied"
    base = first["snapshot"]
    before = copy.deepcopy(base)
    keep, remove = [r["record_id"] for r in base["records"]]
    doc["base_snapshot"] = base
    update = operation("UPDATE", keep)
    update["proposal"]["guidance"] += " Preserve uncertainty when evidence is incomplete."
    addition = operation()
    addition["proposal"]["guidance"] = "Review the final delivered answer for unsupported changes after a revision."
    raw = json.dumps({"operations": [update, operation("DELETE", remove), addition]})
    operations = module.parse_batch_operations(raw, doc, w["actor"].sample_ids[0])
    records, plan = module.synthesize_records(operations, doc, **dict(args, manifest_sha="e"*64))
    result = consolidate_experience_candidates(base, plan, records, round_id="two", source_bindings=bindings)
    assert result["status"] == "applied" and base == before
    rows = {r["record_id"]: r for r in result["snapshot"]["records"]}
    updated = next(r for r in rows.values() if r["supersedes_record_id"] == keep)
    assert updated["record_id"] != keep and updated["revision"] == 2
    assert keep not in rows and remove not in rows
    assert remove in result["snapshot"]["issued_record_ids"]
    assert len(rows) == 2 and not set(rows) & set(base["issued_record_ids"])
    invalid = json.dumps({"operations": [operation("UPDATE", keep), operation("DELETE", keep)]})
    with pytest.raises(MaterializationError, match="repeated"):
        module.parse_batch_operations(invalid, doc, w["actor"].sample_ids[0])


def test_empty_batch_response_preserves_memory_without_inventing_guidance(semantic_world):
    w = semantic_world
    response({"stage": w["stage"]}, '{"operations":[]}')
    result = execute(w)
    out = json.loads(Path(result["path"]).read_text())["output"]
    assert out["candidate_snapshot"]["records"] == []
    assert out["consolidation_receipts"][0]["status"] == "unchanged"

def test_multi_group_synthesis_keeps_full_exposure_scope_and_all_cited_sources(batch_world, tmp_path, monkeypatch):
    from test_system_batch_update import widen_group_report
    w = batch_world
    report, full_pin = widen_group_report(w, monkeypatch)
    spec, _ = prepared(w)
    inputs = (w["data"], w["actor"], {"construction_roster": w["binding"]["batch_roster"]}, w["source_pin"], [])
    stage = make_text_stage_source(inputs, tmp_path, monkeypatch, prepared_spec=spec,
                                  baseline="system-batch-update-text-v1", stage_name="wide-batch")
    combined = operation()
    combined["proposal"].update(primary_option="group-2", supporting_options=["group-1", "group-2"])
    response({"stage": stage}, json.dumps({"operations": [combined]}))
    config = {"schema": module.CONFIG_SCHEMA, "materialization_id": "wide-memory", "max_candidates": 8,
              "batch_manifest": {"path": str(w["data"] / stage["pin"]["relpath"]), "sha256": stage["pin"]["sha256"]},
              "batch_repo_root": str(stage["repo"])}
    path = w["data"] / "wide-memory-config.json"
    path.write_text(json.dumps(config))
    materialized = execute({"data": w["data"], "config_path": path})
    output = json.loads(Path(materialized["path"]).read_text())["output"]
    assert output["candidate_snapshot"]["train_sample_ids"] == sorted(report["full_construction_sample_ids"])
    assert [s["source_sample_id"] for s in output["samples"]] == report["full_construction_sample_ids"]
    assert output["samples"][0]["records"] == []
    records = _records(output, full_pin["sha256"])
    assert len(records) == 1 and records[0].source.source_sample_id == "slurp:train:extra"
    assert len(records[0].supporting_source_refs) == 2
    assert records[0].train_construction_sha256 != w["binding"]["batch_roster"]["sha256"]


def test_model_declared_conflicting_support_is_refused(batch_world):
    w = batch_world
    doc = build_system_batch_update_contexts(w["source_pin"], data_root=w["data"])
    value = operation()
    value["proposal"]["contradicting_options"] = ["group-1"]
    with pytest.raises(ValueError, match="inconsistent"):
        module.parse_batch_operations(json.dumps({"operations": [value]}), doc, w["actor"].sample_ids[0])
