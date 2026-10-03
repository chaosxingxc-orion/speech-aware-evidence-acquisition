"""Reject hidden panel waits, crossed barriers and incomplete source coverage."""
import copy
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis.node_panel_timing import audit_member_node_timing, combine_node_panel_timings


def world(group):
    records, contacts, keys = {}, [], []
    for local in range(2):
        sid = f"sample-{local}"
        keys.append([sid, None])
        sample = {"schema": "saea-sample-execution-timing-v1", "sample_id": sid,
                  "execution_unit_id": None, "panel_id": "panel", "panel_expected_samples": 4,
                  "panel_admission_index": group * 2 + local, "admission_index": local,
                  "expected_samples": 2, "slot_count": 4, "status": "completed", "error_type": None,
                  "batch_started_ns": 0, "panel_execution_started_ns": 1,
                  "admitted_ns": 1, "finished_ns": 20}
        records[f"{sid}/timing"] = {"use_sample_execution_timing": sample}
        for node_index, node in enumerate(("perception", "solver")):
            start = (3 if group == 0 else 5) if node_index == 0 else 10
            for kind in ("prepare", "model"):
                # Group0 prefetch overlaps group1 perception. All solver calls wait.
                begin = (2 if node_index == 0 else (5 if group == 0 else 7)) if kind == "prepare" else start
                end = begin + 1
                event = {"schema": "saea-node-pipeline-timing-v1", "panel_id": "panel", "sample_id": sid,
                         "execution_unit_id": None, "kind": kind, "group_index": group,
                         "round_index": 0, "node_index": node_index, "node_id": node,
                         "slot_id": None if kind == "prepare" else group * 2 + local,
                         "queued_ns": begin, "started_ns": begin, "finished_ns": end,
                         "status": "completed", "error_type": None,
                         "process_memory": {"rss_bytes": 100, "peak_rss_bytes": 120}}
                records[f"{sid}/{node}/{kind}"] = {"use_node_pipeline_timing": event}
            contacts.append({"request_id": f"{sid}-{node}", "sample_id": sid, "role_id": node,
                             "requested_slot_id": group * 2 + local})
    cfg = {"native_node_pipeline": {"schema": "saea-native-node-pipeline-v1", "node_order": ["perception", "solver"],
                                   "group_size": 2, "max_jobs": 4, "prepare_workers": 2}}
    source = SimpleNamespace(sample_ids=[x[0] for x in keys], composed=SimpleNamespace(values=cfg),
                             bundle=SimpleNamespace(trace_records=records))
    spec = {"panel_id": "panel", "group_index": group, "group_size": 2, "max_jobs": 4, "job_keys": keys}
    return source, contacts, spec


def member(group):
    source, contacts, spec = world(group)
    return audit_member_node_timing(source, contacts, **spec)


def test_join_keeps_original_waits_all_owner_jobs_and_prefetch():
    report = combine_node_panel_timings([member(0), member(1)])
    assert report["jobs"] == 4 and report["model_contacts"] == 8
    assert report["barriers_verified"] is True
    assert report["prefetch_overlap_events"] == 2
    assert report["submission_to_terminal_mean_seconds"] == 20 / 1e9
    assert report["admission_to_terminal_mean_seconds"] == 19 / 1e9
    assert len(report["stages"]) == 2


@pytest.mark.parametrize("fault", ["missing-sample", "wrong-owner", "changed-origin", "missing-model", "extra-model", "slot", "role", "negative-time", "failed", "future-sample", "config", "job-order"])
def test_member_custody_refuses_incomplete_or_wrong_owner_records(fault):
    source, contacts, spec = world(0)
    records = source.bundle.trace_records
    event = records["sample-0/solver/model"]["use_node_pipeline_timing"]
    if fault == "missing-sample":
        records.pop("sample-1/timing")
    elif fault == "wrong-owner":
        event["group_index"] = 1
    elif fault == "changed-origin":
        records["sample-0/timing"]["use_sample_execution_timing"]["batch_started_ns"] = 1
    elif fault == "missing-model":
        records.pop("sample-0/solver/model")
    elif fault == "extra-model":
        records["extra"] = copy.deepcopy(records["sample-0/solver/model"])
    elif fault == "slot":
        event["slot_id"] = 3
    elif fault == "role":
        event["node_id"] = "planner"
    elif fault == "negative-time":
        event["queued_ns"] = -1
    elif fault == "failed":
        event["status"] = "failed"
    elif fault == "future-sample":
        event["sample_id"] = "future"
    elif fault == "config":
        source.composed.values["native_node_pipeline"]["max_jobs"] = 20
    else:
        spec["job_keys"].reverse()
    with pytest.raises(ValueError):
        audit_member_node_timing(source, contacts, **spec)


@pytest.mark.parametrize("fault", ["missing-owner", "duplicate-owner", "cross-stage", "unprepared", "early-prefetch", "overlapping-slot", "mixed-panel", "mixed-origin"])
def test_whole_panel_refuses_weak_or_crossed_barrier_evidence(fault):
    rows = [member(0), member(1)]
    if fault == "missing-owner":
        rows.pop()
    elif fault == "duplicate-owner":
        rows[1] = copy.deepcopy(rows[0])
    elif fault == "mixed-panel":
        rows[1]["panel_id"] = "other"
    elif fault == "mixed-origin":
        rows[1]["samples"][0]["batch_started_ns"] = 2
    else:
        events = rows[0]["events"]
        if fault == "cross-stage":
            e = next(e for e in events if e["node_id"] == "solver" and e["kind"] == "model")
            e.update(queued_ns=5, started_ns=5, finished_ns=6)
        elif fault == "unprepared":
            e = next(e for e in events if e["node_id"] == "solver" and e["kind"] == "prepare")
            e["finished_ns"] = 12
        elif fault == "early-prefetch":
            e = next(e for e in events if e["node_id"] == "solver" and e["kind"] == "prepare")
            e.update(queued_ns=2, started_ns=2, finished_ns=3)
        else:
            es = [e for e in events if e["node_id"] == "perception" and e["kind"] == "model"]
            es[1]["slot_id"] = es[0]["slot_id"]
    with pytest.raises(ValueError):
        combine_node_panel_timings(rows)
