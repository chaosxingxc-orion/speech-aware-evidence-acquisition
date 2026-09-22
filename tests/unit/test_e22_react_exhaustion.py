"""Item E22: a tool role's exhausted ReAct loop is a visit disposition.

Item E22 is the ReAct-exhaustion disposition, NOT the Earnings-22 carrier.

On 2026-09-19 the B8b-anchor arm
(``SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1``, attempt
``attempt-slurp-native-reviewer-audit-anchor-train-fold-a-generation-v1``)
died after 2,016 charged contacts -- about 400 of 1,080 rows -- with

    NativeEpisodeError: review node did not return an answer

at component ``reviewer_1_state``. The Reviewer's ReAct loop
(``max_iterations`` 3) called ``saea-tool-task-contract-v1`` with ``{}`` on
iterations 1/3, 2/3 AND 3/3, the pinned framework returned its own
``"Max iterations reached without completion"`` under ``result_type``
``"error"``, and ``reproduction.ojw.native_episode._ApplyRole`` refused the
non-answer. Two Reviewer visits of 410 reached 3/3 and both took the flight
with them.

``native_episode.react_exhaustion_policy`` is the TWELFTH episode-level
switch and the THIRD failure-mode key, after E13's and E20's. ``"raise"`` is
that behaviour, unchanged and still the default.
``"continue-without-answer"`` makes the class a VISIT-level disposition: the
exhausted visit ends with NO finding, the Planner routes normally, the row
delivers as it would have, and the receipt records what happened.

What this module proves, all of it against the fake transport of
``test_native_episode_runner`` and in-memory role nodes -- zero model,
tokenizer, encoder, scorer, network and GPU contacts, and no
``SPEECHRL_DATA_DIR`` read:

1. the key parses, its null arm is the key's absence or ``"raise"``, and it
   is in the closed episode allowlist;
2. the role node recognises the framework's own exhaustion literal and
   records the loop's calls -- tool id, argument digest, observation digest
   -- and NOTHING else;
3. under ``"raise"`` the graph raises exactly the pre-E22
   ``NativeEpisodeError``, and under the armed policy the row is retained
   with no finding, the Planner routes, and the delivery is the Solver's
   own draft;
4. the framework's exhaustion literal never reaches a prompt;
5. the receipt's ``react_exhaustion`` block is validated and bound to real
   visits, and ``validate_native_episode_terminal_policy`` refuses it under
   ``"raise"``;
6. the run-level counters appear only when a row sealed the block;
7. an unarmed episode composes byte-identical requests and seals no block;
8. the gate demands BOTH failure-mode keys and names the one that is
   missing.
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest
from openjiuwen.core.foundation.tool import LocalFunction

from speech_aware_evidence_acquisition.rails.config_tables import (
    EPISODE_LEVEL_SWITCH_KEYS,
    is_episode_null_arm,
    resolve_episode_switch_key,
)
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    REACT_EXHAUSTION_DISPOSITION,
    REACT_EXHAUSTION_SCHEMA,
    validate_native_episode_delivery_receipt,
    validate_native_episode_terminal_policy,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from speech_aware_evidence_acquisition.reproduction.ojw.native_episode import (
    REACT_EXHAUSTION_STAGES,
    NativeEpisodeActions,
    NativeEpisodeError,
    NativeEpisodeSpec,
)
from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import (
    REACT_EXHAUSTION_OUTPUT,
    NativeRoleContactContext,
    NativeRoleNode,
    NativeRoleNodeSpec,
    _canonical_sha256,
    _InstanceOwnedAbility,
)

from test_native_episode_runner import _ActualEpisodeHarness, _config, _program
from test_ojw_native_roles import (
    _MeteredScript,
    _card,
    _completion,
    _tool_call,
)
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401

SWITCH_KEY = "native_episode.react_exhaustion_policy"
ARMED = "continue-without-answer"

#: Perception 1 + 1 x (Solver 1 + Reviewer 3 + Planner 1) -- the shape of the
#: flown arm's own Reviewer, at one revision instead of two.
CEILING = 6


# ---------------------------------------------------------------------------
# 1. The key.
# ---------------------------------------------------------------------------


def _episode_values(policy: str | None) -> dict:
    block = {
        "schema": "saea-native-episode-config-v1",
        "episode_id": "e22-proof-v1",
        "max_revisions": 0,
        "actions": {"accept": "ACCEPT", "revise": "REVISE", "acquire": "ACQUIRE"},
        "roles": {
            kind: {"phase_id": kind, "max_iterations": 3 if kind == "reviewer" else 1}
            for kind in ("perception", "solver", "reviewer", "planner")
        },
    }
    if policy is not None:
        block["react_exhaustion_policy"] = policy
    return {"native_episode": block}


def test_the_key_parses_and_defaults_to_raise():
    program = _program(max_contacts=CEILING)
    assert (
        load_native_episode_config(_episode_values(None), program)
        .react_exhaustion_policy
        == "raise"
    )
    assert (
        load_native_episode_config(_episode_values("raise"), program)
        .react_exhaustion_policy
        == "raise"
    )
    assert (
        load_native_episode_config(_episode_values(ARMED), program)
        .react_exhaustion_policy
        == ARMED
    )


@pytest.mark.parametrize(
    "invalid", ["continue", "", "RAISE", 1, True, None, {"policy": ARMED}]
)
def test_the_key_refuses_every_third_value(invalid):
    values = _episode_values(ARMED)
    values["native_episode"]["react_exhaustion_policy"] = invalid
    with pytest.raises(ValueError, match="react exhaustion policy"):
        load_native_episode_config(values, _program(max_contacts=CEILING))


def test_the_spec_defaults_to_raise_and_refuses_a_third_value():
    actions = NativeEpisodeActions("ACCEPT", "REVISE", "ACQUIRE")
    assert (
        NativeEpisodeSpec("e22", 0, actions).react_exhaustion_policy == "raise"
    )
    assert (
        NativeEpisodeSpec(
            "e22", 0, actions, react_exhaustion_policy=ARMED
        ).react_exhaustion_policy
        == ARMED
    )
    with pytest.raises(ValueError, match="react_exhaustion_policy"):
        NativeEpisodeSpec("e22", 0, actions, react_exhaustion_policy="continue")


def test_the_key_resolves_in_the_closed_episode_class():
    assert SWITCH_KEY in EPISODE_LEVEL_SWITCH_KEYS
    # E37 (owner decision 84, 2026-09-22) added a thirteenth key,
    # native_episode.reviewer_verdict, after this module's own admission;
    # this count is bumped so the two admissions do not race each other's
    # assertion. See tests/unit/test_e37_reviewer_verdict.py for that key's
    # own proof and tests/unit/test_config_table_module_switches.py for the
    # allowlist's full enumeration.
    assert len(EPISODE_LEVEL_SWITCH_KEYS) == 13
    assert resolve_episode_switch_key(SWITCH_KEY) == SWITCH_KEY
    # The null arm is the key's ABSENCE or its explicit default, exactly as
    # E13's and E20's are.
    assert is_episode_null_arm(SWITCH_KEY, None) is True
    assert is_episode_null_arm(SWITCH_KEY, "raise") is True
    assert is_episode_null_arm(SWITCH_KEY, ARMED) is False


# ---------------------------------------------------------------------------
# 2. The role node: recognising the class, and what it records.
# ---------------------------------------------------------------------------


class _StubAbility:
    """The smallest thing ``_InstanceOwnedAbility`` can wrap: a card and an
    ``invoke``. It exists to pin the recorder's digests EXACTLY, without a
    framework tool's own wrapping in the way."""

    def __init__(self, name: str, result: object) -> None:
        self.card = _card(name)
        self._result = result

    async def invoke(self, inputs, **kwargs):
        return self._result


