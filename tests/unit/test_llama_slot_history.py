"""Join preserved numeric wire measurements to actual server slot history."""
import copy
import hashlib

import pytest

from speech_aware_evidence_acquisition.analysis.llama_slot_history import (
    SlotHistoryError, audit_slot_history, contacts_from_numeric_members,
)


def log_task(task, *, slot=0, tick=1, evaluated=10, generated=2,
             prefill=10.12, decode=20.34, truncated=0):
    def line(offset, message):
        return f"0.{tick + offset}.000.000 I slot update_slots: id {slot} | task {task} | {message}\n"
    return (line(0, "processing task, n_tokens = 100")
            + line(1, "decoded mmproj-free speech feature chunk, n_tokens = 7")
            + line(1, f"prompt eval time = {prefill:.2f} ms / {evaluated} tokens")
            + line(2, f"eval time = {decode:.2f} ms / {generated} tokens")
            + line(3, f"stop processing: n_tokens = 102, truncated = {truncated}"))


def contact(task, *, sample="s0", role="solver", layout="before-speech", slot=0,
            evaluated=10, generated=2, prefill=10.12, decode=20.34):
    return {"run_id": "run", "request_id": f"r{task}", "sample_id": sample,
            "role_id": role, "layout": layout, "schedule": "panel",
            "requested_slot_id": slot, "system_message_sha256": "a" * 64,
            "role_query_sha256": ("b" if role == "solver" else "c") * 64,
            "request_body_sha256": str(task % 10) * 64,
            "measurements": {"evaluated_input_tokens": evaluated, "generated_tokens": generated,
                "prefill_ms": prefill, "generation_ms": decode,
                "input_tokens": 100, "reused_input_tokens": 90, "client_transport_ms": 40}}


def audit(contacts, text):
    raw = text.encode()
    return audit_slot_history(contacts, raw, expected_sha256=hashlib.sha256(raw).hexdigest())


def test_actual_slot_predecessor_uses_server_order_not_client_order():
    text = (log_task(0, tick=1, evaluated=77) + log_task(1, tick=5)
            + log_task(2, tick=9, evaluated=11) + log_task(3, tick=13, evaluated=12)
            + log_task(4, tick=17, evaluated=13) + log_task(5, tick=21, evaluated=14)
            + log_task(6, tick=25, evaluated=15))
    cs = [contact(1), contact(2, sample="s1", evaluated=11),
          contact(3, sample="s1", evaluated=12),
          contact(4, role="reviewer", sample="s1", evaluated=13),
          contact(5, role="planner", sample="s2", evaluated=14),
          contact(6, role="planner", layout="legacy", sample="s2", evaluated=15)]
    report = audit(list(reversed(cs)), text)
    rows = report["contacts"]
    assert [r["request_id"] for r in rows] == [f"r{i}" for i in range(1, 7)]
    assert [r["successor_kind"] for r in rows] == [
        "outside-family", "same-node-same-context-different-sample",
        "same-node-same-context-same-sample", "different-node-same-sample",
        "different-node-different-sample", "same-node-context-change"]
    assert rows[0]["server"]["task_id"] == 1
    assert rows[0]["server"]["actual_slot_id"] == 0
    assert rows[0]["server"]["speech_chunk_tokens"] == [7]
    assert rows[0]["previous_server_task_id"] == 0
    assert rows[0]["previous_contact"] is None
    assert rows[1]["previous_contact"] == {"run_id": "run", "request_id": "r1"}
    assert report["server_assignment_verified"] is True
    assert report["model_contacts_added"] == report["scorer_contacts_added"] == 0
    assert report["summary"][0]["contacts"] >= 1


def test_log_boundary_and_identical_request_are_separate_observations():
    cs = [contact(1, slot=-1), contact(2, evaluated=11, slot=None)]
    cs[1]["request_body_sha256"] = cs[0]["request_body_sha256"]
    out = audit(cs, log_task(1) + log_task(2, tick=5, evaluated=11))
    assert out["contacts"][0]["successor_kind"] == "log-boundary"
    assert out["contacts"][1]["same_request_body"] is True
    assert out["contacts"][1]["same_sample"] is True


def test_unmatched_external_task_interrupts_same_node_chain():
    out = audit([contact(1), contact(3, evaluated=12)],
                log_task(1) + log_task(2, tick=5, evaluated=99) + log_task(3, tick=9, evaluated=12))
    assert out["contacts"][1]["successor_kind"] == "outside-family"


def test_different_slots_have_independent_histories():
    out = audit([contact(1), contact(2, slot=1, evaluated=11)],
                log_task(1) + log_task(2, slot=1, evaluated=11))
    assert all(r["successor_kind"] == "log-boundary" for r in out["contacts"])


@pytest.mark.parametrize("fault", ["hash", "missing", "ambiguous", "slot", "truncated",
                                    "duplicate-contact", "reused-task", "bad-number",
                                    "missing-metric", "duplicate-start", "slot-change",
                                    "negative", "bad-hash", "overlap", "empty", "bad-log"])
