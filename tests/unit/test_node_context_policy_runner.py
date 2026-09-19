"""E8a: the Node Context Policy through the PRODUCTION render path.

Every episode here runs the real OpenJiuwen role graph, the real
``rails.runner`` and the real ``LlamaServerTransport.render_request`` over the
shared fake transport. No model, no tokenizer, no server, no run directory.

The L0 falsifier (design section 10) is the point of the first three tests:
with the key absent, with the literal ``"raw"`` and with an all-raw object,
every rendered request is BYTE-IDENTICAL to the pre-change render, pinned below
from master ``716c5e27`` before any line of E8a existed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import fragment_hash
from speech_aware_evidence_acquisition.rails.config_tables import (
    EPISODE_LEVEL_SWITCH_KEYS,
    is_episode_null_arm,
    resolve_episode_switch_key,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    is_illegal_planner_route,
)
from speech_aware_evidence_acquisition.rails.node_context_binding import (
    validate_node_context_policy_config,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness
from test_node_context_policy import DRAFT_SCHEMA, LEGAL_ENTITY_TYPES
from test_role_context_binding import perception_format
from test_role_context_runner import _configure_typed_context

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Byte-identity pins.
#
# Captured from the PRE-CHANGE tree (master 716c5e27, before
# rails/node_context_policy.py existed) with the production render path --
# exactly the bytes ``_ActualEpisodeHarness.request_gate`` admits -- and the
# production transition objects. If any of these move, the change stopped
# being an OFF-arm-identical change. Captured the way E3c captured its own
# (``tests/unit/test_phase_supply_repeat_visit.py``).
# ---------------------------------------------------------------------------

#: The full-shape episode: perception -> solver -> reviewer(tool) -> planner
#: -> solver -> reviewer -> planner, with a task-contract tool call.
ANCHOR_REQUEST_SHA256 = {
    "perception/1/1": "5beb1c332b821c6ad3cb737d1ee745fec34ae75a2a737da13121f538ce660dc0",
    "solver/1/1": "3fbdc4a5ad57bc2ddf9792eec9e9c4ed2e3ca56b6ea7404e7f6e6498973c4e3b",
    "reviewer/1/1": "4afc771211d363c7a235f571a8cf8e2a851990dfbd60925bc0f4b77d3d295812",
    "reviewer/1/2": "a0422abf879caa31c9249777396aad50377c6c92dc14d7abbbf54447ad9c0c00",
    "planner/1/1": "6ed5c35229876296574ff2f693742c479d042c9d9ac8961745c2106e363fa1f7",
    "solver/2/1": "e8a27711c38411e75bdb203d821d8ae9f45dfa9e5095ad00934461837bcbeaa5",
    "reviewer/2/1": "88342fc1e1492d29e898850f3f0c1872024066485dbd436bc8252b113b429cf8",
    "planner/2/1": "2c31940ad171d4c0705022f936748817b22f71b554061628587e2a93fdf9f074",
}
ANCHOR_TRANSITION_SHA256 = (
    "3138a1e283ad1c252e890cfbd954f9f095ed941787be9c510d00b8f3755a992e",
    "ce2e5ea07a326aa28be49c4e04aa7306779265a9d271c2e838f680047afc89fa",
    "514e825d308c092170218ec1cde5326dc95a1f1f13166b9febafb097446b4766",
    "3cf88bf373c87ea740331ea7d88b51a69608dba442026c59493cd57c336c05ae",
    "70fa5090cb09845240e1a5358c1ad74570ef9b22809f7f74c91239443c924fc4",
    "4d24a5e774f9573b8c88ad8d49a5d0b1d9aff62b8f2f5fc0c5846505dac3f659",
    "c4ff80fc304709ef37ec930637399caf2b1b83568488bc570ec615a0942fb9e5",
    "4bc57f881a66beab87951847a4c1318fc0725cbc3674ae0c3b49a69866c457aa",
    "43333e7bce3b520c1c81eaf655eb45339c1be730a369ecb02896b50239a361d6",
)

#: The same episode with the PRE-EXISTING typed role context switched on. E8a
#: folds ``native_episode.role_context`` under the new key but leaves the old
#: block's own path working unchanged, and these pins are what "unchanged"
#: means.
TYPED_ROLE_CONTEXT_REQUEST_SHA256 = {
    "perception/1/1": "bf4408cb8433e2bd32da430599d4345cc5baaf0e6f6d750185dff08cd2cf4ab7",
    "solver/1/1": "d1bd7cfafc301ba58c551ee09274130a275867bf4c67955c9cda4f01c371120a",
    "reviewer/1/1": "becbe1f8bdccd9c9772db6e7b0ddcc011fbce4cf0ebc7d43e28acae24417f0d6",
    "reviewer/1/2": "e0d2f33a7bead1aafad8a700d29e9b0fbd676acab0f70e192db593baef92aa0f",
    "planner/1/1": "b82a0aca286269cdcca6a44c2c8505fc80c83edf0df277ce2e763ea794f84695",
    "solver/2/1": "c1e2f98474e6ee81dab8c33d4dc63f2e212bdbf925fbb73d6be6baaca582bfc9",
    "reviewer/2/1": "a0060cce367e55d34e98f3970305fd7ce747b4a57c1cca1da12ca2f3680d4574",
    "planner/2/1": "2b27852ad0079ea5b76e02c5501632e8ecbb35e537dc81aa2807a34ee4a9b85c",
}

#: The composed hash of the sealed anchor baseline fragment, captured on the
#: same pre-change tree. E8a adds no config key to it and must not move it.
ANCHOR_FRAGMENT_SHA256 = (
    "96e75ab3d3da29e3f94a823e5a7a0f01c588a3b43f2ef876ec857429c6e8bc1a"
)
ANCHOR_FRAGMENT = "slurp-native-dual-store-train-fold-a-anchor-v1"


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


CANDIDATES = _json({"candidates": [
    {"intent_id": "alarm_set", "distinction": "The command may create an alarm.",
     "evidence_refs": [], "unresolved_fields": []},
    {"intent_id": "alarm_remove", "distinction": "The command may remove an alarm.",
     "evidence_refs": [], "unresolved_fields": []},
]})
FIRST_DRAFT = _json({"scenario": "alarm", "action": "remove",
                     "entities": [{"type": "time", "filler": "seven"}]})
REVISED_DRAFT = _json({"scenario": "alarm", "action": "set",
                       "entities": [{"type": "time", "filler": "seven"}]})
PROSE_REVIEW = "The draft looks plausible; the time slot reading is ambiguous."


def _anchor_outputs(harness):
    """The exact synthetic episode the pins above were captured over."""

    def output(key):
        _sample_id, phase, visit, turn = key
        if harness.reviewer_tool and phase == "reviewer" and visit == turn == 1:
            return None
        if phase == "perception":
            return CANDIDATES
        if phase == "solver":
            return FIRST_DRAFT if visit == 1 else REVISED_DRAFT
        if phase == "reviewer":
            return PROSE_REVIEW
        if phase == "planner":
            return harness.planner_actions[visit - 1]
        raise AssertionError(phase)

    return output


def _policy_document(level="structured", boundaries=None, producers=None):
    document = {
        "level": level,
        "policy_id": "typed-slurp-node-context-v1",
        "params": {
            "max_candidates": 3,
            "projection_policy": (
                "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"
            ),
            "draft_response_schema": json.loads(json.dumps(DRAFT_SCHEMA)),
            "legal_entity_types": list(LEGAL_ENTITY_TYPES),
        },
    }
    if boundaries is not None:
        document["boundaries"] = boundaries
    if producers is not None:
        document["producers"] = producers
    return document


def _episode(tmp_path, *, policy=None, typed=False, sample_count=1):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=sample_count,
        max_revisions=1,
        max_contacts=9,
        planner_actions=("REVISE", "ACCEPT"),
        reviewer_task_tool=True,
    )
    if typed:
        _configure_typed_context(harness)
    else:
        harness._output = _anchor_outputs(harness)
    if policy is not None:
        harness.repo_root = REPO_ROOT
        harness.config = replace(
            harness.config,
            context_policy_json=validate_node_context_policy_config(policy),
        )
        if not isinstance(policy, str) and policy.get("level") != "raw":
            harness.program = replace(
                harness.program,
                phases=tuple(
                    replace(phase, response_format_id="slurp-intent-hypotheses-v1")
                    if phase.name == "perception" else phase
                    for phase in harness.program.phases
                ),
            ).validate()
            original = harness.material_for_phase

            def material_for_phase(phase, context, sealed):
                material = original(phase, context, sealed)
                if phase == "perception":
                    return replace(
                        material, response_format=perception_format()
                    ).validate()
                return material

            harness.material_for_phase = material_for_phase
    try:
        summary = harness.run()
    finally:
        harness.close()
    return harness, summary


def _request_digests(harness):
    return {
        f"{phase}/{visit}/{turn}": hashlib.sha256(
            json.dumps(
                prepared["rendered"], sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
        for (_sample, phase, visit, turn), prepared in harness.prepared.items()
    }


def _transition_digests(summary):
    return tuple(
        transition.content_hash() for transition in summary.results[0].transitions
    )


def _wire_chars(rendered):
    """Every character the model would actually read: the system message plus
    every text part of the user turn, plus every replayed tool message."""

    total = 0
    for message in rendered["messages"]:
        content = message.get("content")
        if isinstance(content, str):
            total += len(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    total += len(part["text"])
    return total


# ---------------------------------------------------------------------------
# (a) L0 falsifier
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_l0_with_the_key_absent_renders_the_pinned_pre_change_bytes(tmp_path):
    harness, summary = _episode(tmp_path)
    assert _request_digests(harness) == ANCHOR_REQUEST_SHA256
    assert _transition_digests(summary) == ANCHOR_TRANSITION_SHA256
    receipt = summary.results[0].native_episode_receipt
    assert "node_context_policy_compilations" not in receipt


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize(
    "policy",
    [
        "raw",
        {"level": "raw"},
        {"level": "raw", "boundaries": {"planner:review-finding": {"level": "raw"}}},
    ],
    ids=["string-raw", "object-raw", "object-raw-with-override"],
)
def test_l0_declared_raw_renders_the_same_bytes_and_adds_only_receipt_rows(
    tmp_path, policy
):
    """The declared OFF arm: identical request bytes, identical transitions,
    and a receipt whose ONLY difference is the added policy rows -- every one
    of them a ``level: "raw"`` row whose ``rendered_sha256`` equals its
    source's ``content_sha256``."""

    harness, summary = _episode(tmp_path, policy=policy)
    assert _request_digests(harness) == ANCHOR_REQUEST_SHA256
    assert _transition_digests(summary) == ANCHOR_TRANSITION_SHA256

    receipt = summary.results[0].native_episode_receipt
    rows = receipt["node_context_policy_compilations"]
    assert len(rows) == len(summary.results[0].contacts) == 8
    assert set(receipt) - {"node_context_policy_compilations"} == {
        "role_visits", "planner_routes", "accepted_solver_receipt",
    }
    boundary_rows = [
        row for record in rows for row in record["compilation"]["boundaries"]
    ]
    assert boundary_rows
    for row in boundary_rows:
        assert row["level"] == "raw"
        assert row["rendered_sha256"] == row["source"]["content_sha256"]
        assert row["rendered_state_id"] == row["source"]["state_id"]
        assert row["template_id"] is None and row["parser_id"] is None
    for record in rows:
        traced = harness.traced_contact(record["contact_id"])
        assert record["request_sha256"] == traced["request_sha256"]
        assert record["response_sha256"] == traced["response_sha256"]
        assert record["template_sha256s"] == {}
    org = [
        payload["org_node_context_policy"]
        for channel, record_id, payload in harness.trace.records
        if channel == "ORG" and record_id.endswith("/node-context-policy")
    ]
    assert org == rows


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_e15_an_acquire_planner_output_keeps_the_anchor_request_bytes(tmp_path):
    """E15 (finding I-1 of the 2026-09-19 base-lock draft), through the
    PRODUCTION render path.

    The anchor episode above, with one word changed in the Planner's own
    RESPONSE: ``ACQUIRE`` instead of ``REVISE``.  No SLURP episode is built
    with an acquisition node, so before E15 that word raised
    ``NativeEpisodeError`` inside the graph and took the flight with it.  Two
    claims here:

    * every request the harness admitted up to and including that Planner
      contact is byte-identical to the pins captured on the pre-change tree --
      E15 moves no request byte, and the Planner prompt (which never
      advertised ``ACQUIRE``) is untouched;
    * the row is RETAINED: it delivers the committed first draft, its final
      route carries the E8c disposition, and the receipt counts it.
    """

    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=9,
        planner_actions=("ACQUIRE",),
        reviewer_task_tool=True,
    )
    harness._output = _anchor_outputs(harness)
    try:
        summary = harness.run()
    finally:
        harness.close()

    # The episode stops at the first Planner, so it makes the anchor's first
    # five requests and no more -- each one byte-for-byte the pinned bytes.
    prefix = ("perception/1/1", "solver/1/1", "reviewer/1/1", "reviewer/1/2",
              "planner/1/1")
    assert _request_digests(harness) == {
        key: ANCHOR_REQUEST_SHA256[key] for key in prefix
    }

    result = summary.results[0]
    assert result.final_response_text == FIRST_DRAFT
    receipt = result.native_episode_receipt
    route = receipt["planner_routes"][-1]
    assert is_illegal_planner_route(route)
    assert route["action"] == "ACQUIRE"
    assert route["revision_count"] == 0
    assert receipt["planner_action_illegal"]["count"] == 1
    assert receipt["planner_action_illegal"]["action_sha256"] == [
        hashlib.sha256(b"ACQUIRE").hexdigest()
    ]
    assert "accepted_solver_receipt" in receipt
    assert "terminal_disposition" not in receipt


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_pre_existing_typed_role_context_path_is_unchanged(tmp_path):
    """E8a folds ``role_context`` under the new key without touching the old
    block's own code path: the 2026-09-16 typed-context arm still renders the
    bytes it rendered before E8a."""

    harness, _summary = _episode(tmp_path, typed=True)
    assert _request_digests(harness) == TYPED_ROLE_CONTEXT_REQUEST_SHA256