def test_the_owned_ability_records_the_call_and_its_observation():
    import asyncio

    recorded: list[dict] = []

    def record(tool_id, arguments):
        entry = {
            "tool_id": tool_id,
            "arguments_sha256": _canonical_sha256(arguments),
            "observation_sha256": None,
        }
        recorded.append(entry)
        return entry

    ability = _InstanceOwnedAbility(_StubAbility("analyze", "observed-text"), record)
    assert asyncio.run(ability.invoke({"value": 1})) == "observed-text"

    assert recorded == [
        {
            "tool_id": "analyze",
            "arguments_sha256": _canonical_sha256({"value": 1}),
            "observation_sha256": _canonical_sha256("observed-text"),
        }
    ]
    # Canonical JSON, so key order is not identity, and a string is hashed
    # as the bytes it already is.
    assert _canonical_sha256({"a": 1, "b": 2}) == _canonical_sha256({"b": 2, "a": 1})
    assert _canonical_sha256("x") != _canonical_sha256('"x"')


def _exhausting_node(tmp_path_unused=None, *, iterations=3, arguments='{"value":1}'):
    """A Reviewer whose every iteration answers with a tool call."""

    observations: list[str] = []

    def analyze(value: int):
        observations.append(f"evidence-{len(observations)}")
        return observations[-1]

    script = _MeteredScript(
        [
            _completion(
                text="I will read the contract.",
                contact_id=f"contact-{index + 1}",
                serial=index + 1,
                tool_calls=_tool_call(
                    "analyze",
                    f"call-{index}",
                    arguments if index == 0 else arguments.replace("1", "2")
                    if arguments == "VARY"
                    else arguments,
                ),
            )
            for index in range(iterations)
        ]
    )
    node = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="reviewer",
            role_kind="reviewer",
            prompt="Review and report.",
            max_iterations=iterations,
            ability_names=("analyze",),
        ),
        metered_request=script,
        contact_context_provider=lambda index: NativeRoleContactContext(
            sample_id="sample-1", agent_contact_id=f"contact-{index + 1}",
        ),
        abilities=(LocalFunction(card=_card("analyze"), func=analyze),),
        tool_allowed=lambda _role, name: name == "analyze",
    )
    return node, script, observations


