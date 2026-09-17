"""E2 (SLURP v2 base program M2): the grouped-Solver orchestrator.

Fakes the N per-sample role invocations (a live episode would bind these to
``reproduction.ojw.native_roles.NativeRoleNode.invoke_direct`` through a
``MeteredNativeSpeechRequest`` carrying ``solver_role_id``/
``solver_sampling`` -- proved separately in
``test_native_request_grouped_solver.py``) and proves: N contacts land in
the merged ``execution_receipt``, all N raw responses stay in custody under
``solver_group``, and the delivered ``actor_output`` equals the registered
commit policy's own output on the same votes.

This repository tests async framework code with plain ``asyncio.run`` inside
ordinary (sync) test functions (see ``tests/unit/test_ojw_native_roles.py``)
rather than a pytest-asyncio plugin; this module follows the same pattern.
"""

from __future__ import annotations

import asyncio
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.rails.commit_policies import (
    ParsedSlurpAnswer,
    SolverSampleVote,
    commit_plurality_support_v1,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    validate_solver_group_receipt,
)
from speech_aware_evidence_acquisition.reproduction.ojw.native_group_solver import (
    GroupedSolverError,
    run_grouped_solver_samples,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

FRAGMENT_SEED = 2000
DECODING_OVERRIDES = {"temperature": 0.7, "seed_offset": 3}
COMMIT = {
    "policy": "saea-commit-plurality-support-v1",
    "min_support": 2,
    "similarity_threshold": 0.8,
}

ANSWERS = [
    {"scenario": "alarm", "action": "set", "entities": [{"type": "time", "filler": "six am"}]},
    {"scenario": "alarm", "action": "set", "entities": [{"type": "time", "filler": "six a m"}]},
    {"scenario": "alarm", "action": "cancel", "entities": []},
]


def _text(answer):
    return json.dumps(answer, ensure_ascii=False, sort_keys=True)


def _contact(sample_index, text):
    return {
        "agent_contact_id": f"contact-{sample_index}",
        "request_id": f"req-{sample_index}",
        "request_sha256": "a" * 64,
        "response_sha256": "b" * 64,
        "response_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


def _role_result(sample_index, *, text, role_id="solver", eligible=True):
    contact = _contact(sample_index, text)
    return {
        "role_id": role_id,
        "actor_output": text,
        "result_type": "answer",
        "delivery_eligible": eligible,
        "execution_receipt": {"contacts": [contact], "final_contact": contact},
    }


def _invoke_factory(texts, *, role_id="solver"):
    async def invoke_sample(sample_index):
        return _role_result(sample_index, text=texts[sample_index], role_id=role_id)

    return invoke_sample


def _run(coro):
    return asyncio.run(coro)


def test_three_samples_produce_three_contacts_and_full_custody():
    texts = [_text(answer) for answer in ANSWERS]
    result = _run(run_grouped_solver_samples(
        _invoke_factory(texts),
        samples=3,
        fragment_seed=FRAGMENT_SEED,
        decoding_overrides=DECODING_OVERRIDES,
        commit=COMMIT,
    ))
    contacts = result["execution_receipt"]["contacts"]
    assert len(contacts) == 3
    assert contacts == [_contact(i, texts[i]) for i in range(3)]
    assert result["execution_receipt"]["final_contact"] == contacts[-1]

    votes = [
        SolverSampleVote(sample_index=0, parsed=ParsedSlurpAnswer(
            scenario="alarm", action="set", entities=(SlotEntity(type="time", filler="six am"),),
        )),
        SolverSampleVote(sample_index=1, parsed=ParsedSlurpAnswer(
            scenario="alarm", action="set", entities=(SlotEntity(type="time", filler="six a m"),),
        )),
        SolverSampleVote(sample_index=2, parsed=ParsedSlurpAnswer(
            scenario="alarm", action="cancel", entities=(),
        )),
    ]
    expected = commit_plurality_support_v1(votes, min_support=2, similarity_threshold=0.8)
    expected_text = json.dumps(
        {
            "scenario": expected.answer.scenario,
            "action": expected.answer.action,
            "entities": [{"type": e.type, "filler": e.filler} for e in expected.answer.entities],
        },
        ensure_ascii=False, sort_keys=True,
    )
    assert result["actor_output"] == expected_text
    assert result["result_type"] == "answer"
    assert result["delivery_eligible"] is True

    solver_group = result["solver_group"]
    validate_solver_group_receipt(solver_group, samples=3)
    assert solver_group["commit_policy_id"] == "saea-commit-plurality-support-v1"
    seeds = [record["seed"] for record in solver_group["samples"]]
    assert seeds == [FRAGMENT_SEED + DECODING_OVERRIDES["seed_offset"] + i for i in range(3)]
    assert {record["temperature"] for record in solver_group["samples"]} == {0.7}
    assert [record["parse_status"] for record in solver_group["samples"]] == ["ok", "ok", "ok"]
    assert solver_group["delivered"]["intent_support"] == 2
    assert solver_group["delivered"]["intent_member_sample_indices"] == [0, 1]


def test_a_malformed_sample_is_recorded_but_casts_no_vote():
    texts = [_text(ANSWERS[0]), "not-json-at-all", _text(ANSWERS[0])]
    result = _run(run_grouped_solver_samples(
        _invoke_factory(texts),
        samples=3,
        fragment_seed=FRAGMENT_SEED,
        decoding_overrides=DECODING_OVERRIDES,
        commit=COMMIT,
    ))
    solver_group = result["solver_group"]
    validate_solver_group_receipt(solver_group, samples=3)
    assert solver_group["samples"][1]["parse_status"] == "malformed"
    assert solver_group["samples"][1]["parsed_answer"] is None
    assert solver_group["delivered"]["intent_support"] == 2
    assert solver_group["delivered"]["intent_member_sample_indices"] == [0, 2]
    # The malformed sample still keeps its raw contact in custody.
    assert len(result["execution_receipt"]["contacts"]) == 3


def test_samples_one_is_trivially_the_single_sample():
    texts = [_text(ANSWERS[0])]
    result = _run(run_grouped_solver_samples(
        _invoke_factory(texts),
        samples=1,
        fragment_seed=FRAGMENT_SEED,
        decoding_overrides=DECODING_OVERRIDES,
        commit={"policy": "saea-commit-plurality-support-v1", "min_support": 1, "similarity_threshold": 0.8},
    ))
    assert result["actor_output"] == texts[0]
    assert len(result["execution_receipt"]["contacts"]) == 1
    assert result["execution_receipt"]["contacts"] == [result["execution_receipt"]["final_contact"]]
    validate_solver_group_receipt(result["solver_group"], samples=1)


def test_every_sample_must_share_one_role_id():
    async def invoke_sample(sample_index):
        role_id = "solver" if sample_index == 0 else "reviewer"
        return _role_result(sample_index, text=_text(ANSWERS[0]), role_id=role_id)

    with pytest.raises(GroupedSolverError, match="one role_id"):
        _run(run_grouped_solver_samples(
            invoke_sample, samples=2, fragment_seed=FRAGMENT_SEED,
            decoding_overrides=DECODING_OVERRIDES, commit=COMMIT,
        ))


def test_a_sample_without_an_execution_receipt_is_refused():
    async def invoke_sample(sample_index):
        return {
            "role_id": "solver", "actor_output": _text(ANSWERS[0]),
            "result_type": "answer", "delivery_eligible": True,
        }

    with pytest.raises(GroupedSolverError, match="execution receipt"):
        _run(run_grouped_solver_samples(
            invoke_sample, samples=1, fragment_seed=FRAGMENT_SEED,
            decoding_overrides=DECODING_OVERRIDES, commit=COMMIT,
        ))


def test_unknown_commit_policy_is_refused():
    async def invoke_sample(sample_index):
        return _role_result(sample_index, text=_text(ANSWERS[0]))

    with pytest.raises(GroupedSolverError):
        _run(run_grouped_solver_samples(
            invoke_sample, samples=1, fragment_seed=FRAGMENT_SEED,
            decoding_overrides=DECODING_OVERRIDES,
            commit={"policy": "not-a-real-policy", "min_support": 1, "similarity_threshold": 0.8},
        ))


@pytest.mark.parametrize("bad_samples", [0, -1, 9, True, "3"])
def test_samples_must_be_a_bounded_integer(bad_samples):
    async def invoke_sample(sample_index):
        return _role_result(sample_index, text=_text(ANSWERS[0]))

    with pytest.raises(GroupedSolverError, match="samples"):
        _run(run_grouped_solver_samples(
            invoke_sample, samples=bad_samples, fragment_seed=FRAGMENT_SEED,
            decoding_overrides=DECODING_OVERRIDES, commit=COMMIT,
        ))