def test_the_sealed_anchor_fragment_hash_is_unchanged():
    fragment = json.loads(
        (REPO_ROOT / "configs" / "baseline" / f"{ANCHOR_FRAGMENT}.json").read_text(
            encoding="utf-8"
        )
    )
    assert "context_policy" not in fragment["native_episode"]
    assert fragment_hash(fragment) == ANCHOR_FRAGMENT_SHA256


# ---------------------------------------------------------------------------
# (b) L1 through the production render path
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_l1_reaches_the_actual_requests_and_is_byte_stable(tmp_path):
    first_harness, first_summary = _episode(
        tmp_path / "one", policy=_policy_document()
    )
    second_harness, _second = _episode(tmp_path / "two", policy=_policy_document())
    assert _request_digests(first_harness) == _request_digests(second_harness)
    assert _request_digests(first_harness) != ANCHOR_REQUEST_SHA256
    # Custody is untouched: the canonical ledger still holds the raw model text.
    raw = {state.content for state in first_summary.results[0].agent_states}
    assert CANDIDATES in raw and FIRST_DRAFT in raw and PROSE_REVIEW in raw
    assert all(
        not state.state_kind.startswith("node-context:")
        for state in first_summary.results[0].agent_states
    )
    body = json.dumps(
        first_harness.prepared[("s1", "planner", 1, 1)]["rendered"], sort_keys=True
    )
    assert "DECISION BRIEF" in body
    assert "HARNESS CHECKS" in body
    assert "REVIEW OF THE CURRENT DRAFT (Reviewer, UNPARSED)" in body
    # The design's boundary table has no (planner, candidate-hypothesis) entry,
    # so the Planner keeps the raw Perception state and its row says why.
    assert "PERCEPTION CANDIDATES" not in body
    assert "kind=phase:perception" in body
    reviewer_body = json.dumps(
        first_harness.prepared[("s1", "reviewer", 1, 1)]["rendered"], sort_keys=True
    )
    assert "PERCEPTION CANDIDATES (2 of at most 3" in reviewer_body
    assert "DRAFT UNDER REVIEW (Solver, parsed)" in reviewer_body
    assert "among the Perception candidates" in reviewer_body
    solver_two = json.dumps(
        first_harness.prepared[("s1", "solver", 2, 1)]["rendered"], sort_keys=True
    )
    assert "YOUR PREVIOUS ANSWER (revision 1 of 1, parsed)" in solver_two
    assert "PLANNER DECISION: REVISE" in solver_two


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_l1_receipts_bind_every_boundary_to_its_template_and_source(tmp_path):
    harness, summary = _episode(tmp_path, policy=_policy_document())
    rows = summary.results[0].native_episode_receipt[
        "node_context_policy_compilations"
    ]
    assert len(rows) == 8
    seen = set()
    for record in rows:
        compilation = record["compilation"]
        assert compilation["schema"] == "saea-node-context-policy-compilation-v1"
        assert len(compilation["receipt_sha256"]) == 64
        for row in compilation["boundaries"]:
            seen.add(row["boundary"]["boundary_id"])
            assert row["schema"] == "saea-node-context-policy-v1"
            assert row["cleaning_contact"] is None
            if row["level"] == "structured":
                assert row["template_sha256"] == hashlib.sha256(
                    (REPO_ROOT / "configs" / row["template_id"]).read_bytes()
                ).hexdigest()
                assert row["source"]["source_response_sha256"]
            else:
                assert row["rendered_sha256"] == row["source"]["content_sha256"]
    assert {
        "B-CAND-SOL", "B-CAND-REV", "B-DRAFT-REV", "B-DRAFT-PLAN", "B-DRAFT-SOL",
        "B-REVIEW-PLAN", "B-REVIEW-SOL", "B-PLAN-SOL",
    } <= seen


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_replayed_tool_observation_drops_the_duplicated_contract(tmp_path):
    """(e) through the wire: the Planner's replayed task-contract observation
    references the contract its own system message already carries."""

    harness, summary = _episode(tmp_path, policy=_policy_document())
    planner = harness.prepared[("s1", "planner", 1, 1)]["rendered"]
    tool_messages = [
        message for message in planner["messages"] if message.get("role") == "tool"
    ]
    assert len(tool_messages) == 1
    contract = json.loads(tool_messages[0]["content"])["result"]["task_contract"]
    assert "saea-tool-task-contract-v1" in contract
    assert "task-contract-for-s1" not in contract
    assert planner["messages"][0]["content"].count("task-contract-for-s1") >= 1
    # The Reviewer's own live chain is untouched: its second iteration still
    # replays the sealed observation the framework verifies.
    reviewer = harness.prepared[("s1", "reviewer", 1, 2)]["rendered"]
    live = [
        message for message in reviewer["messages"] if message.get("role") == "tool"
    ]
    assert json.loads(live[0]["content"])["result"] == {
        "task_contract": "task-contract-for-s1"
    }
    rows = [
        row
        for record in summary.results[0].native_episode_receipt[
            "node_context_policy_compilations"
        ]
        for row in record["compilation"]["boundaries"]
        if row["boundary"]["semantic_class"] == "tool-observation"
    ]
    assert {row["raw_reason"] for row in rows} == {None, "live-tool-chain"}


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_l1_prompt_volume_delta_on_four_smoke_rows(tmp_path, capsys):
    """The model-free prompt-volume read the cell registration needs: four
    rows, the same synthetic outputs, L0 against L1 through the production
    renderer."""

    base_harness, _base = _episode(tmp_path / "l0", sample_count=4)
    l1_harness, _l1 = _episode(
        tmp_path / "l1", policy=_policy_document(), sample_count=4
    )
    base = {
        key: _wire_chars(prepared["rendered"])
        for key, prepared in base_harness.prepared.items()
    }
    live = {
        key: _wire_chars(prepared["rendered"])
        for key, prepared in l1_harness.prepared.items()
    }
    assert set(base) == set(live)
    deltas = {key: live[key] - base[key] for key in sorted(base)}
    with capsys.disabled():
        print("\nNCP L1 prompt-volume delta, four smoke rows (wire characters):")
        for key in sorted(deltas):
            print(f"  {key}: {base[key]} -> {live[key]} ({deltas[key]:+d})")
        print(
            f"  total: {sum(base.values())} -> {sum(live.values())} "
            f"({sum(deltas.values()):+d}, "
            f"{100.0 * sum(deltas.values()) / sum(base.values()):+.2f} %)"
        )
    # Bounded and additive, as design section 8 requires of L1.
    assert all(delta < 2000 for delta in deltas.values())