def _run_node(node):
    import asyncio

    async def once():
        try:
            return await node.invoke_direct("Review.")
        finally:
            await node.close()

    return asyncio.run(once())


def test_the_node_recognises_the_frameworks_own_exhaustion_literal():
    node, script, observations = _exhausting_node()
    result = _run_node(node)

    # The pinned framework's own words, not a model response.
    assert result["result_type"] == "error"
    assert result["actor_output"] == REACT_EXHAUSTION_OUTPUT
    assert len(script.requests) == 3
    assert len(observations) == 3

    block = result["react_exhaustion"]
    assert block["role_id"] == "reviewer"
    assert block["role_kind"] == "reviewer"
    assert block["iterations_used"] == block["max_iterations"] == 3
    assert block["identical_calls"] is True
    assert [call["tool_id"] for call in block["calls"]] == ["analyze"] * 3
    assert len({call["arguments_sha256"] for call in block["calls"]}) == 1
    assert set(block["calls"][0]) == {"tool_id", "arguments_sha256"}
    # Digests only: no argument value and no observation text anywhere.
    serialised = json.dumps(block)
    assert "value" not in serialised
    assert "evidence-" not in serialised
    assert len(block["last_observation_sha256"]) == 64


def test_an_answering_role_carries_no_exhaustion_block():
    """The falsifier for the recogniser: a role that answers is byte-for-byte
    the dict it was before E22."""

    script = _MeteredScript(
        [
            _completion(
                text="I will read the contract.",
                tool_calls=_tool_call("analyze", "call-0", '{"value":1}'),
            ),
            _completion(text="review complete", contact_id="contact-2", serial=2),
        ]
    )
    node = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="reviewer", role_kind="reviewer", prompt="Review.",
            max_iterations=3, ability_names=("analyze",),
        ),
        metered_request=script,
        contact_context_provider=lambda index: NativeRoleContactContext(
            sample_id="sample-1", agent_contact_id=f"contact-{index + 1}",
        ),
        abilities=(
            LocalFunction(card=_card("analyze"), func=lambda value: {"seen": value}),
        ),
        tool_allowed=lambda _role, name: name == "analyze",
    )
    result = _run_node(node)
    assert result["result_type"] == "answer"
    assert set(result) == {
        "role_id", "actor_output", "result_type", "delivery_eligible",
        "execution_receipt",
    }


