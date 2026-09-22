"""E20 (2026-09-19): an over-long request degrades into a retained row.

Owner decision 45 and the measured analysis ``docs/results/
2026-09-19-slurp-serving-geometry-and-degradation-v1.md`` part B. Before this
item a request wider than the live serving slot ended the FLIGHT: preflight
raised on the rail's own ``COMPACT_REQUIRED`` verdict ("A pre-flight estimate
has no live compaction mechanism to apply"), dispatch budgeted nothing at
all, and the built fork's HTTP 400 ``exceed_context_size_error`` came back as
a plain ``FrozenCoreError`` at row N of 13,078 with everything after it
unflown.

``native_episode.context_fit_policy`` is the tenth episode-level switch.
``"raise"`` is every one of those behaviours, unchanged. ``"compact-or-
abstain"`` makes the whole class a ROW-level disposition.

What this module proves, all of it against the fake transport of
``test_native_episode_runner`` and pure in-memory views -- zero model,
tokenizer, encoder, network and GPU contacts, and no ``SPEECHRL_DATA_DIR``
read:

1. the key parses, its null arm is the key's absence or ``"raise"``, and it
   is in the closed episode allowlist;
2. the declared drop order is exactly the order of ``DROP_ORDER``, tail-first
   inside each evidence block and oldest-first in the history, in two
   tranches -- and the never-droppable parts survive byte for byte;
3. at preflight a ``COMPACT_REQUIRED`` representative proceeds under the
   armed policy and still raises without it, while a request that exceeds the
   PHYSICAL slot raises on both arms;
4. a dispatch-time over-long request is compacted in that order and SENT,
   with a ``context_compaction`` record naming what went;
5. a request that cannot be made to fit takes the ``context_compaction``
   terminal disposition with the latest Solver draft delivered;
6. the fork's HTTP 400 ``exceed_context_size_error`` takes the same
   disposition with the server's own message, and every other HTTP error
   still raises;
7. an unarmed episode composes byte-identical requests.
"""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from speech_aware_evidence_acquisition.core.model import (
    FrozenCoreContextSizeError,
    FrozenCoreError,
)
from speech_aware_evidence_acquisition.core.model.transport import (
    _exceed_context_message,
)
from speech_aware_evidence_acquisition.rails.config_tables import (
    EPISODE_LEVEL_SWITCH_KEYS,
    is_episode_null_arm,
    resolve_episode_switch_key,
)
from speech_aware_evidence_acquisition.rails.context_fit import (
    AGENT_STATES_BLOCK,
    CANDIDATE_CARDS_BLOCK,
    DROP_ORDER,
    EXEMPLAR_SUPPLY_BLOCK,
    NEVER_DROPPABLE,
    REVIEWER_AUDIT_BLOCK,
    REVIEWER_AUDIT_IDENTIFIER,
    SCENARIO_HINTS_BLOCK,
    SCENARIO_HINTS_IDENTIFIER,
    BlockAttachment,
    CompactableRequest,
    ContextFitError,
    apply_drops,
    compact_to_fit,
    droppable_items,
    is_context_fit_null_arm,
    parse_context_fit_policy,
)
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    ContextFitBudget,
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    validate_native_episode_delivery_receipt,
    validate_native_episode_finite_path,
    validate_native_episode_terminal_policy,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from speech_aware_evidence_acquisition.reproduction.ojw.native_episode import (
    NativeEpisodeSpec,
)

from test_native_episode_runner import _ActualEpisodeHarness, _config, _program
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401

SWITCH_KEY = "native_episode.context_fit_policy"
ARMED = "compact-or-abstain"

#: Perception 1 + 2 x (Solver 1 + Reviewer 1 + Planner 1).
CEILING = 7


# ---------------------------------------------------------------------------
# 1. The key.
# ---------------------------------------------------------------------------


