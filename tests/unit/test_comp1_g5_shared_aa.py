"""Owner decision 160: COMP-1 and G5 fly in ONE campaign with ONE shared in-chain A/A.

Two groups of assertions. The pure helpers of
``scripts/flights/comp1/comp1_g5_shared_aa_proof.py`` (the tool that proves the decision's
condition model-free) are exercised on synthetic inputs, so a classification or comparison defect
cannot pass silently. Config only otherwise: no data root, no lock, no adapter, no contact.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PROOF_TOOL = REPO / "scripts/flights/comp1/comp1_g5_shared_aa_proof.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("comp1_g5_shared_aa_proof", PROOF_TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tool():
    return _load_tool()


# ---------------------------------------------------------------------------------------------
# the proof tool's pure helpers
# ---------------------------------------------------------------------------------------------


def test_flatten_keys_dicts_by_dot_and_lists_by_index(tool) -> None:
    flat = tool.flatten({"a": {"b": [1, {"c": 2}], "e": {}}, "f": []})
    assert flat == {"a.b[0]": 1, "a.b[1].c": 2, "a.e": {}, "f": []}


@pytest.mark.parametrize(
    ("leaf", "klass"),
    [
        ("cells[0].run_id", "bookkeeping"),
        ("cells[0].readiness.requirements[0].sha256", "bookkeeping"),
        ("cells[0].readiness.requirements", "bookkeeping"),
        ("experiment_id", "bookkeeping"),
        ("native_contact_fit.run_id", "bookkeeping"),
        ("generation_budget.target", "bookkeeping"),
        ("what_this_is", "bookkeeping"),
        ("knowledge_stores.intent-boundaries.phase_supply.perception.k", "supply-recall-width"),
        # anything that could reach a request is never waved through
        ("phase_material.reviewer.instruction_template", "unclassified"),
        ("native_contact_fit.budget_tokens", "unclassified"),
        ("knowledge_stores.intent-boundaries.phase_supply.perception.rank_weights.w_agree", "unclassified"),
        ("policy", "unclassified"),
        ("cellsX", "unclassified"),
    ],
)
def test_classify_leaf_names_bookkeeping_and_the_recall_width_and_nothing_else(tool, leaf, klass) -> None:
    assert tool.classify_leaf(leaf)[0] == klass


def test_config_diff_marks_only_unclassified_leaves_request_affecting(tool) -> None:
    left = {"experiment_id": "A", "policy": "p", "knowledge_stores": {"intent-boundaries": {
        "phase_supply": {"perception": {"k": 60}}}}}
    right = {"experiment_id": "B", "policy": "q", "knowledge_stores": {"intent-boundaries": {
        "phase_supply": {"perception": {"k": 8}}}}}
    rows = {row["leaf"]: row for row in tool.config_diff(left, right)}
    assert set(rows) == {"experiment_id", "policy",
                         "knowledge_stores.intent-boundaries.phase_supply.perception.k"}
    assert rows["policy"]["request_affecting"] is True
    assert rows["experiment_id"]["request_affecting"] is False
    assert rows["knowledge_stores.intent-boundaries.phase_supply.perception.k"]["class"] == "supply-recall-width"


def test_contact_key_and_role_come_from_the_last_history_turn(tool) -> None:
    payload = {"sample_id": "s1", "history": [
        {"contact_id": "pol:perception:0:s1"}, {"contact_id": "pol:planner:1:s1"}]}
    key = tool.contact_key(payload)
    assert key == "s1|pol:planner:1:s1"
    assert tool.role_of(key.split("|", 1)[1]) == ("planner", 1)
    with pytest.raises(ValueError):
        tool.contact_key({"sample_id": "s1", "history": []})


def test_canned_answers_are_deterministic_and_role_shaped(tool) -> None:
    intents = tool.CANNED_INTENTS
    perception = json.loads(tool.canned_answer("perception", 0, "s", intents))
    assert [c["intent_id"] for c in perception["candidates"]] == list(intents)
    assert json.loads(tool.canned_answer("solver", 0, "s", intents)) == {
        "scenario": "weather", "action": "query", "entities": []}
    revising = next(f"s{i}" for i in range(64) if tool.revises_first(f"s{i}"))
    accepting = next(f"s{i}" for i in range(64) if not tool.revises_first(f"s{i}"))
    assert tool.canned_answer("planner", 0, revising, intents) == "REVISE"
    assert tool.canned_answer("planner", 1, revising, intents) == "ACCEPT"
    assert tool.canned_answer("planner", 0, accepting, intents) == "ACCEPT"
    with pytest.raises(ValueError):
        tool.canned_answer("summariser", 0, "s", intents)


def test_the_run_id_normalization_blanks_only_the_run_id_derived_field(tool) -> None:
    payload = {"history": [{"source_query_state_sha256": "x", "content": "c"}], "request_id": "r"}
    assert tool.run_id_normalized_payload(payload) == {
        "history": [{"source_query_state_sha256": "<run-id-derived>", "content": "c"}],
        "request_id": "r",
    }


def _row(payload: str, normalized: str, body: str) -> dict:
    return {"payload_sha256": payload, "normalized_payload_sha256": normalized, "body_sha256": body}


def test_compare_captures_reports_each_byte_level_separately(tool) -> None:
    same = tool.compare_captures({"k": _row("p", "n", "b")}, {"k": _row("p", "n", "b")})
    assert same["payload_bytes_identical"] and same["post_body_bytes_identical"]
    assert same["run_id_normalized_payload_bytes_identical"]
    run_id_only = tool.compare_captures({"k": _row("p1", "n", "b")}, {"k": _row("p2", "n", "b")})
    assert not run_id_only["payload_bytes_identical"]
    assert run_id_only["run_id_normalized_payload_bytes_identical"]
    assert run_id_only["post_body_bytes_identical"]
    body = tool.compare_captures({"k": _row("p", "n", "b1")}, {"k": _row("p", "n", "b2")})
    assert not body["post_body_bytes_identical"] and body["first_mismatches"] == ["k"]
    missing = tool.compare_captures({"k": _row("p", "n", "b"), "j": _row("p", "n", "b")},
                                    {"k": _row("p", "n", "b")})
    assert not missing["keys_equal"] and not missing["payload_bytes_identical"]
    assert missing["only_in_comp1_aa"] == ["j"]


def test_identity_hashes_are_quoted_by_prefix_and_output_digests_in_full(tool) -> None:
    full = "ab" * 32
    quoted = tool.quote_hashes_by_prefix({
        "composed_config_hash": full, "output_sha256": full, "sealed_plan_output_sha256": full,
        "rows": [{"sha256": full}], "note": "not a hash", "short": "abcd",
    })
    assert quoted["composed_config_hash"] == "sha256-prefix16:" + full[:16]
    assert quoted["rows"][0]["sha256"] == "sha256-prefix16:" + full[:16]
    assert quoted["output_sha256"] == full and quoted["sealed_plan_output_sha256"] == full
    assert quoted["note"] == "not a hash" and quoted["short"] == "abcd"


def test_the_self_control_counts_differing_fields_per_contact(tool) -> None:
    first = {"k": {"payload": json.dumps({"request_id": "a", "history": [{"x": 1}]}),
                   "body": json.dumps({"id_slot": 0, "messages": []})}}
    second = {"k": {"payload": json.dumps({"request_id": "b", "history": [{"x": 1}]}),
                    "body": json.dumps({"id_slot": 3, "messages": []})}}
    reading = tool.self_control_reading(first, second, 1)
    assert reading["payload_fields_differing"] == {"request_id": 1}
    assert reading["post_body_fields_differing"] == {"id_slot": 1}
    assert reading["keys_equal"] and reading["contacts"] == 1


def test_classify_supply_input_names_the_recall_width_and_its_identity_hash(tool) -> None:
    assert tool.classify_supply_input("sources.supply_spec.k") == "supply-recall-width"
    assert tool.classify_supply_input("config_sha256").startswith("supply-config-identity-hash")
    assert tool.classify_supply_input("sources.supply_spec.rank_weights.w_agree") == "unclassified"