def test_a_tool_free_role_can_never_reach_the_class():
    """Perception and the Solver carry no advertised ability, so an
    exhaustion of theirs is not this class and is refused as it always was."""

    script = _MeteredScript(
        [_completion(text=REACT_EXHAUSTION_OUTPUT, contact_id="contact-1")]
    )
    node = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="perception", role_kind="perception", prompt="Observe.",
            max_iterations=1,
        ),
        metered_request=script,
        contact_context_provider=lambda index: NativeRoleContactContext(
            sample_id="sample-1", agent_contact_id=f"contact-{index + 1}",
        ),
    )
    result = _run_node(node)
    # It ANSWERED (the text happens to be the literal), so there is nothing
    # to record: the class needs the framework's error outcome AND a tool
    # role AND a spent loop.
    assert result["result_type"] == "answer"
    assert "react_exhaustion" not in result


# ---------------------------------------------------------------------------
# 3-5. The graph, the prompt and the receipt, through the actual runner.
# ---------------------------------------------------------------------------


def _exhausting_harness(tmp_path, *, policy, iterations=3):
    """The flown shape: a Reviewer that answers every iteration with a call
    to ``saea-tool-task-contract-v1`` and arguments ``{}``."""

    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=0,
        max_contacts=3 + iterations,
        planner_actions=("ACCEPT",),
        reviewer_task_tool=True,
    )
    harness.config = replace(
        harness.config,
        roles=tuple(
            replace(role, max_iterations=iterations)
            if role.role_kind == "reviewer"
            else role
            for role in harness.config.roles
        ),
        react_exhaustion_policy=policy,
    )
    original = harness._output

    def output(key):
        _sample_id, phase, _visit, _turn = key
        # None means "answer with a tool call" in this fixture, so the
        # Reviewer never produces an answer at all.
        return None if phase == "reviewer" else original(key)

    harness._output = output
    return harness


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_unarmed_arm_still_kills_the_flight(tmp_path):
    """The pre-E22 behaviour, reproduced exactly: the flown message, from the
    flown component."""

    harness = _exhausting_harness(tmp_path, policy="raise")
    try:
        with pytest.raises(NativeEpisodeError) as raised:
            harness.run()
    finally:
        harness.close()
    # The flown sentence, verbatim.
    assert str(raised.value) == "review node did not return an answer"


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_armed_arm_retains_the_row_with_no_finding(tmp_path):
    harness = _exhausting_harness(tmp_path, policy=ARMED)
    try:
        summary = harness.run()
    finally:
        harness.close()

    row = summary.results[0]
    receipt = row.native_episode_receipt

    # The row delivered, through the ordinary explicit ACCEPT.
    assert row.final_response_text == "solver-answer:s1:visit:1"
    assert "accepted_solver_receipt" in receipt
    assert "terminal_disposition" not in receipt

    # Every visit is in custody, the exhausted one included: its three
    # contacts were made, metered and traced.
    assert [visit["stage"] for visit in receipt["role_visits"]] == [
        "perception", "solver", "review", "planner",
    ]
    review_visit = receipt["role_visits"][2]
    assert len(review_visit["execution_receipt"]["contacts"]) == 3

    block = receipt[REACT_EXHAUSTION_DISPOSITION]
    assert block["schema"] == REACT_EXHAUSTION_SCHEMA
    assert block["count"] == 1
    record = block["visits"][0]
    assert record["stage"] == "review"
    assert record["role_id"] == "reviewer"
    assert record["role_visit_index"] == 2
    assert record["revision_count"] == 0
    assert record["iterations_used"] == record["max_iterations"] == 3
    assert record["identical_calls"] is True
    assert [call["tool_id"] for call in record["calls"]] == [
        "saea-tool-task-contract-v1"
    ] * 3

    # The Planner ran and routed on its own; no contact was retried.
    assert receipt["planner_routes"] == [
        {"role_visit_index": 3, "revision_count": 0, "action": "ACCEPT"},
    ]
    assert len(harness.dispatched) == 6


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_frameworks_exhaustion_literal_never_reaches_a_prompt(tmp_path):
    """The one thing an "empty finding" must not become: a finding that says
    the loop broke."""

    harness = _exhausting_harness(tmp_path, policy=ARMED)
    try:
        harness.run()
    finally:
        harness.close()
    rendered = json.dumps(
        [prepared["rendered"] for prepared in harness.prepared.values()],
        sort_keys=True,
    )
    assert REACT_EXHAUSTION_OUTPUT not in rendered
    assert "Max iterations" not in rendered


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_receipt_is_validated_and_refused_without_its_policy(tmp_path):
    harness = _exhausting_harness(tmp_path, policy=ARMED)
    try:
        summary = harness.run()
    finally:
        harness.close()
    receipt = summary.results[0].native_episode_receipt

    delivery = validate_native_episode_delivery_receipt(receipt)
    # A VISIT disposition, not a delivery kind: the row is an ordinary
    # ACCEPT that happens to carry one.
    assert delivery.kind == "accepted"
    assert delivery.terminal_disposition is None
    assert delivery.react_exhaustion == receipt[REACT_EXHAUSTION_DISPOSITION]

    validate_native_episode_terminal_policy(
        delivery,
        exhaustion_policy=harness.config.exhaustion_policy,
        finite_completion_policy=harness.config.finite_completion_policy,
        react_exhaustion_policy=ARMED,
        max_revisions=harness.config.max_revisions,
    )
    with pytest.raises(ValueError, match="declared policy"):
        validate_native_episode_terminal_policy(
            delivery,
            exhaustion_policy=harness.config.exhaustion_policy,
            finite_completion_policy=harness.config.finite_completion_policy,
            react_exhaustion_policy="raise",
            max_revisions=harness.config.max_revisions,
        )
    # The default is the refusal, so a reader written before E22 that never
    # passes the new keyword still refuses an undeclared block.
    with pytest.raises(ValueError, match="declared policy"):
        validate_native_episode_terminal_policy(
            delivery,
            exhaustion_policy=harness.config.exhaustion_policy,
            finite_completion_policy=harness.config.finite_completion_policy,
            max_revisions=harness.config.max_revisions,
        )


