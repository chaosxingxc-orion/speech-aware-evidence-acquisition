"""LIVE (fake-transport, real graph) proof of the decision-338 sampling fan-out.

Structurally ``test_perception_branch_level2_render.py``'s twin: the SAME ``_ActualEpisodeHarness`` fake llama-server-shaped
transport drives the REAL ``rails.runner._invoke_native_role_episode`` graph over a ``roles.perception.sampling_variants``
group. No model, server, GPU or network contact: every response is composed by this file's own ``_output`` callback.

Group: ``l1`` (solver_samples n=3), ``l2`` (perception_samples k=2, cap 3), ``aa`` (twin), ``lock`` (delivering).
Per row: Perception 1 + 2 + 1 + 1 = 5 contacts, Solver 3 + 1 + 1 + 1 = 6 contacts.
"""

from __future__ import annotations

import json
from collections import defaultdict

import pytest

from speech_aware_evidence_acquisition.rails.native_episode_config import NativeEpisodeConfig, NativeEpisodeRole
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    PERCEPTION_BRANCH_RECEIPT_SCHEMA_V6,
    validate_perception_branch_receipt,
)
from speech_aware_evidence_acquisition.rails.supply_variants import parse_perception_sampling_variants
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import ACTIONS, PHASES, _ActualEpisodeHarness

ROWS = 2
LOCK_SEED = 777
FIT = {"slot_tokens": 24576, "completion_ceiling": 640, "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120}
DECODING = {"temperature": 0.6, "top_p": 0.95, "top_k": 20}
BLOCK = {
    "node": "perception", "max_supplied_items": 4, "fit_estimate": dict(FIT),
    "arms": [
        {"arm_id": "l1", "solver_samples": {
            "n": 3, "decoding": DECODING,
            "commit": {
                "policy": "saea-commit-first-support-v1", "min_support": 2, "similarity_threshold": 0.8,
                "n1_min": 0.2, "empty_votes_min": 2,
            },
        }},
        {"arm_id": "l2", "perception_samples": {
            "k": 2, "decoding": DECODING, "merge_policy": "saea-perception-candidate-union-v1", "cap": 3,
        }},
        {"arm_id": "aa", "replicate_of": "lock"},
        {"arm_id": "lock", "deliver": True},
    ],
}


def _note(*ids):
    return json.dumps({"candidates": [{"intent_id": value} for value in ids]}, sort_keys=True)


def _answer(*fillers):
    return json.dumps(
        {"scenario": "s", "action": "a", "entities": [{"type": "place_name", "filler": f} for f in fillers]},
        sort_keys=True,
    )


def _output(key):
    sample_id, phase, visit, turn = key
    if phase == "perception":
        # Turns: l1, l2 sample 0, l2 sample 1, aa, lock.
        return {1: _note("i:a", "i:b"), 2: _note("i:a", "i:b"), 3: _note("i:c", "i:a")}.get(turn, _note("i:a", "i:b"))
    if phase == "solver":
        # Turns 1-3 are l1's samples: two carry the entity, one is empty. Turns 4-6: l2, aa, lock.
        return {1: _answer("paris"), 2: _answer("paris"), 3: _answer()}.get(turn, _answer("paris"))
    return f"{phase}-analysis:{sample_id}:visit:{visit}"


def _config(group):
    return NativeEpisodeConfig(
        episode_id="native-role-runner-sampling-proof-v1", max_revisions=0, actions=ACTIONS,
        roles=tuple(
            NativeEpisodeRole(
                phase_id=phase, role_kind=phase, max_iterations=0 if phase in {"reviewer", "planner"} else 1,
                tool_names=(), perception_branches=(group if phase == "perception" else None),
            )
            for phase in PHASES
        ),
        max_contacts=11,
    )


def _run(tmp_path, *, output=_output):
    group = parse_perception_sampling_variants(BLOCK, phase_id="perception")
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=ROWS, max_revisions=0, max_contacts=11, planner_actions=(),
    )
    harness.config = _config(group)
    harness._output = output
    try:
        summary = harness.run(decoding_params={"temperature": 0, "max_tokens": 64, "seed": LOCK_SEED})
    finally:
        harness.close()
    return group, harness, summary


