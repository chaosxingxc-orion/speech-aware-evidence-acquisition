"""Synthetic pinned policy artifacts; no model, scorer, or live results."""

from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.finite_action_policy import (
    FinitePolicyError, PolicySnapshot, RoundDescriptor, TerminalFeedback,
    sample_action, update_complete_round,
)
from speech_aware_evidence_acquisition.rails.finite_policy_artifacts import (
    PolicyArtifactError, PolicySchedule, load_policy_schedule, load_policy_snapshot,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash


def sha(value: int) -> str:
    return f"{value:064x}"


def write_pin(root: Path, name: str, document: dict) -> dict:
    path = root / name
    raw = json.dumps(document, ensure_ascii=False, sort_keys=True).encode("utf-8")
    path.write_bytes(raw)
    return {"relpath": name, "sha256": hashlib.sha256(raw).hexdigest()}


def policy() -> PolicySnapshot:
    return PolicySnapshot.create(actions=("a", "b", "c"), states=("s0", "s1"), f0=0.8)


def schedule_doc(snapshot, ids=("x", "y", "z", "w"), *, kind="balanced-without-replacement",
                 mode="construction", epsilon=None, quotas=(2, 1, 1)):
    return {
        "schema": "saea-finite-action-policy-schedule-v1", "round_id": "r1", "mode": mode,
        "snapshot_sha256": snapshot.sha256, "roster_ids": list(ids),
        "roster_identity_sha256": content_hash(list(ids)),
        "split_identity_hash": sha(70), "seed": 23,
        "allocation_kind": kind, "epsilon": epsilon, "initial_quotas": list(quotas),
    }


def test_snapshot_roundtrip_and_nested_tampering_rejected(tmp_path):
    initial = policy()
    decision = sample_action(initial, state_id="s0", epsilon=1, draw=0.9)
    descriptor = RoundDescriptor("r1", ("x",), sha(91), initial.sha256, 1.0)
    row = TerminalFeedback("x", sha(1), (("scores", sha(2)),), decision,
                           decision.action, decision.propensity, 0, 1, 0, 1, True, ())
    updated = update_complete_round(initial, descriptor, (row,))
    document = updated.as_json()
    assert PolicySnapshot.from_json(document) == updated
    pin = write_pin(tmp_path, "snapshot.json", document)
    assert load_policy_snapshot(tmp_path, pin, expected_content_sha256=updated.sha256) == updated
    document["credited"][0]["source_hashes"][0] = ["scores"]
    with pytest.raises(FinitePolicyError):
        PolicySnapshot.from_json(document)
    document = updated.as_json()
    document["credited"][0]["decision"]["propensity"] = 0.3
    with pytest.raises(FinitePolicyError):
        PolicySnapshot.from_json(document)
    document = updated.as_json()
    document["cell_stats"][2]["count"] += 1
    with pytest.raises(FinitePolicyError, match="count/sum"):
        PolicySnapshot.from_json(document)


def test_snapshot_schema_unknown_sparse_and_pin_path_refusals(tmp_path):
    current = policy()
    document = current.as_json()
    for mutation in (lambda d: d.update(extra=1),
                     lambda d: d.pop("f0"),
                     lambda d: d.update(sparse_support=19),
                     lambda d: d.update(sparse_support=20.0)):
        changed = current.as_json()
        mutation(changed)
        with pytest.raises(FinitePolicyError):
            PolicySnapshot.from_json(changed)
    pin = write_pin(tmp_path, "snapshot.json", document)
    with pytest.raises(PolicyArtifactError, match="content hash"):
        load_policy_snapshot(tmp_path, pin, expected_content_sha256=sha(88))
    with pytest.raises(PolicyArtifactError, match="SHA"):
        load_policy_snapshot(tmp_path, {**pin, "sha256": sha(88)})
    for bad in ("../outside.json", "/tmp/outside.json", "sub\\outside.json"):
        with pytest.raises(PolicyArtifactError, match="confined"):
            load_policy_snapshot(tmp_path, {"relpath": bad, "sha256": pin["sha256"]})


def test_balanced_schedule_is_independent_of_runtime_arrival_order(tmp_path):
    current = policy()
    document = schedule_doc(current)
    pin = write_pin(tmp_path, "schedule.json", document)
    expected = ("x", "y", "z", "w")
    bound = load_policy_schedule(tmp_path, pin, snapshot=current,
                                 expected_roster_ids=expected, expected_split_identity_hash=sha(70))
    assert bound.as_json() == document
    assert bound.sha256 == content_hash(document)
    forward = {sid: bound.decision_for(sid, "s0" if index % 2 else "s1", current)
               for index, sid in enumerate(expected)}
    reverse = {sid: bound.decision_for(sid, "s0" if index % 2 else "s1", current)
               for index, sid in reversed(tuple(enumerate(expected)))}
    assert forward == reverse
    assert sorted(index for _decision, index in forward.values()) == list(range(4))
    assert sorted(decision.action for decision, _ in forward.values()) == ["a", "a", "b", "c"]
    assert forward["x"][0].probabilities == (0.5, 0.25, 0.25)
    first_digest = content_hash({"schema": "saea-policy-draw-u52-v1", "seed": 23,
                                 "round_id": "r1", "sample_id": "x"})
    assert forward["x"][0].draw == int(first_digest[:13], 16) / 2 ** 52
    with pytest.raises(FrozenInstanceError):
        bound.seed = 24
    with pytest.raises(PolicyArtifactError, match="snapshot"):
        bound.decision_for("x", "s0", PolicySnapshot.create(actions=("a", "b", "c"), states=("s0", "s1"), f0=0.7))


def test_schedule_refuses_wrong_roster_split_snapshot_and_pins(tmp_path):
    current = policy()
    document = schedule_doc(current)
    pin = write_pin(tmp_path, "schedule.json", document)
    for ids in (("y", "x", "z", "w"), ("x", "y", "z")):
        with pytest.raises(PolicyArtifactError, match="roster"):
            load_policy_schedule(tmp_path, pin, snapshot=current,
                                 expected_roster_ids=ids, expected_split_identity_hash=sha(70))
    with pytest.raises(PolicyArtifactError, match="split"):
        load_policy_schedule(tmp_path, pin, snapshot=current,
                             expected_roster_ids=("x", "y", "z", "w"), expected_split_identity_hash=sha(71))
    with pytest.raises(PolicyArtifactError, match="snapshot"):
        load_policy_schedule(tmp_path, pin, snapshot=PolicySnapshot.create(
            actions=("a", "b", "c"), states=("s0", "s1"), f0=0.7),
            expected_roster_ids=("x", "y", "z", "w"), expected_split_identity_hash=sha(70))
    with pytest.raises(PolicyArtifactError, match="SHA"):
        load_policy_schedule(tmp_path, {**pin, "sha256": sha(99)}, snapshot=current,
                             expected_roster_ids=("x", "y", "z", "w"), expected_split_identity_hash=sha(70))


def test_evaluation_requires_epsilon_zero_and_no_balanced_quota(tmp_path):
    current = policy()
    valid = schedule_doc(current, ids=("x",), kind="epsilon-greedy",
                         mode="evaluation", epsilon=0.0, quotas=())
    schedule = PolicySchedule.from_json(valid).bind(current)
    decision, index = schedule.decision_for("x", "s1", current)
    assert index == 0 and decision.probabilities == (1.0, 0.0, 0.0)
    for change in ({"epsilon": 0.2},
                   {"allocation_kind": "balanced-without-replacement", "epsilon": None,
                    "initial_quotas": [1, 0, 0]}):
        bad = {**valid, **change}
        pin = write_pin(tmp_path, "bad.json", bad)
        with pytest.raises(PolicyArtifactError, match="evaluation|balanced"):
            load_policy_schedule(tmp_path, pin, snapshot=current,
                                 expected_roster_ids=("x",), expected_split_identity_hash=sha(70))


def test_schedule_rejects_unknown_fields_bad_roster_identity_and_unbalanced_quota():
    current = policy()
    document = schedule_doc(current)
    for changed in (
        {**document, "extra": 1},
        {key: value for key, value in document.items() if key != "seed"},
        {**document, "roster_identity_sha256": sha(99)},
        {**document, "initial_quotas": [3, 1, 0]},
    ):
        with pytest.raises(FinitePolicyError):
            PolicySchedule.from_json(changed)