def _visits(**overrides):
    record = {
        "role_id": "reviewer",
        "stage": "review",
        "role_visit_index": 0,
        "revision_count": 0,
        "iterations_used": 3,
        "max_iterations": 3,
        "identical_calls": True,
        "calls": [{"tool_id": "t", "arguments_sha256": "a" * 64}] * 3,
        "last_observation_sha256": "b" * 64,
    }
    record.update(overrides)
    return record


def _receipt_with(block, *, stage="review", role_id="reviewer"):
    contact = {
        "agent_contact_id": "c-1",
        "request_id": "r-1",
        "request_sha256": "1" * 64,
        "response_sha256": "2" * 64,
        "response_text_sha256": "3" * 64,
    }
    execution = {"contacts": [contact], "final_contact": dict(contact)}
    solver = {
        "agent_contact_id": "c-2",
        "request_id": "r-2",
        "request_sha256": "4" * 64,
        "response_sha256": "5" * 64,
        "response_text_sha256": "6" * 64,
    }
    solver_receipt = {"contacts": [solver], "final_contact": dict(solver)}
    return {
        "role_visits": [
            {"role_id": role_id, "stage": stage, "execution_receipt": execution},
            {"role_id": "solver", "stage": "solver", "execution_receipt": solver_receipt},
        ],
        "planner_routes": [],
        "accepted_solver_receipt": solver_receipt,
        REACT_EXHAUSTION_DISPOSITION: block,
    }


