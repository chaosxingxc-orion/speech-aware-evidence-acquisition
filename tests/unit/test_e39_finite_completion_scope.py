"""Item E39: the finite-completion scope, per-role caps and the held dry run.

The E35 sub10 read (``docs/results/
2026-09-22-e21-native-window-e35-sub10-diagnosis.md``) found that item E13's
``deliver-latest-or-abstain`` is scoped to the WHOLE episode: 75 of 342
windows saw the Perception note hit the geometry's 1,024-token completion cap
on its FIRST contact, and the episode then ended with no Solver draft at all
and delivered the empty string. Those 76 empty windows hold 22.9 % of the
reference words and 95.6 % of the arm's extra error mass; scored like the
direct arm they move it from 0.2864 to 0.0778 corpus WER.

Item E39 scopes the rule to the node that ANSWERS. These proofs run the real
shared runner, the real six-node graph and the real request composer against
the fixture wire (``test_native_episode_runner``): zero model, tokenizer,
encoder, server, network and scorer contacts, and no utterance, reference or
delivered text anywhere.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

import test_native_episode_runner as fixtures
from test_native_episode_runner import _ActualEpisodeHarness
from test_native_finite_outcome_integration import _finite_wire
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401

from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    TRUNCATION_EVENTS,
    TRUNCATION_EVENTS_SCHEMA,
    validate_native_episode_truncation_scope,
)
from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import (
    NativeRoleNodeSpec,
)

_CHECKS = Path(__file__).resolve().parents[2] / "scripts" / "checks"
if str(_CHECKS) not in sys.path:
    sys.path.insert(0, str(_CHECKS))

import finite_completion_policy_check as gate  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
ARMED = "deliver-latest-or-abstain"
SCOPED = "answering-node"

#: The held dry-run cell item E39 prepares (root registers it).
E39_MODEL = "q4km-e21-native-window-packets-cddb000c-np4-max1024-v1"
E39_DATASET = "e21-native-window-four-row-v1"
E39_BASELINE = "e21-native-window-system-four-row-e39-v1"
E39_EXPERIMENT = "e21-native-window-four-row-e39-dry-run-v1"
PARENT_BASELINE = "e21-native-window-system-four-row-v1"
PARENT_EXPERIMENT = "e21-native-window-four-row-direct-vs-system-v1"


def _harness(tmp_path, **kwargs):
    """One tool-free four-contact episode: Perception, Solver, Reviewer,
    Planner, one ACCEPT, one row."""

    return _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=0,
        max_contacts=4,
        planner_actions=("ACCEPT",),
        **kwargs,
    )


def _armed(config, *, scope=SCOPED):
    return replace(
        config, finite_completion_policy=ARMED, finite_completion_scope=scope,
    )


# ---------------------------------------------------------------------------
# 1. ``episode`` -- today's behaviour, reproduced leaf by leaf.
# ---------------------------------------------------------------------------


def test_the_episode_scope_is_the_default_and_keeps_the_whole_episode_rule(
    tmp_path, monkeypatch,
):
    """A truncated Perception under the DEFAULT scope still voids the row.

    This is the E35 sub10 failure in one row, and it is what the existing E13
    proofs (``test_native_finite_outcome_integration``) assert at length. It
    is restated here so the two scopes are read side by side, and so the
    absence of the ``scope`` key on an ``"episode"`` disposition -- the
    byte-identity every sealed cell depends on -- is asserted by name.
    """

    _finite_wire(monkeypatch, "perception")
    harness = _harness(tmp_path)
    assert harness.config.finite_completion_scope == "episode"
    harness.config = replace(harness.config, finite_completion_policy=ARMED)
    try:
        summary = harness.run()
    finally:
        closed = harness.close()

    assert closed["request_count"] == 1
    row = summary.results[0]
    receipt = row.native_episode_receipt
    assert row.final_response_text == ""
    assert receipt["role_visits"] == []
    assert receipt["abstention_receipt"]["source_contact"]
    assert "terminal_solver_receipt" not in receipt
    assert TRUNCATION_EVENTS not in receipt
    disposition = receipt["terminal_disposition"]
    assert disposition["stage"] == "perception"
    assert "scope" not in disposition


# ---------------------------------------------------------------------------
# 2. ``answering-node`` -- the repair.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phase,stage,visit_index",
    [("perception", "perception", 0), ("reviewer", "review", 2)],
)
def test_a_truncated_auxiliary_node_keeps_its_text_and_the_solver_answers(
    tmp_path, monkeypatch, phase, stage, visit_index,
):
    """The whole point of item E39.

    Perception is the node the E35 sub10 arm lost 75 windows on: under
    ``answering-node`` its truncated note is kept, the Solver runs, and the
    row delivers the Solver's draft under an ordinary Planner ACCEPT. The
    Reviewer case is the one the flown arm already survived (30 windows), and
    it must keep surviving -- now without ending the episode at all.
    """

    _finite_wire(monkeypatch, phase)
    harness = _harness(tmp_path)
    harness.config = _armed(harness.config)
    try:
        summary = harness.run()
    finally:
        closed = harness.close()

    # Every node ran: nothing was cut short.
    assert closed["request_count"] == 4
    row = summary.results[0]
    receipt = row.native_episode_receipt
    assert row.final_response_text == "solver-answer:s1:visit:1"
    assert [visit["stage"] for visit in receipt["role_visits"]] == [
        "perception", "solver", "review", "planner",
    ]
    assert receipt["planner_routes"][-1]["action"] == "ACCEPT"
    # An ordinary accepted delivery: no terminal disposition, no abstention.
    assert receipt["accepted_solver_receipt"] is not None
    assert "terminal_disposition" not in receipt
    assert "abstention_receipt" not in receipt

    # The truncation is recorded, on the visit and in its own ordered list.
    visits = receipt["role_visits"]
    assert visits[visit_index]["truncated"] is True
    assert [index for index, visit in enumerate(visits) if visit.get("truncated")] == [
        visit_index
    ]
    block = receipt[TRUNCATION_EVENTS]
    assert block["schema"] == TRUNCATION_EVENTS_SCHEMA and block["count"] == 1
    event = block["events"][0]
    assert event["stage"] == stage
    assert event["role_visit_index"] == visit_index
    assert event["finish_reason"] == "length"
    assert event["role_id"] == visits[visit_index]["role_id"]
    assert event["contact"] == visits[visit_index]["execution_receipt"]["final_contact"]
    # Digests only: the event carries no text of any kind.
    assert set(event["contact"]) == {
        "agent_contact_id", "request_id", "request_sha256", "response_sha256",
        "response_text_sha256",
    }
    assert validate_native_episode_truncation_scope(
        receipt, finite_completion_scope=SCOPED,
    ) == (event,)


def test_a_truncated_solver_still_takes_the_e13_disposition(tmp_path, monkeypatch):
    """The answering node keeps item E13's rule, and says which rule it was."""

    _finite_wire(monkeypatch, "solver")
    harness = _harness(tmp_path)
    harness.config = _armed(harness.config)
    try:
        summary = harness.run()
    finally:
        closed = harness.close()

    assert closed["request_count"] == 2
    row = summary.results[0]
    receipt = row.native_episode_receipt
    assert row.final_response_text == ""
    assert [visit["stage"] for visit in receipt["role_visits"]] == ["perception"]
    assert receipt["abstention_receipt"]["source_contact"]
    disposition = receipt["terminal_disposition"]
    assert disposition["stage"] == "solver"
    assert disposition["reason"] == "finite_completion"
    # Item E39: WHICH scope rule ended the row.
    assert disposition["scope"] == SCOPED
    assert TRUNCATION_EVENTS not in receipt