def _requests(harness):
    by_row = defaultdict(list)
    for channel, _record_id, payload in harness.trace.records:
        if channel == "MODEL_REQUEST":
            by_row[payload["payload"]["sample_id"]].append(payload["payload"])
    return by_row


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_sampling_visit_spends_one_contact_per_slot_and_seals_a_valid_v6_receipt(tmp_path):
    group, harness, summary = _run(tmp_path)
    assert len(summary.results) == ROWS
    for result in summary.results:
        assert len(result.contacts) == 11
        receipt = result.native_episode_receipt["perception_branches"]
        assert receipt["schema"] == PERCEPTION_BRANCH_RECEIPT_SCHEMA_V6
        assert receipt["level"] == 2 and receipt["delivered_branch_id"] == "lock"
        validate_perception_branch_receipt(
            receipt, branch_ids=group.branch_ids, delivered_branch_id="lock", twin_branch_id="aa",
            phase_id="perception", level=2,
        )
        rows = {row["branch_id"]: row for row in receipt["branches"]}
        assert rows["aa"]["sampling"] is None and rows["lock"]["sampling"] is None
        l2 = rows["l2"]["sampling"]["perception_samples"]
        assert rows["l2"]["sampling"]["solver_samples"] is None
        assert l2["seeds"] == [LOCK_SEED, LOCK_SEED + 1]
        assert l2["merged_candidate_ids"] == ["i:a", "i:b", "i:c"] and l2["appended_candidate_ids"] == ["i:c"]
        assert [s["sample_index"] for s in l2["samples"]] == [0, 1]
        assert rows["l2"]["contact_id"] == l2["samples"][0]["contact_id"]
        l1 = rows["l1"]["sampling"]["solver_samples"]
        assert rows["l1"]["sampling"]["perception_samples"] is None
        assert l1["seeds"] == [LOCK_SEED + o for o in (0, 1, 2)]
        assert [s["parse_status"] for s in l1["samples"]] == ["ok", "ok", "ok"]
        assert l1["outcome"]["entity_supports"] == [{"type": "place_name", "support": 2}]
        assert l1["outcome"]["delivered_entity_count"] == 1
        # The gate is configured but the run supplies no N1.
        assert l1["outcome"]["gate"]["status"] == "n1-unavailable"
        assert rows["l1"]["solver_contact_id"] == l1["samples"][0]["contact_id"]
        assert len({s["contact_id"] for s in l1["samples"]}) == 3
        # Downstream custody is the delivering branch's alone: one sealed Perception state, the lock's own note.
        perception_states = [s for s in result.agent_states if s.state_kind == "phase:perception"]
        assert [s.content for s in perception_states] == [_note("i:a", "i:b")]


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_every_sample_request_carries_its_seed_and_sampling_and_sample_zero_is_the_locks_request(tmp_path):
    _group, harness, summary = _run(tmp_path)
    by_row = _requests(harness)
    for result in summary.results:
        requests = by_row[result.sample_id]
        assert len(requests) == 11
        perception, solver = requests[:5], requests[5:]
        # Perception contacts: l1, l2 s0, l2 s1, aa, lock.
        decodings = [r["decoding_params"] for r in perception]
        assert [d["seed"] for d in decodings] == [LOCK_SEED, LOCK_SEED, LOCK_SEED + 1, LOCK_SEED, LOCK_SEED]
        assert decodings[2]["temperature"] == 0.6 and decodings[2]["top_p"] == 0.95 and decodings[2]["top_k"] == 20
        for index in (0, 1, 3, 4):
            assert decodings[index]["temperature"] == 0 and "top_p" not in decodings[index]
        # Solver contacts: l1 s0..s2, l2, aa, lock.
        solver_decodings = [r["decoding_params"] for r in solver]
        assert [d["seed"] for d in solver_decodings] == [
            LOCK_SEED, LOCK_SEED + 1, LOCK_SEED + 2, LOCK_SEED, LOCK_SEED, LOCK_SEED,
        ]
        assert solver_decodings[1]["temperature"] == 0.6 and solver_decodings[2]["top_k"] == 20
        for index in (0, 3, 4, 5):
            assert solver_decodings[index]["temperature"] == 0 and "top_p" not in solver_decodings[index]


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_union_branch_solver_reads_the_merged_note_and_the_others_read_their_own(tmp_path):
    _group, harness, summary = _run(tmp_path)
    by_row = _requests(harness)

    def history(request):
        return json.dumps(
            [h.get("content") for h in request["history"] if "state_kind" in h], sort_keys=True,
        )

    for result in summary.results:
        solver = by_row[result.sample_id][5:]
        # l2's Solver (index 3) sees the merged list including i:c; the lock's Solver (index 5) does not.
        assert "i:c" in history(solver[3])
        assert "i:c" not in history(solver[5])
        # l1's samples render one identical request body apart from the sampling fields.
        assert history(solver[0]) == history(solver[1]) == history(solver[2])
