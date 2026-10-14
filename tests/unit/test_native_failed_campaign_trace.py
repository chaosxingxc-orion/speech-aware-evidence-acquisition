"""Failure-path trace custody for concurrent native OpenJiuwen episodes.

E8c moved the Planner's OWN OUTPUT off this path: a token that names no
registered action is now a row-level disposition, not a flight failure
(tests/unit/test_ojw_native_episode.py, and the campaign-level proof in
tests/unit/test_flight_native_episode_dispatch.py).  The failure this
suite still needs is an EPISODE contract failure: this configuration
allows no revision at all, so a registered REVISE exhausts the episode at
the same graph position, after the same four contacts, and the trace
custody claims below are unchanged.
"""

from __future__ import annotations

from collections import Counter
import threading

import pytest

from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from speech_aware_evidence_acquisition.reproduction.ojw.native_episode import (
    NativeEpisodeError,
)
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness, PHASES


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_completed_and_failing_native_episode_traces_survive_once(tmp_path):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=2,
        max_revisions=0,
        max_contacts=4,
        planner_actions=("ACCEPT",),
        overlap=True,
    )
    completed_id, failing_id = (sample.sample_id for sample in harness.samples)
    completed_planner_returned = threading.Event()
    original_output = harness._output

    def output(key):
        sample_id, phase, _visit, _turn = key
        if sample_id == completed_id and phase == "planner":
            completed_planner_returned.set()
            return "ACCEPT"
        if sample_id == failing_id and phase == "solver":
            assert completed_planner_returned.wait(timeout=5.0)
        if sample_id == failing_id and phase == "planner":
            # A REGISTERED action this configuration cannot honour:
            # max_revisions is 0, so REVISE exhausts the episode.
            return "REVISE"
        return original_output(key)

    harness._output = output
    try:
        with pytest.raises(
            NativeEpisodeError, match="episode revision limit is exhausted"
        ):
            harness.run()
    finally:
        close_summary = harness.close()

    expected_contacts = {
        (sample_id, phase, 1, 1)
        for sample_id in (completed_id, failing_id)
        for phase in PHASES
    }
    assert set(harness.prepared) == expected_contacts
    assert set(harness.dispatched) == expected_contacts
    assert close_summary["request_count"] == len(expected_contacts)

    channel_counts = Counter(channel for channel, _record_id, _payload in harness.trace.records)
    records_by_channel = {
        channel: [
            (record_id, payload)
            for actual_channel, record_id, payload in harness.trace.records
            if actual_channel == channel
        ]
        for channel in ("MODEL_REQUEST", "MODEL_RESPONSE", "MODEL_WIRE_RESPONSE", "COST")
    }
    suffixes = {
        "MODEL_REQUEST": "/request",
        "MODEL_RESPONSE": "/response",
        "MODEL_WIRE_RESPONSE": "/wire-response",
        "COST": "/cost",
    }
    request_ids = {
        record_id.removesuffix("/request")
        for record_id, _payload in records_by_channel["MODEL_REQUEST"]
    }
    for channel, records in records_by_channel.items():
        assert channel_counts[channel] == len(expected_contacts)
        assert len({record_id for record_id, _payload in records}) == len(records)
        assert {
            record_id.removesuffix(suffixes[channel])
            for record_id, _payload in records
        } == request_ids
    request_samples = Counter(
        payload["payload"]["sample_id"]
        for _record_id, payload in records_by_channel["MODEL_REQUEST"]
    )
    assert request_samples == {completed_id: len(PHASES), failing_id: len(PHASES)}

    contact_use = [
        (record_id, payload)
        for channel, record_id, payload in harness.trace.records
        if channel == "USE" and record_id.endswith("/native-role-contact")
    ]
    terminal_use = [
        (record_id, payload)
        for channel, record_id, payload in harness.trace.records
        if channel == "USE" and record_id.endswith("/native-episode")
    ]
    expected_agent_contacts = {
        f"native-role-runner-proof-v1:{phase}:0:{sample_id}"
        for sample_id in (completed_id, failing_id)
        for phase in PHASES
    }
    assert len(contact_use) == len(expected_contacts)
    assert len({record_id for record_id, _payload in contact_use}) == len(contact_use)
    assert {
        payload["use_agent_contact_id"] for _record_id, payload in contact_use
    } == expected_agent_contacts
    assert len(terminal_use) == 1
    assert terminal_use[0][0].startswith(f"{completed_id}/")
    timing = [payload["use_sample_execution_timing"]
              for channel, _, payload in harness.trace.records
              if channel == "USE" and "use_sample_execution_timing" in payload]
    assert len(timing) == 2
    assert {row["sample_id"]: row["status"] for row in timing} == {
        completed_id: "completed", failing_id: "failed",
    }
    assert all(row["batch_started_ns"] <= row["admitted_ns"] <= row["finished_ns"]
               for row in timing)
    # Owner decision 309 (2026-10-14): a row's gold-free runtime records are
    # emitted when ITS episode settles, not after the whole window, so the
    # completed row's `runtime-use` record now survives a failing sibling too.
    # The failing row never settled and has none; the gold-bearing posthoc
    # record is still emitted only after the whole window and so is absent.
    runtime_use = [
        record_id for channel, record_id, _payload in harness.trace.records
        if channel == "USE" and record_id.endswith("/runtime-use")
    ]
    assert len(runtime_use) == 1 and runtime_use[0].startswith(f"{completed_id}/")
    assert not any(record_id.endswith("/posthoc-use")
                   for _channel, record_id, _payload in harness.trace.records)
    assert channel_counts["USE"] == (
        len(contact_use) + len(terminal_use) + len(timing) + len(runtime_use)
    )