def test_a_content_filter_stop_is_never_tolerated(tmp_path, monkeypatch):
    """Only ``length`` is a partial answer; a filtered stop is a refusal."""

    _finite_wire(monkeypatch, "perception", finish="content_filter")
    harness = _harness(tmp_path)
    harness.config = _armed(harness.config)
    try:
        summary = harness.run()
    finally:
        closed = harness.close()

    assert closed["request_count"] == 1
    receipt = summary.results[0].native_episode_receipt
    assert receipt["terminal_disposition"]["finish_reason"] == "content_filter"
    assert receipt["terminal_disposition"]["stage"] == "perception"
    assert TRUNCATION_EVENTS not in receipt


def test_the_answering_role_may_never_carry_the_node_level_tolerance():
    """Fail-closed: the Solver IS the answering node."""

    with pytest.raises(ValueError, match="answering Solver role"):
        NativeRoleNodeSpec(
            role_id="solver", role_kind="solver", prompt="p", max_iterations=1,
            tolerate_length_truncation=True,
        )
    assert NativeRoleNodeSpec(
        role_id="perception", role_kind="perception", prompt="p", max_iterations=1,
    ).tolerate_length_truncation is False


def test_a_truncation_block_is_refused_without_its_declared_scope():
    """The prospective-configuration rule items E13, E20 and E22 all take."""

    receipt = {
        "role_visits": [
            {
                "role_id": "perception",
                "stage": "perception",
                "truncated": True,
                "execution_receipt": {"contacts": [], "final_contact": {}},
            }
        ],
        TRUNCATION_EVENTS: {
            "schema": TRUNCATION_EVENTS_SCHEMA,
            "count": 1,
            "events": [
                {
                    "role_id": "perception",
                    "stage": "perception",
                    "role_visit_index": 0,
                    "revision_count": 0,
                    "finish_reason": "length",
                    "contact": {
                        "agent_contact_id": "c1",
                        "request_id": "r1",
                        "request_sha256": "a" * 64,
                        "response_sha256": "b" * 64,
                        "response_text_sha256": "c" * 64,
                    },
                }
            ],
        },
    }
    with pytest.raises(ValueError, match="without its declared scope"):
        validate_native_episode_truncation_scope(
            receipt, finite_completion_scope="episode",
        )
    assert len(
        validate_native_episode_truncation_scope(
            receipt, finite_completion_scope=SCOPED,
        )
    ) == 1

    # A visit marked truncated with no event of its own is refused too.
    orphaned = json.loads(json.dumps(receipt))
    orphaned["role_visits"].append(
        {
            "role_id": "reviewer",
            "stage": "review",
            "truncated": True,
            "execution_receipt": {"contacts": [], "final_contact": {}},
        }
    )
    with pytest.raises(ValueError, match="no length truncation event"):
        validate_native_episode_truncation_scope(
            orphaned, finite_completion_scope=SCOPED,
        )

    # The answering stage can never claim one.
    answering = json.loads(json.dumps(receipt))
    answering["role_visits"][0]["stage"] = "solver"
    answering[TRUNCATION_EVENTS]["events"][0]["stage"] = "solver"
    with pytest.raises(ValueError, match="inadmissible stage"):
        validate_native_episode_truncation_scope(
            answering, finite_completion_scope=SCOPED,
        )


