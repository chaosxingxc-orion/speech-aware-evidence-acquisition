"""The SLURP native episode's finite-completion switch, flown against the fake model.

Item E13 (2026-09-19). The B7a recovery arm (run ``SAEA-SLURP-NATIVE-NCP-L1-
ANCHOR-TRAIN-FOLD-A-RECOVERY-V1``) aborted after 1,451 contacts because ONE
Reviewer completion reached the 512-token cap and the harness, under the
parser's default ``finite_completion_policy`` ``"raise"``, turned that row into
a flight abort. The repair is not new code -- ``deliver-latest-or-abstain`` has
been implemented since the A2T cells -- it is that the SLURP baselines never
declared the key.

This module proves the three things that claim owes, on the REAL anchor
baseline's ``native_episode`` block (``configs/baseline/
slurp-native-dual-store-train-fold-a-anchor-v1.json``) parsed by the
repository's own ``load_native_episode_config``, never a hand-written
stand-in:

1. **ON retains the row.** Reviewer visit 1 returns ``finish_reason``
   ``length`` at 512 completion tokens; the episode delivers the Solver's own
   draft, the receipt carries ``terminal_disposition.reason ==
   "finite_completion"`` with that finish reason and the interrupted Reviewer
   role, and the receipt validates through ``rails.native_episode_receipt``.
2. **OFF still aborts.** The same input with the key ABSENT raises
   ``NativeEpisodeError`` naming ``finish_reason is 'length'`` -- the exact
   September failure, reproduced.
3. **The key is not a request field.** With and without the key, on a clean
   (non-finite) wire, every composed request the Solver and the Reviewer send
   is byte-identical, so arming the key moves no model contact and changes
   only what the harness does with a completion the core already returned.

Zero model, tokenizer, encoder, network and GPU contacts; no
``SPEECHRL_DATA_DIR`` read. The "model" is the shared fake transport of
``test_native_episode_runner``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import test_native_episode_runner as fixtures
from test_native_episode_runner import _ActualEpisodeHarness
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401

from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    validate_native_episode_delivery_receipt,
    validate_native_episode_finite_path,
    validate_native_episode_terminal_policy,
)
from speech_aware_evidence_acquisition.reproduction.ojw.native_episode import (
    NativeEpisodeError,
)

#: The sealed SLURP TRAIN Fold A anchor: the OFF arm of every B cell, and the
#: fragment whose ``native_episode`` block the September cells inherited
#: WITHOUT ``finite_completion_policy``.
ANCHOR_RELPATH = "configs/baseline/slurp-native-dual-store-train-fold-a-anchor-v1.json"
SWITCH_KEY = "finite_completion_policy"
ARMED = "deliver-latest-or-abstain"

#: The anchor's own bounded graph ceiling (Perception 1 + 2 x (Solver 1 +
#: Reviewer 3 + Planner 1)); ``load_native_episode_config`` refuses a program
#: whose ``max_contacts`` is anything else, so this number is the config's, not
#: this test's.
ANCHOR_CEILING = 11
#: The serving geometry's completion cap, and therefore the completion-token
#: count a ``finish_reason`` ``length`` carries on this carrier.
OUTPUT_CAP_TOKENS = 512

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _anchor_values(*, armed: bool) -> dict:
    """The real anchor fragment, with the switch armed or absent."""

    values = json.loads((_REPO_ROOT / ANCHOR_RELPATH).read_text(encoding="utf-8"))
    episode = values["native_episode"]
    # The defect this item closes: the sealed SLURP baselines carry no such key.
    assert SWITCH_KEY not in episode, (
        f"{ANCHOR_RELPATH} already declares {SWITCH_KEY}; this test pins the "
        "sealed anchor's own shape and the arms it composes"
    )
    if armed:
        episode[SWITCH_KEY] = ARMED
    return values


def _anchor_config(program, *, armed: bool):
    return load_native_episode_config(_anchor_values(armed=armed), program)


def _finite_reviewer_wire(monkeypatch, *, sample_id: str = "s1") -> None:
    """Reviewer visit 1's authoritative completion stops at the output cap.

    The Reviewer's FIRST contact of that visit is the task-contract tool call
    (``_wire_tool_call``); the completion patched here is its second, the one
    the runner would otherwise accept as the review.
    """

    original = fixtures._wire_response

    def render(text: str) -> bytes:
        payload = json.loads(original(text))
        if text == f"reviewer-analysis:{sample_id}:visit:1":
            payload["choices"][0]["finish_reason"] = "length"
            payload["usage"]["completion_tokens"] = OUTPUT_CAP_TOKENS
        return json.dumps(payload, separators=(",", ":")).encode()

    monkeypatch.setattr(fixtures, "_wire_response", render)


def _slurp_harness(tmp_path, *, armed: bool) -> _ActualEpisodeHarness:
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=ANCHOR_CEILING,
        planner_actions=("ACCEPT",),
        reviewer_task_tool=True,
    )
    harness.config = _anchor_config(harness.program, armed=armed)
    return harness


def _cap_decoding() -> dict:
    return {"temperature": 0, "max_tokens": OUTPUT_CAP_TOKENS}


def _rendered_requests(harness) -> list[tuple[tuple, str]]:
    """Every composed request this flight prepared, keyed by its contact."""

    return sorted(
        (key, json.dumps(prepared["rendered"], sort_keys=True))
        for key, prepared in harness.prepared.items()
    )


def test_armed_key_retains_the_row_a_finite_reviewer_completion_would_abort(
    tmp_path, monkeypatch
):
    _finite_reviewer_wire(monkeypatch)
    harness = _slurp_harness(tmp_path, armed=True)
    assert harness.config.finite_completion_policy == ARMED
    try:
        summary = harness.run(decoding_params=_cap_decoding())
    finally:
        closed = harness.close()

    assert len(summary.results) == 1
    row = summary.results[0]
    receipt = row.native_episode_receipt

    disposition = receipt["terminal_disposition"]
    assert disposition["reason"] == "finite_completion"
    assert disposition["finish_reason"] == "length"
    assert disposition["stage"] == "review"
    assert disposition["planner_accepted"] is False
    assert "reviewer" in disposition["role_id"]

    # The interrupted role is the Reviewer, and its receipt keeps BOTH of that
    # visit's contacts -- the tool call and the completion that stopped.
    interrupted = receipt["interrupted_role"]
    assert interrupted["stage"] == "review"
    assert interrupted["role_id"] == disposition["role_id"]
    assert len(interrupted["execution_receipt"]["contacts"]) == 2
    assert (
        interrupted["execution_receipt"]["final_contact"]
        == disposition["rejected_contact"]
    )

    # The row is DELIVERED, and what it delivers is the Solver's own draft --
    # never the truncated Reviewer text.
    assert row.final_response_text == "solver-answer:s1:visit:1"
    assert "terminal_solver_receipt" in receipt
    assert "abstention_receipt" not in receipt
    assert "accepted_solver_receipt" not in receipt
    assert receipt["planner_routes"] == []
    assert [visit["stage"] for visit in receipt["role_visits"]] == [
        "perception",
        "solver",
    ]

    # Custody: the receipt validates through the repository's own reader, and
    # the terminal policy accepts it only BECAUSE the key is armed.
    delivery = validate_native_episode_delivery_receipt(receipt)
    assert delivery.kind == "finite"
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
        max_revisions=harness.config.max_revisions,
    )
    with pytest.raises(ValueError, match="configured"):
        validate_native_episode_terminal_policy(
            delivery,
            exhaustion_policy=harness.config.exhaustion_policy,
            finite_completion_policy="raise",
            max_revisions=harness.config.max_revisions,
        )

    # The completion that stopped really is a 512-token one, and its text never
    # becomes the delivered row.
    records = {record_id: payload for _, record_id, payload in harness.trace.records}
    rejected = disposition["rejected_contact"]
    response = records[f"{rejected['request_id']}/response"]
    assert response["usage"]["completion_tokens"] == OUTPUT_CAP_TOKENS
    assert response["text"] != row.final_response_text
    # Perception + Solver + Reviewer (tool call, then the finite completion).
    assert closed["request_count"] == 4


def test_absent_key_reproduces_the_september_flight_abort(tmp_path, monkeypatch):
    _finite_reviewer_wire(monkeypatch)
    harness = _slurp_harness(tmp_path, armed=False)
    # The parser's default, which is what every sealed SLURP baseline inherits.
    assert harness.config.finite_completion_policy == "raise"
    try:
        with pytest.raises(NativeEpisodeError, match=r"finish_reason is 'length'"):
            harness.run(decoding_params=_cap_decoding())
    finally:
        harness.close()


def test_the_key_renders_no_request_byte_on_either_arm(tmp_path):
    """ON and OFF compose the same Solver and Reviewer requests.

    ``finite_completion_policy`` is read only where a completion has already
    come back, so a clean flight cannot tell the two arms apart. Running both
    against a wire with no finite completion and comparing every prepared
    request is the falsifier for that claim.
    """

    prepared = {}
    for armed in (True, False):
        harness = _slurp_harness(tmp_path / ("on" if armed else "off"), armed=armed)
        try:
            summary = harness.run(decoding_params=_cap_decoding())
        finally:
            harness.close()
        assert summary.results[0].final_response_text == "solver-answer:s1:visit:1"
        prepared[armed] = _rendered_requests(harness)

    on, off = prepared[True], prepared[False]
    assert [key for key, _ in on] == [key for key, _ in off]
    roles = {key[1] for key, _ in on}
    assert {"solver", "reviewer"} <= roles
    assert on == off, "arming the key moved a composed request"

    # And the two configs really do differ in exactly that one leaf.
    armed_values = _anchor_values(armed=True)["native_episode"]
    plain_values = _anchor_values(armed=False)["native_episode"]
    assert set(armed_values) - set(plain_values) == {SWITCH_KEY}
    assert {
        key: value for key, value in armed_values.items() if key != SWITCH_KEY
    } == plain_values


def test_the_anchor_block_parses_on_both_arms_and_moves_nothing_else(tmp_path):
    harness = _slurp_harness(tmp_path, armed=False)
    try:
        armed = _anchor_config(harness.program, armed=True)
        plain = _anchor_config(harness.program, armed=False)
    finally:
        harness.close()
    assert armed.finite_completion_policy == ARMED
    assert plain.finite_completion_policy == "raise"
    fields = {
        name: getattr(armed, name)
        for name in armed.__dataclass_fields__
        if name != "finite_completion_policy"
    }
    assert fields == {
        name: getattr(plain, name)
        for name in plain.__dataclass_fields__
        if name != "finite_completion_policy"
    }
    assert armed.max_contacts == ANCHOR_CEILING
    assert armed.exhaustion_policy == "deliver-latest-solver"
    assert armed.role("reviewer").max_iterations == 3
