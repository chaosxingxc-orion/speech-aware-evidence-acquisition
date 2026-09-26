# ruff: noqa: F811
"""Prove visible pool limits reach fit, synthesis, source replay and memory use."""
import copy
import json
from pathlib import Path

import pytest
from test_system_summary_preparation import summary_world, pin, exercise_shared_fit_and_send  # noqa: F401
from test_system_comparison_preparation import comparison_world  # noqa: F401
from test_system_group_update import update_world, response  # noqa: F401
from test_system_batch_update import batch_world, prepared, load  # noqa: F401
from test_system_semantic_memory import make_semantic_world, execute, attested, operation, proposal
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401

from speech_aware_evidence_acquisition.rails import system_batch_update_context as context_module
from speech_aware_evidence_acquisition.core import system_semantic_memory as memory_module
from speech_aware_evidence_acquisition.core.provisional_candidate_materialization import MaterializationError
from speech_aware_evidence_acquisition.rails.prepared_feedback import PreparedFeedbackError

V2 = "saea-system-batch-update-source-v2"
BASELINE = "system-batch-update-bounded-text-v1"


@pytest.fixture
def bounded_world(batch_world):
    w = batch_world
    w["binding"].update(schema=V2, max_memory_records=8)
    w["source_pin"] = pin(w["data"], "bounded-source.json", w["binding"])
    return w


@pytest.fixture
def bounded_semantic(bounded_world, tmp_path, monkeypatch):
    bounded_world["binding"]["max_memory_records"] = 2
    bounded_world["source_pin"] = pin(bounded_world["data"], "bounded-source.json", bounded_world["binding"])
    w = make_semantic_world(bounded_world, tmp_path, monkeypatch, BASELINE)
    w["config"]["max_candidates"] = 2
    w["config_path"].write_text(json.dumps(w["config"]))
    return w


@pytest.mark.parametrize("cap", [1, 8, 32])
def test_visible_limit_is_bound_in_prepared_input_and_real_fit_send(bounded_world, tmp_path, cap):
    w = bounded_world
    w["binding"]["max_memory_records"] = cap
    w["source_pin"] = pin(w["data"], "bounded-source.json", w["binding"])
    spec, _ = prepared(w)
    states, _ = load(w, spec)
    model_context = json.loads(next(iter(states.values())).content)
    assert model_context["max_memory_records"] == cap
    doc = context_module.build_system_batch_update_contexts(w["source_pin"], data_root=w["data"])
    assert doc["schema"] == "saea-system-batch-update-contexts-v2"
    assert doc["max_memory_records"] == cap
    assert doc["model_contacts_added"] == 0
    inputs = (w["data"], w["actor"], {"construction_roster": w["binding"]["batch_roster"]}, w["source_pin"], [])
    proof = exercise_shared_fit_and_send(inputs, tmp_path / "consumer", True,
        prepared_spec=spec, baseline=BASELINE, batch_update=True, output_text='{"operations":[]}')
    assert json.loads(proof["sent"]["history"][0]["content"])["max_memory_records"] == cap
    assert "max_memory_records" in proof["sent"]["history"][-1]["content"]


@pytest.mark.parametrize("cap", [0, -1, 33, True, 1.5, "8", None])
def test_invalid_or_unsupported_pool_limit_fails_before_preparation(bounded_world, cap):
    w = bounded_world
    w["binding"]["max_memory_records"] = cap
    w["source_pin"] = pin(w["data"], "invalid-bound.json", w["binding"])
    with pytest.raises(PreparedFeedbackError, match="max_memory_records"):
        prepared(w)
    assert not (w["data"] / "prepared/batch.json").exists()


def test_legacy_contract_has_no_new_model_fields_and_rejects_undeclared_limit(batch_world):
    w = batch_world
    doc = context_module.build_system_batch_update_contexts(w["source_pin"], data_root=w["data"])
    assert doc["schema"] == "saea-system-batch-update-contexts-v1"
    assert "max_memory_records" not in doc
    assert "max_memory_records" not in doc["contexts"][0]["model_context"]
    binding = dict(w["binding"], max_memory_records=8)
    source = pin(w["data"], "legacy-extra.json", binding)
    with pytest.raises(PreparedFeedbackError, match="fields"):
        context_module.build_system_batch_update_contexts(source, data_root=w["data"])


def test_v2_requires_explicit_limit(bounded_world):
    w = bounded_world
    del w["binding"]["max_memory_records"]
    source = pin(w["data"], "missing-limit.json", w["binding"])
    with pytest.raises(PreparedFeedbackError, match="fields"):
        context_module.build_system_batch_update_contexts(source, data_root=w["data"])