# ---------------------------------------------------------------------------
# 3. The per-role completion cap.
# ---------------------------------------------------------------------------


def test_a_per_role_cap_narrows_exactly_one_role_s_requests(tmp_path):
    """The cap is composed at request time, for that role's contacts only."""

    harness = _harness(tmp_path)
    harness.config = replace(
        harness.config,
        roles=tuple(
            replace(role, max_completion_tokens=32)
            if role.role_kind == "reviewer" else role
            for role in harness.config.roles
        ),
    )
    assert harness.config.role_completion_caps == {"reviewer": 32}

    seen: dict[str, list[object]] = {}
    original_gate = harness.request_gate

    def gate(prepared_request):
        payload = prepared_request.as_payload()
        original_gate(prepared_request)
        rendered = harness.transport.render_request(prepared_request.payload_bytes)
        _sample_id, phase, _visit = harness._material_key(rendered)
        seen.setdefault(phase, []).append(payload["decoding_params"].get("max_tokens"))

    harness.request_gate = gate
    try:
        summary = harness.run()
    finally:
        closed = harness.close()

    assert closed["request_count"] == 4
    assert summary.results[0].final_response_text == "solver-answer:s1:visit:1"
    # The fixture's own geometry is 64; only the Reviewer's request narrows.
    assert seen == {
        "perception": [64], "solver": [64], "reviewer": [32], "planner": [64],
    }


def test_the_loader_bounds_a_cap_by_the_serving_geometry():
    """A cap wider than the geometry can never bind, so it is refused."""

    composed = compose(REPO, E39_MODEL, E39_DATASET, E39_BASELINE, E39_EXPERIMENT)
    program = default_phase_program(composed.values["policy"])
    values = json.loads(json.dumps(composed.values))
    assert values["serving_geometry"]["max_tokens"] == 1024

    values["native_episode"]["roles"]["perception"]["max_completion_tokens"] = 1024
    assert load_native_episode_config(values, program).role_completion_caps[
        "perception"
    ] == 1024

    values["native_episode"]["roles"]["perception"]["max_completion_tokens"] = 1025
    with pytest.raises(ValueError, match="must not exceed the serving"):
        load_native_episode_config(values, program)

    values["native_episode"]["roles"]["perception"]["max_completion_tokens"] = 0
    with pytest.raises(ValueError, match="must be a positive integer"):
        load_native_episode_config(values, program)

    values["native_episode"]["roles"]["perception"]["max_completion_tokens"] = 320
    values.pop("serving_geometry")
    values.pop("decoding_params")
    with pytest.raises(ValueError, match="requires a declared"):
        load_native_episode_config(values, program)