def test_the_key_parses_and_keeps_its_null_arm():
    assert parse_context_fit_policy(None) == "raise"
    assert parse_context_fit_policy("raise") == "raise"
    assert parse_context_fit_policy(ARMED) == ARMED
    for bad in ("compact", "", 1, True, {"policy": ARMED}):
        with pytest.raises(ContextFitError):
            parse_context_fit_policy(bad)

    # The OFF arm is the key's ABSENCE or its explicit default, exactly as
    # E13's and E17's are, so a fragment that writes the default out loud
    # composes the same episode as one that omits it.
    assert is_context_fit_null_arm(None) is True
    assert is_context_fit_null_arm("raise") is True
    assert is_context_fit_null_arm(ARMED) is False


def test_the_key_resolves_in_the_closed_episode_class():
    assert SWITCH_KEY in EPISODE_LEVEL_SWITCH_KEYS
    assert resolve_episode_switch_key(SWITCH_KEY) == SWITCH_KEY
    assert is_episode_null_arm(SWITCH_KEY, None) is True
    assert is_episode_null_arm(SWITCH_KEY, "raise") is True
    assert is_episode_null_arm(SWITCH_KEY, ARMED) is False


#: The sealed SLURP TRAIN Fold A anchor -- the same fragment E13's proof
#: reads, so the parse below is of a config this study actually flies.
ANCHOR_RELPATH = "configs/baseline/slurp-native-dual-store-train-fold-a-anchor-v1.json"
#: The anchor's own bounded graph ceiling (Perception 1 + 2 x (Solver 1 +
#: Reviewer 3 + Planner 1)).
ANCHOR_CEILING = 11


def _anchor_values(*, armed: bool) -> dict:
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    values = json.loads(
        (repo_root / ANCHOR_RELPATH).read_text(encoding="utf-8")
    )
    episode = values["native_episode"]
    # The gap this item closes: no sealed SLURP baseline declares the key.
    assert "context_fit_policy" not in episode
    if armed:
        episode["context_fit_policy"] = ARMED
    return values


def test_the_episode_config_and_spec_default_to_raise():
    program = _program(max_contacts=ANCHOR_CEILING)
    plain = load_native_episode_config(_anchor_values(armed=False), program)
    assert plain.context_fit_policy == "raise"

    armed = load_native_episode_config(_anchor_values(armed=True), program)
    assert armed.context_fit_policy == ARMED
    # Exactly one leaf moves.
    assert {
        name: getattr(armed, name)
        for name in armed.__dataclass_fields__
        if name != "context_fit_policy"
    } == {
        name: getattr(plain, name)
        for name in plain.__dataclass_fields__
        if name != "context_fit_policy"
    }

    bad = _anchor_values(armed=False)
    bad["native_episode"]["context_fit_policy"] = "compact"
    with pytest.raises(ValueError, match="context_fit_policy"):
        load_native_episode_config(bad, program)

    # The episode spec's own field is APPENDED, so every positional
    # construction written before E20 composes the spec it always did. Item
    # E22 (the ReAct-exhaustion disposition, not the Earnings-22 carrier)
    # appended its own key after it under exactly the same rule, which
    # leaves E20's position untouched. Item E37 (owner decision 84) appended
    # a third key after E22's under the same rule, and item E39 (2026-09-22)
    # a fourth after E37's, which leaves E20's, E22's and E37's positions
    # untouched.
    assert list(NativeEpisodeSpec.__dataclass_fields__)[-4:] == [
        "context_fit_policy",
        "react_exhaustion_policy",
        "reviewer_verdict_vocabulary",
        "finite_completion_scope",
    ]


# ---------------------------------------------------------------------------
# 2. The declared drop order, and what is never dropped.
# ---------------------------------------------------------------------------


_AUDIT_BLOCK = "[audit] entity_type: device_name appears in 82 % of rows"
_HINTS_BLOCK = "[hints] the scenario 'lighting' most often takes action 'set'"


def _text_part(evidence_id, role, text):
    return {
        "type": "text", "text": text, "evidence_id": evidence_id,
        "knowledge_role": role,
    }


def _state(state_id, content):
    return {"state_id": state_id, "state_kind": "phase-response", "content": content}