@pytest.mark.parametrize("ops,cap,valid", [
    ([], 2, True), ([], 1, False),
    ([operation()], 2, False),
    ([operation("UPDATE", "old-1")], 2, True),
    ([operation(), operation("DELETE", "old-2")], 2, True),
    ([operation("DELETE", "old-1")], 1, True),
])
def test_final_pool_counts_unchanged_records_and_atomic_deletions(bounded_world, ops, cap, valid):
    w = bounded_world
    doc = context_module.build_system_batch_update_contexts(w["source_pin"], data_root=w["data"])
    doc["base_snapshot"]["records"] = [{"record_id": "old-1"}, {"record_id": "old-2"}]
    doc["max_memory_records"] = cap
    before = copy.deepcopy(doc)
    raw = json.dumps({"operations": ops})
    if valid:
        assert len(memory_module.parse_batch_operations(raw, doc, w["actor"].sample_ids[0])) == len(ops)
    else:
        with pytest.raises(MaterializationError, match="memory record"):
            memory_module.parse_batch_operations(raw, doc, w["actor"].sample_ids[0])
    assert doc == before


@pytest.mark.parametrize("mode", ["mismatch-smaller", "mismatch-larger", "overflow"])
def test_refusal_preserves_raw_response_without_publishing_proposals(bounded_semantic, mode):
    w = bounded_semantic
    raw = json.dumps({"operations": [operation()] * (3 if mode == "overflow" else 1)})
    if mode.startswith("mismatch"):
        w["config"]["max_candidates"] = 1 if mode == "mismatch-smaller" else 3
        w["config_path"].write_text(json.dumps(w["config"]))
    response({"stage": w["stage"]}, raw)
    with pytest.raises(MaterializationError, match="retained"):
        execute(w)
    name = w["config"]["materialization_id"] + ".json"
    assert not (w["data"] / "provisional/experience-candidates" / name).exists()
    assert not (w["data"] / "provisional/system-semantic-proposals" / name).exists()
    rejection = json.loads((w["data"] / "provisional/system-semantic-rejections" / name).read_text())["output"]
    assert rejection["snapshot"] is None and rejection["batch_response"]["text"] == raw
    assert rejection["max_memory_records"] == 2


def test_bounded_source_attestation_reaches_reviewer_and_full_revision(bounded_semantic, tmp_path, monkeypatch):
    import test_provisional_candidate_materialization as fixtures
    w = bounded_semantic
    result = execute(w)
    proof = attested(w, result)
    source = {"data_root": w["data"], "receipt": result, "attestation": proof,
              "roster_path": w["data"] / w["batch"]["binding"]["batch_roster"]["relpath"]}
    monkeypatch.setattr(fixtures, "_real_materialized_source", lambda *a, **k: source)
    used = fixtures._connected_candidate_native_source(None, None, tmp_path / "connected", monkeypatch)
    assert len(used["memory"].records) == 1
    assert used["memory"].records[0].guidance == proposal()["guidance"]
    assert all(row["text"].endswith(":visit:2") for row in used["canonical"])


def test_rehashed_different_source_limit_cannot_reuse_prepared_input(bounded_world):
    w = bounded_world
    spec, _ = prepared(w)
    binding = dict(w["binding"], max_memory_records=4)
    spec["source_bindings"] = pin(w["data"], "changed-bound.json", binding)
    with pytest.raises(PreparedFeedbackError):
        load(w, spec)


@pytest.mark.parametrize("count", [1, 3])
def test_no_operation_batch_cannot_bypass_pool_limit(bounded_world, monkeypatch, count):
    w = bounded_world
    response({"stage": w["stage"]}, '[{"operation":"NONE","id":null,"content":""}]')
    report = copy.deepcopy(context_module.read_system_group_operations(
        w["stage"]["pin"], repo_root=w["stage"]["repo"], data_root=w["data"]))
    # Substitute the upstream verified report only; exercise the no-contact builder.
    report["base_snapshot"]["records"] = [
        {key: value for key, value in dict(proposal(), record_id=f"old-{i}").items()
         if key in {"record_id", "kind", "diagnosis", "guidance", "limitations", "applicability"}}
        for i in range(count)]
    monkeypatch.setattr(context_module, "read_system_group_operations", lambda *a, **k: report)
    binding = dict(w["binding"], batch_roster=None, max_memory_records=2)
    source = pin(w["data"], "no-operation-bound.json", binding)
    if count <= 2:
        doc = context_module.build_system_batch_update_contexts(source, data_root=w["data"])
        assert doc["disposition"] == "no-change-no-operation" and doc["contexts"] == []
        assert len(doc["base_snapshot"]["records"]) == count
    else:
        with pytest.raises(PreparedFeedbackError, match="unchanged memory"):
            context_module.build_system_batch_update_contexts(source, data_root=w["data"])


def test_empty_model_update_is_valid_and_replayable_without_filling_pool(bounded_semantic):
    w = bounded_semantic
    response({"stage": w["stage"]}, '{"operations":[]}')
    result = execute(w)
    output = json.loads(Path(result["path"]).read_text())["output"]
    assert output["candidate_snapshot"]["records"] == []
    assert output["consolidation_receipts"][0]["status"] == "unchanged"
    assert attested(w, result)["sha256"]
