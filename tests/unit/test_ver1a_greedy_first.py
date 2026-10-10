"""VER-1a (2026-10-10): the ``decoding_overrides.greedy_first`` option of the grouped Solver.

VER-1a seals a five-sample pool (amended from three before any contact) whose FIRST sample is the greedy delivery the lock already makes
(the fragment's own temperature 0) and whose four continuations are drawn at temperature 0.7. Until this option, a grouped Solver visit applied ONE registered
temperature to every sample, so no config could ask for "sample 0 greedy, samples 1.. sampled". The option is the literal ``true``
beside ``temperature`` and ``seed_offset``; absent it every sample takes the registered temperature, byte for byte as before.

Three layers are proved here. (1) The pure pieces: the request composer, the grouped-sample runner's custody record and the role
validator. (2) The production walk: a four-row review-off grouped episode driven through the real graph, request renderer,
state sealer and trace sink, with the wire decoding of every Solver contact captured at the request gate. (3) The SEAL PATH
(the 2026-10-09 E1 lesson): the same rows handed to ``FlightRuntime._canonical_output_rows``, the function the worker's seal calls,
with the RAW declared native block the cell's fragment carries, then the bundle's own outputs/trace binding check.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.bundle.outputs import _verify_outputs_trace_binding
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    NativeEpisodeConfig,
    NativeEpisodeRole,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import validate_solver_group_receipt
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from speech_aware_evidence_acquisition.reproduction.ojw.native_group_solver import (
    GroupedSolverError,
    run_grouped_solver_samples,
)
from speech_aware_evidence_acquisition.reproduction.ojw.native_request import (
    NativeSpeechRequestError,
    compose_solver_sample_decoding_params,
)

import test_native_episode_runner as runner_tests
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import ACTIONS, PHASES, _ActualEpisodeHarness

BASE = {"temperature": 0, "seed": 20260913, "max_tokens": 512, "id_slot": "per-sample"}
OVERRIDES = {"temperature": 0.7, "seed_offset": 0, "greedy_first": True}
COMMIT = {"policy": "saea-commit-plurality-support-v1", "min_support": 3, "similarity_threshold": 0.8}
ANSWERS = [
    {"scenario": "alarm", "action": "set", "entities": [{"type": "time", "filler": "six am"}]},
    {"scenario": "alarm", "action": "set", "entities": [{"type": "time", "filler": "six a m"}]},
    {"scenario": "alarm", "action": "cancel", "entities": []},
    {"scenario": "alarm", "action": "set", "entities": [{"type": "time", "filler": "six o'clock"}]},
    {"scenario": "alarm", "action": "cancel", "entities": []},
]


# --- (1) the pure pieces ---------------------------------------------------------------------------------------------


def test_the_composer_keeps_sample_zero_greedy_and_samples_the_rest():
    composed = [
        compose_solver_sample_decoding_params(BASE, fragment_seed=1000, decoding_overrides=OVERRIDES, sample_index=i)
        for i in range(5)
    ]
    assert [c["temperature"] for c in composed] == [0] + [0.7] * 4
    assert [c["seed"] for c in composed] == [1000, 1001, 1002, 1003, 1004]
    # sample 0 is the fragment's own block except the pinned seed (a temperature-0 request does not consume it)
    assert {k: v for k, v in composed[0].items() if k != "seed"} == {k: v for k, v in BASE.items() if k != "seed"}
    assert type(composed[0]["temperature"]) is int  # the base block's own literal, so the wire bytes match the single-sample request


def test_without_greedy_first_every_sample_takes_the_registered_temperature():
    plain = {"temperature": 0.7, "seed_offset": 0}
    composed = [
        compose_solver_sample_decoding_params(BASE, fragment_seed=1000, decoding_overrides=plain, sample_index=i)
        for i in range(5)
    ]
    assert [c["temperature"] for c in composed] == [0.7] * 5


@pytest.mark.parametrize("bad", [
    {"temperature": 0.7, "seed_offset": 0, "greedy_first": False},
    {"temperature": 0.7, "seed_offset": 0, "greedy_first": 1},
    {"temperature": 0.7, "seed_offset": 0, "greedy_first": True, "extra": 1},
    {"seed_offset": 0, "greedy_first": True},
    {"temperature": 0.7, "seed_offset": 0, "extra": 1},
])
def test_the_composer_refuses_a_malformed_greedy_first_block(bad):
    with pytest.raises(NativeSpeechRequestError):
        compose_solver_sample_decoding_params(BASE, fragment_seed=1, decoding_overrides=bad, sample_index=0)


def _hash_contact(text, i):
    import hashlib

    contact = {
        "agent_contact_id": f"c{i}", "request_id": f"r{i}", "request_sha256": "a" * 64, "response_sha256": "b" * 64,
        "response_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }
    return {"role_id": "solver", "actor_output": text, "result_type": "answer", "delivery_eligible": True,
            "execution_receipt": {"contacts": [contact], "final_contact": contact}}


def test_the_group_runner_custodies_sample_zero_at_temperature_zero():
    import asyncio

    texts = [json.dumps(a, sort_keys=True) for a in ANSWERS]

    async def invoke(i):
        return _hash_contact(texts[i], i)

    result = asyncio.run(run_grouped_solver_samples(
        invoke, samples=5, fragment_seed=1000, decoding_overrides=OVERRIDES, commit=COMMIT,
    ))
    group = result["solver_group"]
    validate_solver_group_receipt(group, samples=5)
    assert [r["temperature"] for r in group["samples"]] == [0, 0.7, 0.7, 0.7, 0.7]
    assert [r["seed"] for r in group["samples"]] == [1000, 1001, 1002, 1003, 1004]
    # 3 x set vs 2 x cancel: the plurality intent is "set" with support 3 (= min_support 3)
    assert group["delivered"]["intent_support"] == 3


def test_the_group_runner_refuses_a_non_true_greedy_first():
    import asyncio

    async def invoke(i):
        return _hash_contact("{}", i)

    with pytest.raises(GroupedSolverError):
        asyncio.run(run_grouped_solver_samples(
            invoke, samples=2, fragment_seed=1, commit=COMMIT,
            decoding_overrides={"temperature": 0.7, "seed_offset": 0, "greedy_first": False},
        ))


def test_the_role_validator_admits_greedy_first_and_refuses_the_twin_combination():
    role = NativeEpisodeRole("solver", "solver", 1, (), samples=5, decoding_overrides=OVERRIDES, commit=COMMIT)
    assert role.decoding_overrides["greedy_first"] is True
    with pytest.raises(ValueError, match="greedy_first"):
        NativeEpisodeRole("solver", "solver", 1, (), samples=5,
                          decoding_overrides={**OVERRIDES, "greedy_first": False}, commit=COMMIT)
    with pytest.raises(ValueError, match="twin"):
        NativeEpisodeRole("solver", "solver", 1, (), samples=5, decoding_overrides={**OVERRIDES, "temperature": 0},
                          commit=COMMIT, twin="greedy-repeat")
    with pytest.raises(ValueError, match="exactly"):
        NativeEpisodeRole("solver", "solver", 1, (), samples=5,
                          decoding_overrides={**OVERRIDES, "other": 1}, commit=COMMIT)
    with pytest.raises(ValueError, match="requires samples"):
        NativeEpisodeRole("solver", "solver", 1, (), samples=1, decoding_overrides=OVERRIDES)


# --- (2) + (3) the production walk and the seal path ------------------------------------------------------------------

pytest.importorskip("openjiuwen", reason="OpenJiuwen unavailable")


def _review_off_grouped_config():
    return NativeEpisodeConfig(
        episode_id="native-role-runner-proof-v1", max_revisions=0, actions=ACTIONS,
        roles=tuple(
            NativeEpisodeRole(
                phase_id=phase, role_kind=phase, max_iterations=0 if phase in {"reviewer", "planner"} else 1,
                tool_names=(), samples=5 if phase == "solver" else 1,
                decoding_overrides=OVERRIDES if phase == "solver" else None,
                commit=COMMIT if phase == "solver" else None,
            )
            for phase in PHASES
        ),
        max_contacts=6,
    )


def _output(key):
    sample_id, phase, _visit, turn = key
    if phase == "solver":
        return json.dumps(ANSWERS[turn - 1], ensure_ascii=False, sort_keys=True)
    if phase == "planner":
        return "ACCEPT"
    return f"{phase}-analysis:{sample_id}"


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_four_greedy_first_rows_walk_and_seal_through_the_runtime(tmp_path, monkeypatch):
    class FourRowWorld(runner_tests._World):
        SAMPLE_SPECS = (("s1", 2.0), ("s2", 3.5), ("s3", 2.5), ("s4", 3.0))

    monkeypatch.setattr(runner_tests, "_World", FourRowWorld)
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=4, max_revisions=0, max_contacts=6, planner_actions=(),
    )
    harness.config = _review_off_grouped_config()
    harness._output = _output
    wire = []
    original_gate = harness.request_gate

    def recording_gate(prepared_request):
        payload = prepared_request.as_payload()
        wire.append((payload["decoding_params"].get("temperature"), payload["decoding_params"].get("seed")))
        return original_gate(prepared_request)

    harness.request_gate = recording_gate
    try:
        summary = harness.run(decoding_params={"temperature": 0, "seed": 20260913, "max_tokens": 64})
        raw_native = {
            "finite_completion_policy": harness.config.finite_completion_policy,
            "exhaustion_policy": "raise", "max_revisions": 0,
            "actions": dict(zip(("accept", "revise", "acquire"), harness.config.actions)),
            "roles": {"solver": {
                "phase_id": "solver", "samples": 5, "decoding_overrides": dict(OVERRIDES), "commit": dict(COMMIT),
            }},
        }
        runtime = object.__new__(FlightRuntime)
        runtime._composed = SimpleNamespace(values={"native_episode": raw_native})
        runtime._plan = harness.plan
        runtime._phase_summaries = [summary]
        runtime._output_rows = [
            {
                "sample_id": row.sample_id, "final_response_text": row.final_response_text,
                "native_episode_receipt": row.native_episode_receipt, "solver_group": dict(row.solver_group),
            }
            for row in summary.results
        ]
        runtime._result_kind = lambda: "answer"
        runtime._arm = lambda: harness.client.arm
        outputs = runtime._canonical_output_rows(harness.client)
    finally:
        harness.close()

    assert [row["sample_id"] for row in outputs] == ["s1", "s2", "s3", "s4"]
    # 4 rows x (1 Perception + 5 Solver) contacts; the Solver wire is greedy first, then 0.7 x 4, with the pinned seeds (offsets 0..4)
    solver_wire = [w for w in wire if w[1] != 20260913]
    assert len(wire) == 24 and len(solver_wire) == 20
    seed0 = min(seed for _, seed in solver_wire)
    # rows run concurrently, so the walk is row-interleaved: judge the wire by (temperature, seed offset) pairs
    from collections import Counter

    assert Counter((t, s - seed0) for t, s in solver_wire) == Counter({(0, 0): 4, (0.7, 1): 4, (0.7, 2): 4, (0.7, 3): 4, (0.7, 4): 4})
    for row, result in zip(outputs, summary.results):
        group = row["solver_group"]
        validate_solver_group_receipt(group, samples=5)
        assert [r["temperature"] for r in group["samples"]] == [0, 0.7, 0.7, 0.7, 0.7]
        assert group["delivered"]["intent_support"] == 3
        assert json.loads(row["text"]) == json.loads(result.final_response_text)
    records = {rid: payload for _, rid, payload in harness.trace.records}
    _verify_outputs_trace_binding(tuple(outputs), records)