def _sha(text):
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rich_request():
    """One realised request carrying every droppable class at once."""

    speech = {
        "type": "input_speech_features",
        "speech_features": {"packet_id": "p1", "sha256": "a" * 64, "role": "query"},
    }
    content = (
        speech,
        _text_part("key:intent:lighting", "key", "Lighting intents."),
        _text_part("key:intent:music", "key", "Music intents."),
        _text_part("key:intent:alarm", "key", "Alarm intents."),
        _text_part("key:intent:news", "key", "News intents."),
        _text_part("value:ex-1", "value", "Exemplar one."),
        _text_part("value:ex-2", "value", "Exemplar two."),
        _text_part("value:ex-3", "value", "Exemplar three."),
        _text_part("value:ex-4", "value", "Exemplar four."),
    )
    states = (
        _state("s-old", "oldest perception state"),
        _state("s-hints", f"candidate rendering\n{_HINTS_BLOCK}"),
        _state("s-draft", f"the current draft\n{_AUDIT_BLOCK}"),
    )
    attachments = (
        BlockAttachment(
            state_id="s-hints", block=SCENARIO_HINTS_BLOCK,
            chars=len(_HINTS_BLOCK), sha256=_sha(_HINTS_BLOCK),
        ),
        BlockAttachment(
            state_id="s-draft", block=REVIEWER_AUDIT_BLOCK,
            chars=len(_AUDIT_BLOCK), sha256=_sha(_AUDIT_BLOCK),
        ),
    )
    return CompactableRequest(
        content=content, agent_states=states, attachments=attachments
    )


def test_the_drop_order_is_exactly_the_declared_one():
    request = _rich_request()
    items = droppable_items(request)

    # Tranche 1 first, then tranche 2; within a tranche, DROP_ORDER.
    tranches = [item.tranche for item in items]
    assert tranches == sorted(tranches)
    by_tranche = {1: [], 2: []}
    for item in items:
        by_tranche[item.tranche].append((item.block, item.identifier))

    # Tranche 1: the exemplar tail beyond k // 2 (4 items -> keep 2, drop the
    # last 2, tail first), then the candidate tail on the same rule, then the
    # whole hints block, then the whole audit block, then every agent state
    # but the newest, oldest first.
    assert by_tranche[1] == [
        (EXEMPLAR_SUPPLY_BLOCK, "value:ex-4"),
        (EXEMPLAR_SUPPLY_BLOCK, "value:ex-3"),
        (CANDIDATE_CARDS_BLOCK, "facet:intent:news"),
        (CANDIDATE_CARDS_BLOCK, "facet:intent:alarm"),
        (SCENARIO_HINTS_BLOCK, SCENARIO_HINTS_IDENTIFIER),
        (REVIEWER_AUDIT_BLOCK, REVIEWER_AUDIT_IDENTIFIER),
        (AGENT_STATES_BLOCK, "agent-state:s-old"),
        (AGENT_STATES_BLOCK, "agent-state:s-hints"),
    ]
    # Tranche 2: the retained halves, still tail first, still by DROP_ORDER.
    assert by_tranche[2] == [
        (EXEMPLAR_SUPPLY_BLOCK, "value:ex-2"),
        (EXEMPLAR_SUPPLY_BLOCK, "value:ex-1"),
        (CANDIDATE_CARDS_BLOCK, "facet:intent:music"),
        (CANDIDATE_CARDS_BLOCK, "facet:intent:lighting"),
    ]
    # The newest state -- the current draft -- is in NEITHER tranche.
    assert all(item.identifier != "agent-state:s-draft" for item in items)
    assert [item.block for item in items[:1]] == [DROP_ORDER[0]]


def test_never_droppable_parts_survive_byte_for_byte():
    request = _rich_request()
    everything = droppable_items(request)
    stripped = apply_drops(request, everything)

    # The speech packet reference is untouched, byte for byte.
    assert stripped.content[0] == request.content[0]
    # Every evidence part is gone; nothing else is.
    assert len(stripped.content) == 1
    # The current draft survives, and the audit block appended to it is gone
    # -- removed by exact trailing bytes, never by rewriting the draft.
    assert len(stripped.agent_states) == 1
    assert stripped.agent_states[0]["state_id"] == "s-draft"
    assert stripped.agent_states[0]["content"] == "the current draft"
    assert set(NEVER_DROPPABLE) == {
        "instruction-text", "task-contract", "speech-packet-reference",
        "current-draft", "tools-array",
    }