def test_the_loader_refuses_a_scope_outside_the_enum():
    composed = compose(REPO, E39_MODEL, E39_DATASET, E39_BASELINE, E39_EXPERIMENT)
    program = default_phase_program(composed.values["policy"])
    values = json.loads(json.dumps(composed.values))
    values["native_episode"]["finite_completion_scope"] = "role"
    with pytest.raises(ValueError, match="finite completion scope is invalid"):
        load_native_episode_config(values, program)


# ---------------------------------------------------------------------------
# 4. The held dry-run fragments.
# ---------------------------------------------------------------------------


def test_the_held_e39_fragments_compose_and_move_exactly_three_leaves():
    composed = compose(REPO, E39_MODEL, E39_DATASET, E39_BASELINE, E39_EXPERIMENT)
    program = default_phase_program(composed.values["policy"])
    config = load_native_episode_config(composed.values, program)

    assert config.finite_completion_policy == ARMED
    assert config.react_exhaustion_policy == "continue-without-answer"
    assert config.finite_completion_scope == SCOPED
    assert config.role_completion_caps == {"perception": 320, "reviewer": 384}
    # Both caps sit inside the serving geometry's own output cap.
    assert max(config.role_completion_caps.values()) < 1024

    parent = compose(REPO, E39_MODEL, E39_DATASET, PARENT_BASELINE, PARENT_EXPERIMENT)
    parent_config = load_native_episode_config(
        parent.values, default_phase_program(parent.values["policy"])
    )
    # The parent is untouched: it still composes the pre-E39 episode.
    assert parent_config.finite_completion_scope == "episode"
    assert parent_config.role_completion_caps == {}
    assert config.max_contacts == parent_config.max_contacts

    # Exactly three leaves move in the baseline's own episode/material block,
    # and every pinned artifact is the parent's (they are roster-bound, not
    # run-bound).
    child = json.loads(
        (REPO / "configs/baseline" / f"{E39_BASELINE}.json").read_text(
            encoding="utf-8"
        )
    )
    parent_doc = json.loads(
        (REPO / "configs/baseline" / f"{PARENT_BASELINE}.json").read_text(
            encoding="utf-8"
        )
    )
    for key in ("prepared_execution_units", "prepared_window_feature_packets",
                "knowledge_snapshot_relpath", "knowledge_snapshot_sha256"):
        assert child[key] == parent_doc[key]
    assert child["phase_material"]["reviewer"]["instruction_template"] == (
        "probes/e21_native_window_system_reviewer_v2.txt"
    )
    assert child["readiness"]["state"] == "held"

    probe = (REPO / "configs/probes/e21_native_window_system_reviewer_v2.txt").read_text(
        encoding="utf-8"
    )
    assert "tool" not in probe.lower()
    assert "300 words" in probe


def test_the_finite_completion_gate_reports_the_held_cell_s_posture():
    """The gate passes, and the new keys are reported rather than required."""

    data = gate.evaluate(REPO)
    assert data["passed"], data["violations"]
    assert data["finite_completion_scopes"] == ["episode", "answering-node"]
    # Every reported cell names a scope the enum admits.
    for row in data["scope_report"]:
        assert row[gate.SCOPE_KEY] in gate.SCOPE_VALUES

    # Rule 3 refuses a third value, wherever it is declared.
    baseline = json.loads(
        (REPO / "configs/baseline" / f"{E39_BASELINE}.json").read_text(
            encoding="utf-8"
        )
    )
    assert baseline["native_episode"][gate.SCOPE_KEY] == SCOPED
    assert baseline["native_episode"]["roles"]["perception"][gate.ROLE_CAP_KEY] == 320
    assert baseline["native_episode"]["roles"]["reviewer"][gate.ROLE_CAP_KEY] == 384
