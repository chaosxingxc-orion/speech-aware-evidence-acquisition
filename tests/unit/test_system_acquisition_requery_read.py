"""Protect causal ordering and complete evidence exclusion in offline replay."""
from pathlib import Path
import sys

import pytest
from speech_aware_evidence_acquisition.rails.hashing import content_hash

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/analysis"))
import system_acquisition_requery_read as reader


def fixture():
    records = {}
    visits = []
    for i, (stage, evidence) in enumerate([
        ("perception", ["kb::perception"]),
        ("solver", ["kb::solver"]),
        ("review", ["kb::solver"]),
        ("planner", ["kb::solver"]),
        ("solver", ["kb::future"]),
    ]):
        payload = {"sample_id": "row", "supplied_evidence": [
            {"evidence_id": eid} for eid in evidence],
            "history": ([{"state_kind": "phase:reviewer", "content": "Review a missing field."}]
                        if stage == "planner" else [])}
        record = {"payload": payload, "payload_sha256": content_hash(payload)}
        rid = f"r{i}/request"
        records[rid] = record
        visits.append({"stage": stage, "interrupted": False, "contacts": [{
            "request_record_id": rid, "request_record_sha256": content_hash(record),
            "request_payload_sha256": content_hash(payload)}]})
    return {"sample_id": "row", "role_visits": visits}, records


def test_boundary_accumulates_prior_solver_supply_but_never_future():
    trajectory, records = fixture()
    boundary = reader.review_boundary(trajectory, records)
    assert boundary["visible_ids"] == ["kb::perception", "kb::solver"]
    assert boundary["review"] == "Review a missing field."
    assert boundary["planner_request_id"] == "r3/request"


def test_missing_planner_is_explicit_not_dropped_or_defaulted():
    trajectory, records = fixture()
    trajectory["role_visits"] = trajectory["role_visits"][:3]
    assert reader.review_boundary(trajectory, records) is None


def test_changed_request_fails_closed():
    trajectory, records = fixture()
    records["r1/request"]["payload"]["supplied_evidence"] = []
    with pytest.raises(ValueError, match="fingerprint"):
        reader.review_boundary(trajectory, records)


def test_missing_review_state_fails_closed():
    trajectory, records = fixture()
    record = records["r3/request"]
    record["payload"]["history"] = []
    record["payload_sha256"] = content_hash(record["payload"])
    contact = trajectory["role_visits"][3]["contacts"][0]
    contact["request_record_sha256"] = content_hash(record)
    contact["request_payload_sha256"] = content_hash(record["payload"])
    with pytest.raises(ValueError, match="Reviewer state"):
        reader.review_boundary(trajectory, records)


def test_wrong_sample_fails_even_with_matching_hashes():
    trajectory, records = fixture()
    trajectory["sample_id"] = "another-row"
    with pytest.raises(ValueError, match="sample"):
        reader.review_boundary(trajectory, records)


def test_missing_evidence_ids_cannot_be_silently_treated_as_unseen():
    with pytest.raises(ValueError, match="snapshot"):
        reader.require_known_evidence(["missing"], {"kb::known": object()})


def test_query_surface_does_not_confuse_marker_with_executed_tool():
    from system_acquisition_query_surface import query_surface
    result = query_surface('{"tool_call":{"tool":"example"}}', ("tool_call",), {"call"})
    assert result["strict_json_tool_call_object"]
    assert result["retained_call_from_tool_call_filter"]
    assert not result["retained_other_token"]


def test_plain_review_is_not_a_structured_tool_call():
    from system_acquisition_query_surface import query_surface
    result = query_surface("A boundary needs evidence.", ("boundary",), {"boundary"})
    assert not result["strict_json_tool_call_object"]
    assert not result["tool_call_marker_in_review"]
    assert result["retained_other_token"]


def test_acquire_already_in_review_is_not_attributed_to_hypothetical_plan():
    from system_acquisition_query_surface import query_surface
    result = query_surface("Acquire evidence.", ("acquire", "evidence"), {"acquire"})
    assert result["retained_acquire_token"]
    assert not result["acquire_key_introduced_by_hypothetical_action"]


def test_appended_acquire_has_explicit_origin():
    from system_acquisition_query_surface import query_surface
    result = query_surface("Missing evidence.", ("missing", "evidence", "acquire"), {"acquire"})
    assert result["acquire_key_introduced_by_hypothetical_action"]