def test_incomplete_or_ambiguous_custody_never_becomes_an_actual_assignment(fault):
    cs, text = [contact(1)], log_task(1)
    if fault == "hash":
        with pytest.raises(SlotHistoryError):
            audit_slot_history(cs, text.encode(), expected_sha256="0" * 64)
        return
    if fault == "missing":
        text = text.replace("prompt eval time", "unavailable time")
    elif fault == "ambiguous":
        text += log_task(2, tick=5)
    elif fault == "slot":
        cs[0]["requested_slot_id"] = 1
    elif fault == "truncated":
        text = log_task(1, truncated=1)
    elif fault == "duplicate-contact":
        cs *= 2
    elif fault == "reused-task":
        cs.append(contact(2))
    elif fault == "bad-number":
        cs[0]["measurements"]["prefill_ms"] = float("nan")
    elif fault == "missing-metric":
        cs[0]["measurements"]["evaluated_input_tokens"] = None
    elif fault == "duplicate-start":
        text += log_task(1, tick=5)
    elif fault == "slot-change":
        text = text.replace("id 0 | task 1 | eval", "id 1 | task 1 | eval")
    elif fault == "negative":
        cs[0]["measurements"]["generated_tokens"] = -1
    elif fault == "bad-hash":
        cs[0]["role_query_sha256"] = "bad"
    elif fault == "overlap":
        cs.append(contact(2, evaluated=11))
        text += log_task(2, tick=2, evaluated=11)
    elif fault == "empty":
        cs = []
    elif fault == "bad-log":
        with pytest.raises(SlotHistoryError):
            audit_slot_history(cs, b"\xff", expected_sha256=hashlib.sha256(b"\xff").hexdigest())
        return
    with pytest.raises(SlotHistoryError):
        audit(cs, text)


def test_rounded_server_times_are_matched_without_inventing_queue_delay():
    row = contact(1, prefill=10.1249, decode=20.3351)
    report = audit([row], log_task(1))
    assert report["contacts"][0]["measurements"]["prefill_ms"] == 10.1249
    assert "queue_ms" not in report["contacts"][0]
    assert "not exclusive GPU" in report["limitations"][0]


def test_pressure_events_are_scoped_and_do_not_leak_raw_log_text():
    text = "outside scope evict raw secret\n" + log_task(1) + "99 I cache size limit private answer\n"
    report = audit([contact(1)], text)
    assert all(not v for v in report["pressure_event_lines"].values())
    text = log_task(1).replace("prompt eval time", "evict private answer\n" +
            "0.2.000.000 I slot update_slots: id 0 | task 1 | prompt eval time")
    report = audit([contact(1)], text)
    assert report["pressure_event_lines"]["evict"]
    assert "private answer" not in str(report)


def numeric_fixture():
    row = contact(1)
    wire = {k: row[k] for k in ("request_id", "sample_id", "role_id", "requested_slot_id",
             "system_message_sha256", "role_query_sha256", "request_body_sha256")}
    return {"run": {"context_execution": {"contacts": [wire]},
                    "node_timing": {"contacts": [{k: row[k] for k in
                        ("request_id", "sample_id", "role_id", "measurements")}]}}}


def test_assembly_preserves_all_contacts_and_joins_original_numeric_sources():
    numeric = numeric_fixture()
    reg = [{"run_id": "run", "layout": "before-speech", "schedule": "panel"}]
    cs = contacts_from_numeric_members(numeric, reg)
    assert cs == [contact(1)]
    assert numeric == numeric_fixture()
    report = audit(cs, log_task(1))
    assert len(report["contacts"]) == 1


@pytest.mark.parametrize("fault", ["family", "duplicate", "missing", "sample", "role", "extra"])
def test_assembly_refuses_partial_or_cross_sample_numeric_join(fault):
    numeric = copy.deepcopy(numeric_fixture())
    reg = [{"run_id": "run", "layout": "before-speech", "schedule": "panel"}]
    row = numeric["run"]
    if fault == "family":
        reg.append({"run_id": "other"})
    elif fault == "duplicate":
        row["node_timing"]["contacts"] *= 2
    elif fault == "missing":
        row["node_timing"]["contacts"] = []
    elif fault == "sample":
        row["node_timing"]["contacts"][0]["sample_id"] = "other"
    elif fault == "role":
        row["node_timing"]["contacts"][0]["role_id"] = "other"
    else:
        row["context_execution"]["contacts"].append({**row["context_execution"]["contacts"][0], "request_id": "extra"})
    with pytest.raises(SlotHistoryError):
        contacts_from_numeric_members(numeric, reg)


def test_independent_owners_may_reuse_local_request_ids():
    first, second = contact(1), contact(2, evaluated=11)
    second.update(run_id="other-owner", request_id=first["request_id"])
    report = audit([first, second], log_task(1) + log_task(2, tick=5, evaluated=11))
    assert len(report["contacts"]) == 2
    assert report["contacts"][1]["previous_contact"] == {"run_id": "run", "request_id": "r1"}