def test_an_attachment_is_removed_only_on_an_exact_digest_match():
    request = _rich_request()
    # A receipt that names the right length but the wrong bytes drops nothing:
    # the block is simply not an addressable item for this contact.
    lying = BlockAttachment(
        state_id="s-draft", block=REVIEWER_AUDIT_BLOCK,
        chars=len(_AUDIT_BLOCK), sha256=_sha("some other block"),
    )
    poisoned = CompactableRequest(
        content=request.content, agent_states=request.agent_states,
        attachments=(lying,),
    )
    assert all(
        item.block != REVIEWER_AUDIT_BLOCK for item in droppable_items(poisoned)
    )


def test_compaction_stops_at_the_first_view_that_fits():
    request = _rich_request()

    def measure(view):
        # One token per content part and per agent state, plus a fixed floor.
        return 10 + len(view.content) + len(view.agent_states)

    # Fits already: nothing moves and no pass is spent.
    outcome = compact_to_fit(request, measure=measure, limit_tokens=100)
    assert outcome.fitted and outcome.passes == 0 and outcome.dropped == ()
    assert outcome.request is request
    assert outcome.record()["blocks"] == []

    # Two tokens over: exactly the first two items of the declared order go.
    outcome = compact_to_fit(request, measure=measure, limit_tokens=20)
    assert outcome.fitted is True
    assert outcome.passes == 1
    assert outcome.dropped_identifiers() == ("value:ex-4", "value:ex-3")
    record = outcome.record(budget_receipt_sha256="b" * 64)
    assert record["schema"] == "saea-context-compaction-v1"
    assert record["blocks"] == [
        {
            "block": EXEMPLAR_SUPPLY_BLOCK,
            "identifiers": ["value:ex-4", "value:ex-3"],
            "items": 2,
        }
    ]
    assert record["tokens_before"] == 22 and record["tokens_after"] == 20
    assert record["budget_receipt_sha256"] == "b" * 64

    # Not enough even after both passes: the outcome says so rather than
    # truncating anything.
    outcome = compact_to_fit(request, measure=measure, limit_tokens=5)
    assert outcome.fitted is False
    assert outcome.passes == 2
    # Everything droppable is gone: the speech part and the current draft
    # are all that is left, and ``measure`` charges 10 + 1 + 1.
    assert outcome.tokens_after == 12


# ---------------------------------------------------------------------------
# 3. Preflight.
# ---------------------------------------------------------------------------


def _preflight_runtime(tmp_path, *, armed: bool, tokens: int):
    import test_flight_runtime as flight

    baseline_extra = (
        {"native_episode": {"context_fit_policy": ARMED}} if armed else None
    )
    return flight._make_runtime(
        tmp_path,
        config_kwargs={"baseline_extra": baseline_extra} if armed else {},
        token_counter=lambda payload_bytes: tokens,
    )


def test_preflight_proceeds_on_compact_required_only_under_the_armed_policy(tmp_path):
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntimeError

    # 3,800 rendered tokens against the fake adapter's 4,096-token slot and
    # its 512-token reserve: the operational margin is negative
    # (COMPACT_REQUIRED) but the PHYSICAL margin is not -- the prompt fits
    # the hardware, only not the reserve.
    armed = _preflight_runtime(tmp_path / "on", armed=True, tokens=3_800)
    receipt = armed.preflight()
    (budget,) = receipt["prompt_budget"]
    assert budget["decision"] == "COMPACT_REQUIRED"
    assert budget["physical_margin_tokens"] >= 0
    assert budget["operational_margin_tokens"] < 0

    plain = _preflight_runtime(tmp_path / "off", armed=False, tokens=3_800)
    with pytest.raises(FlightRuntimeError, match="prompt budget COMPACT_REQUIRED"):
        plain.preflight()


def test_preflight_still_refuses_a_request_wider_than_the_physical_slot(tmp_path):
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntimeError

    # A million tokens does not fit the slot itself: no compaction can repair
    # that, so it aborts on BOTH arms.
    for armed in (True, False):
        runtime = _preflight_runtime(
            tmp_path / ("on" if armed else "off"), armed=armed, tokens=1_000_000
        )
        with pytest.raises(FlightRuntimeError, match="prompt budget"):
            runtime.preflight()


