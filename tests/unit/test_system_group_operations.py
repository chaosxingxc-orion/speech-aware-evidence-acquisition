"""Keep invalid updater proposals and conflicts without mutating memory."""
import copy
import json

import pytest

from test_experience_consolidation import record, snapshot
from speech_aware_evidence_acquisition.analysis.system_group_operations import parse_group_operations


def test_operations_keep_content_and_frozen_target_without_applying():
    base = snapshot((record("existing"),))
    before = copy.deepcopy(base)
    operations = [{"operation": "ADD", "id": None, "content": "When evidence conflicts, recheck delivery."},
                  {"operation": "UPDATE", "id": "existing", "content": "Keep supported repairs after review."},
                  {"operation": "DELETE", "id": "existing", "content": ""},
                  {"operation": "NONE", "id": None, "content": ""}]
    raw = json.dumps(operations)
    result = parse_group_operations(raw, base)
    assert result["status"] == "valid" and result["operations"] == operations
    assert result["raw_text"] == raw and base == before
    assert result["base_snapshot_sha256"] == base["content_sha256"]
    # Conflicting UPDATE/DELETE is a proposal for batch reconciliation, not an applied plan.


@pytest.mark.parametrize("raw", [
    'not JSON', '{}', '[{"operation":"DELETE","id":"unknown","content":""}]',
    '[{"operation":"ADD","id":"invented","content":"rule"}]',
    '[{"operation":"UPDATE","id":"existing","content":""}]',
    '[{"operation":"DELETE","id":"existing","content":"new rule"}]',
    '[{"operation":"NONE","id":null,"content":"","admitted":true}]',
    '[{"operation":"NONE","operation":"ADD","id":null,"content":"rule"}]',
    '[{"operation":"EXECUTE","id":null,"content":"tool"}]',
])
def test_invalid_operations_are_recorded_without_repair(raw):
    base = snapshot((record("existing"),))
    result = parse_group_operations(raw, base)
    assert result["status"] == "invalid" and result["operations"] is None
    assert result["raw_text"] == raw and result["error"]


def test_empty_proposals_are_valid_no_change():
    result = parse_group_operations("[]", snapshot())
    assert result["status"] == "valid" and result["operations"] == []


@pytest.mark.parametrize("state,expected", [("usable", "ready"), ("output-limit", "blocked-unusable-update")])
def test_sealed_update_reader_keeps_full_population_and_base(monkeypatch, state, expected):
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.analysis import system_group_operations as module
    base = snapshot()
    source = SimpleNamespace(
        manifest_sha256="a"*64, prepared_document={
            "base_snapshot": base, "source_construction_roster_sha256": "b"*64,
            "full_construction_sample_ids": ["train-001", "train-002"],
            "ready_sample_ids": ["train-001"], "round_id": "round-1",
            "population": [{"sample_id": "train-001", "disposition": "ready", "experience_source": {"fixture": 1}},
                           {"sample_id": "train-002", "disposition": "no-update-terminal-tie", "experience_source": {"fixture": 2}}],
        },
        rows={"train-001": {"text": "[]", "status": state}})
    before = copy.deepcopy(source.prepared_document)
    calls = []
    def verified(*args, **kwargs):
        calls.append(kwargs)
        return source
    monkeypatch.setattr(module, "verify_prepared_text_source", verified)
    result = module.read_system_group_operations({}, repo_root="/fixture", data_root="/fixture-data")
    assert result["population"][0]["disposition"] == expected
    assert result["population"][1]["update_response"] is None
    assert result["full_construction_sample_ids"] == ["train-001", "train-002"]
    assert result["runtime_authorized"] is False and result["base_snapshot"] == base
    assert source.prepared_document == before
    assert calls[0]["input_schema"] == "saea-prepared-system-group-update-v1"