# ---------------------------------------------------------------------------
# (f) the config surface
# ---------------------------------------------------------------------------


def test_the_switch_key_resolves_in_the_episode_class():
    assert "native_episode.context_policy" in EPISODE_LEVEL_SWITCH_KEYS
    assert (
        resolve_episode_switch_key("native_episode.context_policy")
        == "native_episode.context_policy"
    )
    assert is_episode_null_arm("native_episode.context_policy", None) is True
    assert is_episode_null_arm("native_episode.context_policy", "raw") is True
    assert is_episode_null_arm(
        "native_episode.context_policy", {"level": "raw"}
    ) is True
    assert is_episode_null_arm(
        "native_episode.context_policy", {"level": "structured"}
    ) is False


def test_role_context_and_context_policy_together_are_refused():
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )
    from test_native_episode_config import config
    from test_role_context_binding import context_program, context_spec

    values = config()
    values["native_episode"]["role_context"] = context_spec()
    values["native_episode"]["context_policy"] = "raw"
    with pytest.raises(ValueError, match="folded under context_policy"):
        load_native_episode_config(values, context_program())


def test_a_declared_policy_records_its_canonical_text_and_the_off_arm_still_binds():
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )
    from test_native_episode_config import config, program
    from test_role_context_binding import context_program

    assert load_native_episode_config(config(), program()).context_policy_json is None

    off = config()
    off["native_episode"]["context_policy"] = "raw"
    loaded = load_native_episode_config(off, program())
    assert loaded.context_policy_json == '"raw"'

    on = config()
    on["native_episode"]["context_policy"] = _policy_document()
    loaded_on = load_native_episode_config(on, context_program())
    assert json.loads(loaded_on.context_policy_json)["level"] == "structured"

    # An untyped Perception phase cannot carry a structured policy.
    with pytest.raises(ValueError, match="Perception"):
        load_native_episode_config(on, program())


def test_a_declared_producer_format_must_match_the_producing_phase():
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )
    from test_native_episode_config import config
    from test_role_context_binding import context_program

    values = config()
    values["native_episode"]["context_policy"] = _policy_document(
        producers={"review-finding": {"response_format_id": "saea-review-findings-v1"}}
    )
    with pytest.raises(ValueError, match="review-finding|reviewer producer"):
        load_native_episode_config(values, context_program())

    typed_reviewer = replace(
        context_program(),
        phases=tuple(
            replace(phase, response_format_id="saea-review-findings-v1")
            if phase.name == "reviewer" else phase
            for phase in context_program().phases
        ),
    )
    loaded = load_native_episode_config(values, typed_reviewer)
    assert json.loads(loaded.context_policy_json)["producers"] == {
        "review-finding": {"response_format_id": "saea-review-findings-v1"}
    }
