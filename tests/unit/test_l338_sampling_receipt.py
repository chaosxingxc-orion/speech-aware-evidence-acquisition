"""Decision 338: the v6 receipt against its own trace -- the bundle verifier and the resume replay.

A sampling episode is flown through the real graph on the fake transport (``test_l338_sampling_live``), its trace is lifted into
the mapping the bundle verifier reads, and the verifier and the replay are then held to it, positively and by tampering.
"""

from __future__ import annotations

import copy
import hashlib

import pytest

from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.bundle.outputs import _verify_perception_branch_trace_binding
from speech_aware_evidence_acquisition.rails.supply_variants import (
    PerceptionBranchError,
    PerceptionBranchReplayContact,
    replay_perception_branch_block,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_l338_sampling_live import _output, _run
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401


@pytest.fixture
def flown(tmp_path):
    if not openjiuwen_available():
        pytest.skip("OpenJiuwen unavailable")
    group, harness, summary = _run(tmp_path)
    trace = {record_id: payload for _channel, record_id, payload in harness.trace.records}
    return group, summary, trace


def _row(result):
    return {"sample_id": result.sample_id, "native_episode_receipt": copy.deepcopy(result.native_episode_receipt)}


def test_the_verifier_accepts_a_flown_v6_row(flown):
    _group, summary, trace = flown
    for result in summary.results:
        _verify_perception_branch_trace_binding(_row(result), trace)


def _refuses(row, trace, fragment):
    with pytest.raises(BundleError) as caught:
        _verify_perception_branch_trace_binding(row, trace)
    assert fragment in str(caught.value), str(caught.value)


def test_a_tampered_merge_is_refused(flown):
    _group, summary, trace = flown
    row = _row(summary.results[0])
    rows = {r["branch_id"]: r for r in row["native_episode_receipt"]["perception_branches"]["branches"]}
    record = rows["l2"]["sampling"]["perception_samples"]
    record["merged_candidate_ids"] = ["i:a", "i:b"]
    record["appended_candidate_ids"] = []
    _refuses(row, trace, "merge differently")


def test_a_tampered_commit_is_refused(flown):
    _group, summary, trace = flown
    row = _row(summary.results[0])
    rows = {r["branch_id"]: r for r in row["native_episode_receipt"]["perception_branches"]["branches"]}
    rows["l1"]["sampling"]["solver_samples"]["outcome"]["entity_supports"] = [{"type": "place_name", "support": 3}]
    _refuses(row, trace, "commit differently")


def test_a_wrong_recorded_seed_is_refused(flown):
    _group, summary, trace = flown
    row = _row(summary.results[0])
    rows = {r["branch_id"]: r for r in row["native_episode_receipt"]["perception_branches"]["branches"]}
    sample = rows["l2"]["sampling"]["perception_samples"]["samples"][1]
    sample["seed"] += 1
    record = rows["l2"]["sampling"]["perception_samples"]
    record["seeds"][1] += 1
    record["seed_offsets"][0] += 1
    _refuses(row, trace, "seed")


def test_a_swapped_sample_contact_is_refused(flown):
    _group, summary, trace = flown
    row = _row(summary.results[0])
    rows = {r["branch_id"]: r for r in row["native_episode_receipt"]["perception_branches"]["branches"]}
    samples = rows["l2"]["sampling"]["perception_samples"]["samples"]
    samples[0]["contact_id"], samples[1]["contact_id"] = samples[1]["contact_id"], samples[0]["contact_id"]
    _refuses(row, trace, "contact")


def _replay_contacts(summary, trace):
    contacts = {}
    for result in summary.results:
        for visit in result.native_episode_receipt["role_visits"]:
            for contact in visit["execution_receipt"]["contacts"]:
                response = trace[f"{contact['request_id']}/response"]
                contacts[contact["agent_contact_id"]] = PerceptionBranchReplayContact(
                    request_sha256=contact["request_sha256"],
                    response_text_sha256=contact["response_text_sha256"],
                    text=response["text"],
                )
    return contacts


def test_the_resume_replay_keeps_the_v6_schema_and_rederives_the_samples(flown):
    _group, summary, trace = flown
    contacts = _replay_contacts(summary, trace)
    block = summary.results[0].native_episode_receipt["perception_branches"]
    rebuilt = replay_perception_branch_block(block, contacts=contacts)
    assert rebuilt["schema"] == block["schema"] == "saea-perception-branch-arms-v6"
    assert rebuilt["branches"] == block["branches"]


def test_the_resume_replay_refuses_a_sample_whose_text_changed(flown):
    _group, summary, trace = flown
    contacts = _replay_contacts(summary, trace)
    block = copy.deepcopy(summary.results[0].native_episode_receipt["perception_branches"])
    rows = {r["branch_id"]: r for r in block["branches"]}
    victim = rows["l2"]["sampling"]["perception_samples"]["samples"][1]["contact_id"]
    changed = PerceptionBranchReplayContact(
        request_sha256=contacts[victim].request_sha256, response_text_sha256=contacts[victim].response_text_sha256,
        text=_output(("x", "perception", 1, 1)),
    )
    contacts[victim] = changed
    with pytest.raises(PerceptionBranchError):
        replay_perception_branch_block(block, contacts=contacts)
    assert hashlib.sha256(changed.text.encode()).hexdigest() != contacts[victim].response_text_sha256