# ---------------------------------------------------------------------------
# 4-7. The live dispatch seam.
# ---------------------------------------------------------------------------


def _armed_harness(tmp_path, *, budget, policy=ARMED, **kwargs):
    from dataclasses import replace

    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=CEILING,
        planner_actions=("ACCEPT",),
        **kwargs,
    )
    harness.config = replace(harness.config, context_fit_policy=policy)
    harness.context_fit_budget = budget
    return harness


def _budget(counter, *, prompt_limit_tokens: int) -> ContextFitBudget:
    """A budget whose ``prompt_limit_tokens`` is exactly what a test wants."""

    return ContextFitBudget(
        slot_tokens=prompt_limit_tokens + 66,
        reserve_tokens=0,
        completion_ceiling=64,
        token_counter=counter,
        special_token_reserve=2,
    )


def _reviewer_heavy_counter(body_bytes: bytes) -> int:
    """Only the Reviewer's request is over budget, and only while it still
    carries the Perception state."""

    text = body_bytes.decode("utf-8", "replace")
    if "native-role:reviewer:" not in text:
        return 10
    return 400 if "perception-analysis" in text else 40


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_an_over_long_request_is_compacted_in_order_and_still_sent(tmp_path):
    harness = _armed_harness(
        tmp_path, budget=_budget(_reviewer_heavy_counter, prompt_limit_tokens=100)
    )
    try:
        summary = harness.run()
    finally:
        harness.close()

    row = summary.results[0]
    receipt = row.native_episode_receipt
    # The row delivered normally: a compacted contact is not a degraded row.
    assert row.final_response_text == "solver-answer:s1:visit:1"
    assert "terminal_disposition" not in receipt
    assert receipt["accepted_solver_receipt"]

    block = receipt["context_fit"]
    assert block["schema"] == "saea-native-context-fit-v1"
    assert block["policy"] == ARMED
    assert block["prompt_limit_tokens"] == 100
    assert block["compacted_contacts"] == 1
    compacted = [
        row for row in block["contacts"] if row["context_compaction"] is not None
    ]
    assert len(compacted) == 1
    record = compacted[0]["context_compaction"]
    assert compacted[0]["role_id"] == "reviewer"
    assert record["passes"] == 1
    assert record["fitted"] is True
    assert record["tokens_before"] == 400
    assert record["tokens_after"] == 40
    # The declared order reached the history block and stopped there: exactly
    # one agent state went, and it was the OLDEST.
    assert [entry["block"] for entry in record["blocks"]] == [AGENT_STATES_BLOCK]
    assert len(record["dropped_identifiers"]) == 1
    assert record["dropped_identifiers"][0].startswith("agent-state:")

    # Every other contact carries a null record, so the receipt says the check
    # ran on all of them rather than only on the one that moved.
    assert [
        row["context_compaction"] is None for row in block["contacts"]
    ].count(True) == len(block["contacts"]) - 1


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_request_that_cannot_fit_retains_the_row_and_delivers_the_draft(tmp_path):
    def counter(body_bytes: bytes) -> int:
        text = body_bytes.decode("utf-8", "replace")
        return 10_000 if "native-role:reviewer:" in text else 10

    harness = _armed_harness(
        tmp_path, budget=_budget(counter, prompt_limit_tokens=100)
    )
    try:
        summary = harness.run()
    finally:
        harness.close()

    row = summary.results[0]
    receipt = row.native_episode_receipt
    disposition = receipt["terminal_disposition"]
    assert disposition["reason"] == "context_compaction"
    assert disposition["stage"] == "review"
    assert disposition["role_id"] == "reviewer"
    assert disposition["source"] == "dispatch-budget"
    assert disposition["server_message"] is None
    assert disposition["planner_accepted"] is False
    # One pass, because this roster HAS no second tranche: the fake
    # snapshot exposes a single facet card (retained floor 0) and the row
    # carries one droppable agent state, so every droppable item of this
    # request is a tranche-1 item and the walk ends there.
    assert disposition["compaction_pass"] == 1
    assert disposition["tokens_before"] == 10_000
    assert disposition["limit_tokens"] == 100
    assert disposition["dropped_identifiers"]

    # The row is RETAINED and what it delivers is the Solver's own draft.
    assert row.final_response_text == "solver-answer:s1:visit:1"
    assert "terminal_solver_receipt" in receipt
    assert "abstention_receipt" not in receipt
    assert "accepted_solver_receipt" not in receipt
    assert [visit["stage"] for visit in receipt["role_visits"]] == [
        "perception", "solver",
    ]
    # The interrupted Reviewer made no contact of its own: the refused
    # request never reached the wire.
    assert receipt["interrupted_role"] == {
        "role_id": "reviewer", "stage": "review",
    }

    delivery = validate_native_episode_delivery_receipt(receipt)
    assert delivery.kind == "context-fit"
    assert (
        validate_native_episode_finite_path(
            receipt,
            max_revisions=harness.config.max_revisions,
            accept_action=harness.config.actions[0],
            revise_action=harness.config.actions[1],
        )
        == 0
    )
    validate_native_episode_terminal_policy(
        delivery,
        exhaustion_policy=harness.config.exhaustion_policy,
        finite_completion_policy=harness.config.finite_completion_policy,
        context_fit_policy=ARMED,
        max_revisions=harness.config.max_revisions,
    )
    with pytest.raises(ValueError, match="configured"):
        validate_native_episode_terminal_policy(
            delivery,
            exhaustion_policy=harness.config.exhaustion_policy,
            finite_completion_policy=harness.config.finite_completion_policy,
            context_fit_policy="raise",
            max_revisions=harness.config.max_revisions,
        )


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_unarmed_arm_still_kills_the_flight_on_a_request_it_cannot_fit(tmp_path):
    """The pre-E20 behaviour, reproduced: with the key absent nothing checks
    the live slot at dispatch at all, so the harness composes and sends the
    over-long request exactly as it always did."""

    harness = _armed_harness(tmp_path, budget=None, policy="raise")
    try:
        summary = harness.run()
    finally:
        harness.close()
    receipt = summary.results[0].native_episode_receipt
    assert "context_fit" not in receipt
    assert "terminal_disposition" not in receipt