def _block(*records):
    return {
        "schema": REACT_EXHAUSTION_SCHEMA,
        "count": len(records),
        "visits": list(records),
    }


def test_the_validator_binds_every_record_to_a_real_visit():
    receipt = _receipt_with(_block(_visits()))
    delivery = validate_native_episode_delivery_receipt(receipt)
    assert delivery.kind == "accepted"
    assert delivery.react_exhaustion["count"] == 1


@pytest.mark.parametrize(
    ("block", "message"),
    [
        ({"schema": "other", "count": 1, "visits": [_visits()]}, "malformed"),
        ({"schema": REACT_EXHAUSTION_SCHEMA, "count": 2, "visits": [_visits()]},
         "count differs"),
        (_block(), "count differs"),
        (_block(_visits(role_visit_index=9)), "actual role visit"),
        (_block(_visits(stage="solver")), "actual role visit"),
        (_block(_visits(role_id="planner")), "actual role visit"),
        (_block(_visits(), _visits()), "actual role visit"),
        (_block(_visits(iterations_used=2)), "whole declared iteration budget"),
        (_block(_visits(calls=[])), "records no tool call"),
        (_block(_visits(identical_calls=False)), "differs from its own calls"),
        (_block(_visits(calls=[{"tool_id": "t", "arguments_sha256": "nope"}])),
         "64-hex"),
        (_block(_visits(last_observation_sha256="nope")), "64-hex"),
    ],
)
def test_the_validator_refuses_a_malformed_block(block, message):
    with pytest.raises(ValueError, match=message):
        validate_native_episode_delivery_receipt(_receipt_with(block))


def test_only_the_review_stage_may_end_without_a_finding():
    """A Solver visit owes a draft and a Planner visit owes a route, so
    neither may take this disposition -- stated by the module and enforced by
    the receipt validator."""

    assert set(REACT_EXHAUSTION_STAGES) == {"review"}
    with pytest.raises(ValueError, match="inadmissible stage"):
        validate_native_episode_delivery_receipt(
            _receipt_with(
                _block(_visits(stage="planner", role_id="planner")),
                stage="planner", role_id="planner",
            )
        )


# ---------------------------------------------------------------------------
# 6. The run-level counters.
# ---------------------------------------------------------------------------


def test_the_manifest_counts_rows_and_visits_only_when_a_row_sealed_one(tmp_path):
    import test_flight_runtime as flight

    runtime = flight._make_runtime(tmp_path)
    unarmed = {
        "planner_action_illegal_rows": 0,
        "finite_completion_rows": 0,
        "context_compaction_rows": 0,
        "context_compaction_contacts": 0,
    }
    assert runtime._episode_disposition_counts() == unarmed

    # An armed dispatch on which NOTHING exhausted reports exactly the same
    # four counters -- the E21w rule, applied here.
    runtime._output_rows = [{"sample_id": "a", "native_episode_receipt": {}}]
    assert runtime._episode_disposition_counts() == unarmed

    runtime._output_rows = [
        {"sample_id": "a", "native_episode_receipt": {
            REACT_EXHAUSTION_DISPOSITION: {"count": 2, "visits": [{}, {}]},
        }},
        {"sample_id": "b", "native_episode_receipt": {
            REACT_EXHAUSTION_DISPOSITION: {"count": 1, "visits": [{}]},
        }},
        {"sample_id": "c", "native_episode_receipt": {}},
    ]
    assert runtime._episode_disposition_counts() == {
        **unarmed,
        "react_exhaustion_rows": 2,
        "react_exhaustion_visits": 3,
    }


# ---------------------------------------------------------------------------
# 7. Byte identity with the key absent.
# ---------------------------------------------------------------------------