# ---------------------------------------------------------------------------
# 6. The wire.
# ---------------------------------------------------------------------------


def _exceed_body(message: str = "request (30000 tokens) exceeds the available "
                 "context size (24576 tokens), try increasing it") -> bytes:
    return json.dumps(
        {"error": {"code": 400, "message": message,
                   "type": "exceed_context_size_error"}}
    ).encode()


def test_only_the_forks_context_size_error_is_classified():
    message = "request (30000 tokens) exceeds the available context size"
    assert _exceed_context_message(400, _exceed_body(message).decode()) == message
    # Right type, wrong status.
    assert _exceed_context_message(500, _exceed_body().decode()) is None
    # Right status, another error class.
    assert _exceed_context_message(
        400, json.dumps({"error": {"type": "invalid_request_error"}})
    ) is None
    # A body this cannot parse is never guessed at.
    assert _exceed_context_message(400, "exceed_context_size_error") is None
    assert _exceed_context_message(400, "") is None


def _refusing_post(harness, *, status: int, body: bytes, marker: str):
    """Wrap the harness's own transport post so ONE role's contact fails."""

    original = harness.transport._post

    def post(url, body_bytes):
        if marker in body_bytes.decode("utf-8", "replace"):
            raise urllib.error.HTTPError(
                url, status, "Bad Request", {}, io.BytesIO(body)
            )
        return original(url, body_bytes)

    harness.transport._post = post


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_forks_http_400_becomes_the_same_retained_row(tmp_path):
    harness = _armed_harness(
        tmp_path, budget=_budget(lambda _bytes: 10, prompt_limit_tokens=100)
    )
    _refusing_post(
        harness, status=400, body=_exceed_body(), marker="native-role:reviewer:"
    )
    try:
        summary = harness.run()
    finally:
        harness.close()

    receipt = summary.results[0].native_episode_receipt
    disposition = receipt["terminal_disposition"]
    assert disposition["reason"] == "context_compaction"
    assert disposition["source"] == "server-refusal"
    assert disposition["stage"] == "review"
    assert "exceeds the available context size" in disposition["server_message"]
    assert summary.results[0].final_response_text == "solver-answer:s1:visit:1"
    assert validate_native_episode_delivery_receipt(receipt).kind == "context-fit"


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_every_other_http_error_still_raises(tmp_path):
    harness = _armed_harness(
        tmp_path, budget=_budget(lambda _bytes: 10, prompt_limit_tokens=100)
    )
    _refusing_post(
        harness,
        status=500,
        body=json.dumps({"error": {"type": "server_error"}}).encode(),
        marker="native-role:reviewer:",
    )
    try:
        with pytest.raises(Exception) as caught:
            harness.run()
    finally:
        harness.close()
    assert "HTTP 500" in str(caught.value)
    assert not isinstance(caught.value, FrozenCoreContextSizeError)


def test_a_context_size_error_is_a_frozen_core_error():
    error = FrozenCoreContextSizeError("boom", server_message="too wide")
    assert isinstance(error, FrozenCoreError)
    assert error.server_message == "too wide"
    assert FrozenCoreContextSizeError.WIRE_ERROR_TYPE == "exceed_context_size_error"


# ---------------------------------------------------------------------------
# 7. Byte identity.
# ---------------------------------------------------------------------------


def _rendered_requests(harness):
    return sorted(
        (key, json.dumps(prepared["rendered"], sort_keys=True))
        for key, prepared in harness.prepared.items()
    )


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_arming_the_key_moves_no_request_byte_on_a_row_that_fits(tmp_path):
    """E17/E18's own falsifier, applied here: the key renders nothing.

    A contact whose realised request already fits is dispatched as the
    object ``prepare`` returned, so the two arms must compose identical
    bytes on a roster where nothing is over budget.
    """

    rendered = {}
    for armed in (True, False):
        harness = _armed_harness(
            tmp_path / ("on" if armed else "off"),
            budget=(
                _budget(lambda _bytes: 10, prompt_limit_tokens=10_000)
                if armed else None
            ),
            policy=ARMED if armed else "raise",
        )
        try:
            summary = harness.run()
        finally:
            harness.close()
        assert summary.results[0].final_response_text == "solver-answer:s1:visit:1"
        rendered[armed] = _rendered_requests(harness)

    on, off = rendered[True], rendered[False]
    assert [key for key, _ in on] == [key for key, _ in off]
    assert {key[1] for key, _ in on} >= {"solver", "reviewer", "planner"}
    assert on == off, "arming the key moved a composed request"


def test_the_runners_manifest_counts_every_row_level_disposition(tmp_path):
    """Deliverable 2's counters, read off the rows' own sealed receipts.

    ``context_compaction_rows`` and ``context_compaction_contacts`` are
    deliberately different numbers: most compacted contacts belong to rows
    that go on to deliver normally.
    """

    import test_flight_runtime as flight

    runtime = flight._make_runtime(tmp_path)
    assert runtime._episode_disposition_counts() == {
        "planner_action_illegal_rows": 0,
        "finite_completion_rows": 0,
        "context_compaction_rows": 0,
        "context_compaction_contacts": 0,
    }
    runtime._output_rows = [
        {"sample_id": "a", "native_episode_receipt": {
            "planner_action_illegal": {"count": 1},
            "context_fit": {"compacted_contacts": 3},
        }},
        {"sample_id": "b", "native_episode_receipt": {
            "terminal_disposition": {"reason": "finite_completion"},
        }},
        {"sample_id": "c", "native_episode_receipt": {
            "terminal_disposition": {"reason": "context_compaction"},
            "context_fit": {"compacted_contacts": 2},
        }},
        {"sample_id": "d"},
    ]
    assert runtime._episode_disposition_counts() == {
        "planner_action_illegal_rows": 1,
        "finite_completion_rows": 1,
        "context_compaction_rows": 1,
        "context_compaction_contacts": 5,
    }


def test_the_harness_config_default_is_the_pre_e20_behaviour():
    config = _config(max_revisions=1, max_contacts=CEILING)
    assert config.context_fit_policy == "raise"