def _answering_harness(tmp_path, *, policy):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=0,
        max_contacts=4,
        planner_actions=("ACCEPT",),
    )
    harness.config = replace(harness.config, react_exhaustion_policy=policy)
    return harness


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_arming_the_key_moves_no_request_byte_on_a_row_that_answers(tmp_path):
    """E13/E17/E20/E21's own falsifier, applied here: the key renders
    nothing at all. Every role answers, so the two arms must compose
    identical bytes and seal identical receipts."""

    rendered = {}
    receipts = {}
    for armed in (True, False):
        harness = _answering_harness(
            tmp_path / ("on" if armed else "off"),
            policy=ARMED if armed else "raise",
        )
        try:
            summary = harness.run()
        finally:
            harness.close()
        assert summary.results[0].final_response_text == "solver-answer:s1:visit:1"
        rendered[armed] = sorted(
            (key, json.dumps(prepared["rendered"], sort_keys=True))
            for key, prepared in harness.prepared.items()
        )
        receipts[armed] = summary.results[0].native_episode_receipt

    on, off = rendered[True], rendered[False]
    assert [key for key, _ in on] == [key for key, _ in off]
    assert {key[1] for key, _ in on} >= {"solver", "reviewer", "planner"}
    assert on == off, "arming the key moved a composed request"
    assert REACT_EXHAUSTION_DISPOSITION not in receipts[True]
    assert REACT_EXHAUSTION_DISPOSITION not in receipts[False]
    assert receipts[True] == receipts[False]


def test_the_harness_config_default_is_the_pre_e22_behaviour():
    config = _config(max_revisions=1, max_contacts=7)
    assert config.react_exhaustion_policy == "raise"


# ---------------------------------------------------------------------------
# 8. The gate.
# ---------------------------------------------------------------------------


def test_the_gate_demands_both_keys_and_names_the_missing_one(tmp_path):
    import test_finite_completion_policy_check as e13

    from finite_completion_policy_check import (  # noqa: PLC0415
        POLICY_KEY,
        REACT_POLICY_KEY,
        REQUIRED_POLICY,
        REQUIRED_REACT_POLICY,
    )
    import finite_completion_policy_check as gate  # noqa: PLC0415

    # Both armed: the gate passes.
    e13._build(tmp_path / "both", policy=REQUIRED_POLICY)
    assert gate.evaluate(tmp_path / "both")["passed"] is True

    # Only E13's key: one finding, naming E22's.
    e13._build(tmp_path / "e13", policy=REQUIRED_POLICY, react_policy=None)
    result = gate.evaluate(tmp_path / "e13")
    assert [v["key"] for v in result["violations"]] == [REACT_POLICY_KEY]
    assert REACT_POLICY_KEY in result["violations"][0]["message"]
    assert REQUIRED_REACT_POLICY in result["violations"][0]["message"]
    assert "ABSENT" in result["violations"][0]["message"]

    # Only E22's key: one finding, naming E13's.
    e13._build(tmp_path / "e22", policy=None, react_policy=REQUIRED_REACT_POLICY)
    result = gate.evaluate(tmp_path / "e22")
    assert [v["key"] for v in result["violations"]] == [POLICY_KEY]
    assert POLICY_KEY in result["violations"][0]["message"]

    # Neither: two findings, in key order.
    e13._build(tmp_path / "none", policy=None, react_policy=None)
    result = gate.evaluate(tmp_path / "none")
    assert [v["key"] for v in result["violations"]] == [POLICY_KEY, REACT_POLICY_KEY]

    # The abort default written out loud is refused twice over, exactly as
    # E13's is.
    e13._build(tmp_path / "loud", policy=REQUIRED_POLICY, react_policy="raise")
    result = gate.evaluate(tmp_path / "loud")
    assert sorted(v["kind"] for v in result["violations"]) == [
        "declared-third-value", "wrong-policy",
    ]
    assert {v["key"] for v in result["violations"]} == {REACT_POLICY_KEY}
