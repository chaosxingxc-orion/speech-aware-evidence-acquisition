"""E8b: the Node Context Policy at level L2 through the PRODUCTION render path.

Every episode here runs the real OpenJiuwen role graph, the real
``rails.runner``, the real ``MeteredNativeSpeechRequest`` composition and the
real ``LlamaServerTransport.render_request`` over the shared fake transport.
No model, no tokenizer, no server, no run directory: the frozen core is the
same scripted fake transport every other episode proof uses, and the cleaning
contact reaches it through the same metered path a role contact does.

Design: ``docs/superpowers/specs/2026-09-17-node-context-policy-design.md``
sections 3 (L2), 7 (the ceiling arithmetic), 9 (receipts) and 10.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.node_context_binding import (
    validate_node_context_policy_config,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness
from test_node_context_policy import DRAFT_SCHEMA, LEGAL_ENTITY_TYPES
from test_node_context_policy_l2 import (
    CLEANED_BOUNDARY,
    CLEANING_INSTRUCTION_TEMPLATE,
    CLEANING_INSTRUCTION_TEMPLATE_SHA256,
    CLEANING_RENDER_TEMPLATE_SHA256,
    VALID_CLEANED,
    _INVALID_CLEANINGS,
)
from test_node_context_policy_runner import (
    ANCHOR_REQUEST_SHA256,
    PROSE_REVIEW,
    REPO_ROOT,
    _anchor_outputs,
    _policy_document,
    _request_digests,
)
from test_role_context_binding import perception_format

# ---------------------------------------------------------------------------
# E8a's L1 byte-identity pin.
#
# Captured on master bc9763bd -- E8a merged, before one line of E8b existed --
# with the same production render path this module uses. L2 changes the
# boundary it is declared on and nothing else, so an L1 policy must still
# render exactly these bytes. (E8a's own L0 pin, ANCHOR_REQUEST_SHA256, is
# imported above and re-asserted here for the same reason.)
# ---------------------------------------------------------------------------

L1_REQUEST_SHA256 = {
    "perception/1/1": "bf4408cb8433e2bd32da430599d4345cc5baaf0e6f6d750185dff08cd2cf4ab7",
    "solver/1/1": "f541cf748e21b16e863560b6a295e18a2e0127cb3297738faba4ba3a8a40f314",
    "reviewer/1/1": "4b14d93e384151dbc971e82aa460f30196847541ec1beddf9b28ef31f44d34a6",
    "reviewer/1/2": "3025fdd7861b9d4746272c3ee582627cc09d0f26f0390b4fed32c08043ba20fc",
    "planner/1/1": "e665e7b38412ea372ed869b12111e28d76b678865db9a1c0937c1f63eeafb368",
    "solver/2/1": "ea0675db5164d843406cb6906071a7b6722cd05ca59366384a215e6787d46856",
    "reviewer/2/1": "05ead7ac29ecb2262c372aa7a5dfbf9113e5cb8bca1b4f4a7da27c6a996ebc1a",
    "planner/2/1": "a33dc36837b77fd418ad30c8c6dc989693883b7082c7a83612a1b0891732af35",
}

#: The harness episode's shape is perception 1, solver 1, reviewer 2, planner 1
#: with one revision, so its bounded ceiling is 1 + 2 * 4 = 9. One cleaning
#: boundary on the one-iteration Planner adds (max_revisions + 1) = 2.
HARNESS_L1_CEILING = 9
HARNESS_L2_CEILING = 11

#: The first line of the committed cleaning instruction's material section --
#: the marker that tells this harness a prepared request is a cleaning contact
#: rather than a phase visit, because a cleaning contact carries no phase
#: material at all.
CLEANING_MARKER = "REVIEWER COMMENTARY, AS THE HARNESS PREPARED IT:"


class _CleaningHarness(_ActualEpisodeHarness):
    """The shared production harness, taught the ONE thing L2 adds.

    A cleaning contact's instruction is the committed template plus the L1
    material -- never a phase's ``PhaseMaterial`` -- so it carries none of the
    per-visit markers ``_material_key`` matches on. Everything else (the fit
    gate, the slot, the dispatch bookkeeping, the trace) is the base class's.
    """

    def request_gate(self, prepared_request):
        payload = prepared_request.as_payload()
        rendered = self.transport.render_request(prepared_request.payload_bytes)
        serialized = json.dumps(rendered, sort_keys=True)
        with self.lock:
            if CLEANING_MARKER in serialized:
                visit = 1 + sum(
                    key[0] == payload["sample_id"] and key[1] == "cleaning"
                    for key in self.prepared
                )
                material_key = (payload["sample_id"], "cleaning", visit)
            else:
                material_key = self._material_key(rendered)
            turn = 1 + sum(key[:3] == material_key for key in self.prepared)
            key = (*material_key, turn)
            assert key not in self.prepared
            self.prepared[key] = {
                "rendered": rendered,
                "slot_id": payload["decoding_params"]["id_slot"],
            }
            self.events.append(("fit", key))


def _l2_policy(**boundary_overrides):
    boundary = json.loads(json.dumps(CLEANED_BOUNDARY))
    boundary.update(boundary_overrides)
    return _policy_document(boundaries={"planner:review-finding": boundary})


def _outputs(harness, cleaning_texts):
    anchor = _anchor_outputs(harness)

    def output(key):
        if key[1] == "cleaning":
            index = min(key[2], len(cleaning_texts)) - 1
            return cleaning_texts[index]
        return anchor(key)

    return output


def _episode(tmp_path, *, policy, cleaning_texts=(VALID_CLEANED,), max_contacts):
    harness = _CleaningHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=max_contacts,
        planner_actions=("REVISE", "ACCEPT"),
        reviewer_task_tool=True,
    )
    harness._output = _outputs(harness, cleaning_texts)
    harness.repo_root = REPO_ROOT
    harness.config = replace(
        harness.config,
        context_policy_json=validate_node_context_policy_config(policy),
    )
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
            return replace(material, response_format=perception_format()).validate()
        return material

    harness.material_for_phase = material_for_phase
    try:
        summary = harness.run()
    finally:
        harness.close_summary = harness.close()
    return harness, summary


def _cleaned_rows(summary, boundary_id="B-REVIEW-PLAN"):
    """Every row of one boundary that the policy actually CLEANED.

    The Reviewer's own tool-calling turn is a ``review-finding``-classed state
    too, but it is a native tool-call source, so the policy leaves it verbatim
    and records a ``level: "raw"`` row with that reason -- the same disposition
    E8a already proved.
    """

    return [
        row
        for record in summary.results[0].native_episode_receipt[
            "node_context_policy_compilations"
        ]
        for row in record["compilation"]["boundaries"]
        if row["boundary"]["boundary_id"] == boundary_id and row["level"] == "cleaned"
    ]


def _cleaning_keys(harness):
    return sorted(key for key in harness.prepared if key[1] == "cleaning")


# ---------------------------------------------------------------------------
# (a) the cleaned block reaches the Planner, and an invalid answer does not
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_l2_renders_the_cleaned_block_on_the_planner_and_spends_one_contact(tmp_path):
    harness, summary = _episode(
        tmp_path, policy=_l2_policy(), max_contacts=HARNESS_L2_CEILING,
    )
    # The episode's own eight role contacts, plus ONE cleaning contact per
    # Planner contact -- the (max_revisions + 1) of design section 7.
    assert len(harness.prepared) == 10
    assert len(_cleaning_keys(harness)) == 2
    assert harness.close_summary["request_count"] == 10

    for visit in (1, 2):
        planner = json.dumps(
            harness.prepared[("s1", "planner", visit, 1)]["rendered"], sort_keys=True
        )
        assert "restated as structured issues by one cleaning contact" in planner
        assert "verdict: draft_has_issues" in planner
        assert "- entity_filler: the time reading is ambiguous" in planner
    # The first Planner holds one review and reads only the cleaned block. The
    # second holds two: the one it is deciding about is cleaned, and the
    # superseded earlier one keeps its L1 rendering -- one contact per
    # consumer contact per boundary, exactly as the ceiling assumes.
    assert "UNPARSED REVIEW, VERBATIM" not in json.dumps(
        harness.prepared[("s1", "planner", 1, 1)]["rendered"], sort_keys=True
    )
    assert json.dumps(
        harness.prepared[("s1", "planner", 2, 1)]["rendered"], sort_keys=True
    ).count("UNPARSED REVIEW, VERBATIM") == 1
    # L2 is declared on ONE boundary and changes only what THAT consumer
    # reads: the revising Solver's own ``review-finding`` boundary is still
    # L1, so it still receives the verbatim prose.
    revising_solver = json.dumps(
        harness.prepared[("s1", "solver", 2, 1)]["rendered"], sort_keys=True
    )
    assert "REVIEW OF THE CURRENT DRAFT (Reviewer, UNPARSED)" in revising_solver
    assert PROSE_REVIEW in revising_solver
    assert "restated as structured issues" not in revising_solver

    rows = _cleaned_rows(summary)
    accepted = [row for row in rows if row["cleaning_contact"]["validation"] == "accepted"]
    assert len(accepted) == 2
    for row in accepted:
        assert row["level"] == "cleaned"
        assert row["derived_fields"]["verdict"] == "draft_has_issues"
        contact = row["cleaning_contact"]
        assert contact["rejected_reason"] is None
        # The cleaning contact is an ORDINARY contact in the trace, bound by
        # the same USE record every role contact carries.
        traced = harness.traced_contact(contact["agent_contact_id"])
        assert traced["request_sha256"] == contact["request_sha256"]
        assert traced["response_sha256"] == contact["response_sha256"]
        assert traced["response_text_sha256"] == contact["response_text_sha256"]
        assert contact["instruction_template_sha256"] == (
            CLEANING_INSTRUCTION_TEMPLATE_SHA256
        )
        assert contact["render_template_sha256"] == CLEANING_RENDER_TEMPLATE_SHA256
    # The Planner at revision 2 holds both reviews and cleans only the latest.
    superseded = [row for row in rows if row["cleaning_contact"]["validation"] == "skipped"]
    assert len(superseded) == 1
    assert superseded[0]["cleaning_contact"]["agent_contact_id"] is None

    # A cleaning contact registers no phase state and settles no episode step:
    # the episode's own contact/wave ledger is exactly the L1 episode's.
    assert len(summary.results[0].contacts) == 8
    assert len(summary.results[0].waves) == 8
    # Custody is untouched: the raw Reviewer prose is still the sealed state,
    # and no rendered node-context state is ever sealed into the ledger.
    raw = {state.content for state in summary.results[0].agent_states}
    assert PROSE_REVIEW in raw
    assert all(
        not state.state_kind.startswith("node-context:")
        for state in summary.results[0].agent_states
    )


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize("case", sorted(_INVALID_CLEANINGS))
def test_an_invalid_cleaning_answer_leaves_the_planner_with_the_l1_block(
    tmp_path, case
):
    """(a) five invalid answers, one behaviour: the Planner reads exactly the
    L1 rendering, the receipt records the rejection and its reason, and the
    contact was still spent and still metered -- one attempt, no retry."""

    harness, summary = _episode(
        tmp_path,
        policy=_l2_policy(),
        cleaning_texts=(_INVALID_CLEANINGS[case],),
        max_contacts=HARNESS_L2_CEILING,
    )
    assert len(_cleaning_keys(harness)) == 2
    assert harness.close_summary["request_count"] == 10
    for visit in (1, 2):
        planner = json.dumps(
            harness.prepared[("s1", "planner", visit, 1)]["rendered"], sort_keys=True
        )
        assert "REVIEW OF THE CURRENT DRAFT (Reviewer, UNPARSED)" in planner
        assert PROSE_REVIEW in planner
        assert "restated as structured issues" not in planner
    rejected = [
        row for row in _cleaned_rows(summary)
        if row["cleaning_contact"]["validation"] == "rejected"
    ]
    assert len(rejected) == 2
    for row in rejected:
        reason = row["cleaning_contact"]["rejected_reason"]
        assert isinstance(reason, str) and reason
        assert harness.traced_contact(row["cleaning_contact"]["agent_contact_id"])


# ---------------------------------------------------------------------------
# (b) the ceiling arithmetic, and refusal past it
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_cleaning_contact_is_refused_past_the_registered_ceiling(tmp_path):
    """The Planner's own contact is the fifth of the harness's shape, so a
    ceiling of five leaves nothing for the cleaning contact and the row fails
    rather than silently skipping it."""

    with pytest.raises(Exception, match="cleaning contact exceeds the registered"):
        _episode(
            tmp_path,
            policy=_l2_policy(),
            max_contacts=5,
        )


def test_the_ceiling_formula_adds_one_cleaning_contact_per_consumer_contact():
    """Design section 7 through the actual loader, on the harness's own shape:
    9 without the cleaning boundary, 11 with it."""

    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )
    from test_native_episode_config import config
    from test_role_context_binding import context_program

    def values(policy):
        document = config()
        document["native_episode"]["max_revisions"] = 1
        document["native_episode"]["roles"]["reviewer"]["max_iterations"] = 2
        document["native_episode"]["context_policy"] = policy
        return document

    program = context_program()
    l1 = load_native_episode_config(
        values(_policy_document()), replace(program, max_contacts=HARNESS_L1_CEILING),
    )
    assert l1.max_contacts == HARNESS_L1_CEILING
    l2 = load_native_episode_config(
        values(_l2_policy()), replace(program, max_contacts=HARNESS_L2_CEILING),
    )
    assert l2.max_contacts == HARNESS_L2_CEILING


# ---------------------------------------------------------------------------
# (c) the cleaning request: no evidence, and the committed instruction bytes
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_cleaning_request_carries_no_evidence_and_the_committed_instruction(
    tmp_path
):
    harness, _summary = _episode(
        tmp_path, policy=_l2_policy(), max_contacts=HARNESS_L2_CEILING,
    )
    template_text = (REPO_ROOT / "configs" / CLEANING_INSTRUCTION_TEMPLATE).read_text(
        encoding="utf-8"
    )
    contract = "\n".join(
        line for line in template_text.split("\n")[2:]
        if line and not line.startswith("[")
    )
    contract_lines = [
        line for line in contract.split("\n") if "{structured_material}" not in line
    ]
    for key in _cleaning_keys(harness):
        rendered = harness.prepared[key]["rendered"]
        serialized = json.dumps(rendered, sort_keys=True)
        # The committed instruction bytes, line for line.
        for line in contract_lines:
            assert line in serialized.replace("\\n", "\n")
        # The L1 material it is cleaning, and nothing about the task answer.
        assert PROSE_REVIEW in serialized
        assert "DECISION BRIEF" not in serialized
        assert "HARNESS CHECKS" not in serialized
        # knowledge: "none" -- no evidence block at all, while the speech part
        # this harness attaches to every contact is still there. (This fixture
        # supplies no evidence to ANY contact, so the filter's own falsifier is
        # the direct test below, over a turn that does carry some.)
        assert _evidence_ids(rendered) == []
        assert serialized.count('"type": "input_speech_features"') == 1
        # No agent-state history: the material is IN the instruction.
        assert "[agent state " not in serialized
    # The cleaning contact rides the consumer's own pinned slot.
    slots = {harness.prepared[key]["slot_id"] for key in harness.prepared}
    assert len(slots) == 1


def test_the_cleaning_messages_drop_every_evidence_block_of_the_consumers_turn():
    """The episode fixture above carries no supplied evidence at all, so the
    request-level check there cannot fail. This drives the production filter
    directly, over a user turn that DOES carry evidence: ``knowledge: "none"``
    means the speech part survives and every knowledge block does not."""

    from speech_aware_evidence_acquisition.rails.runner import (
        RailsRunnerError,
        node_context_cleaning_messages,
    )

    speech = {
        "type": "input_speech_features",
        "speech_features": {"packet_id": "p", "sha256": "a" * 64, "role": "query"},
    }
    supplied = [
        {"type": "text", "text": "connected-device control", "evidence_id": "key:domain",
         "source_uri": "knowledge-snapshot://x/domain", "knowledge_role": "key"},
        {"type": "text", "text": "dim the light", "evidence_id": "value:dim",
         "source_uri": "knowledge-snapshot://x/value", "knowledge_role": "value"},
    ]
    system = {"role": "system", "content": "the shared task contract"}
    user = {"role": "user", "content": [speech, *supplied]}
    cleaned_system, cleaned_user = node_context_cleaning_messages((system, user))
    assert cleaned_system == system
    assert cleaned_user["content"] == [speech]
    # The consumer's own messages are never mutated in place.
    assert user["content"] == [speech, *supplied]
    with pytest.raises(RailsRunnerError, match="shared speech turn"):
        node_context_cleaning_messages((system, {"role": "user", "content": []}))
    with pytest.raises(RailsRunnerError, match="shared two messages"):
        node_context_cleaning_messages((system,))


def _without_remaining_contacts(rendered):
    return re.sub(
        r"(remaining_model_contacts[^0-9]{0,6})\d+",
        r"\1N",
        json.dumps(rendered, sort_keys=True),
    )


def _evidence_ids(rendered):
    found = []
    for message in rendered["messages"]:
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and isinstance(part.get("evidence_id"), str):
                found.append(part["evidence_id"])
    return found


# ---------------------------------------------------------------------------
# (d) L0 and L1 are byte-identical to what E8a pinned
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_l0_and_l1_render_exactly_what_e8a_pinned(tmp_path):
    """E8b touches the request bytes of a boundary it is DECLARED on and of no
    other. With the key absent the anchor bytes come back; with an L1 policy
    the bytes captured on master before E8b existed come back."""

    from test_node_context_policy_runner import _episode as _e8a_episode

    l0_harness, _l0 = _e8a_episode(tmp_path / "l0")
    assert _request_digests(l0_harness) == ANCHOR_REQUEST_SHA256
    l1_harness, _l1 = _e8a_episode(tmp_path / "l1", policy=_policy_document())
    assert _request_digests(l1_harness) == L1_REQUEST_SHA256
    assert set(L1_REQUEST_SHA256) == set(ANCHOR_REQUEST_SHA256)
    assert all(
        L1_REQUEST_SHA256[key] != ANCHOR_REQUEST_SHA256[key]
        for key in L1_REQUEST_SHA256
    )


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_l2_changes_only_the_declared_boundarys_consumer(tmp_path, capsys):
    """Design section 8's prompt-fit read, model-free: which contacts of the
    episode L2 moves at all, and by how much.

    Only the Planner's own requests differ from the L1 arm; every other role
    contact is byte-identical, and the cleaning contact is the one request the
    episode gains. On this fixture the reviewer prose is 62 characters, so the
    bounded cleaned brief is LARGER than the verbatim block it replaces --
    design section 8's "L2 reduces the consumer's slice" holds against the
    anchor's p95 of 439 characters, not against a synthetic one-line review.

    Both arms run at the SAME ceiling on purpose. The episode appends its own
    bounded limits (including ``remaining_model_contacts``) to every
    instruction, so a cell that raises the ceiling from 11 to 13 moves every
    request in the episode by that much; isolating the boundary's own effect
    means holding the ceiling fixed.
    """

    from test_node_context_policy_runner import _wire_chars

    l1_harness, _l1 = _episode(
        tmp_path / "l1", policy=_policy_document(), max_contacts=HARNESS_L2_CEILING,
    )
    l2_harness, _l2 = _episode(
        tmp_path / "l2", policy=_l2_policy(), max_contacts=HARNESS_L2_CEILING,
    )
    shared = set(l1_harness.prepared) & set(l2_harness.prepared)
    assert set(l1_harness.prepared) - shared == set()
    assert set(l2_harness.prepared) - shared == set(_cleaning_keys(l2_harness))
    planners = {("s1", "planner", 1, 1), ("s1", "planner", 2, 1)}
    moved = {
        key for key in sorted(shared)
        if l1_harness.prepared[key]["rendered"] != l2_harness.prepared[key]["rendered"]
    }
    assert planners <= moved
    # Every OTHER request that moved did so in exactly one field: the episode
    # tells each role how many contacts remain, and a cleaning contact is a
    # contact. Normalising that one number away makes them byte-identical --
    # which is the check that the cleaning contact is metered like any other
    # and changes no other role's context.
    for key in moved - planners:
        assert _without_remaining_contacts(
            l1_harness.prepared[key]["rendered"]
        ) == _without_remaining_contacts(l2_harness.prepared[key]["rendered"]), key
    with capsys.disabled():
        print("\nNCP L2 prompt-volume delta (wire characters):")
        for key in sorted(moved):
            before = _wire_chars(l1_harness.prepared[key]["rendered"])
            after = _wire_chars(l2_harness.prepared[key]["rendered"])
            print(f"  {key}: {before} -> {after} ({after - before:+d})")
        for key in _cleaning_keys(l2_harness):
            print(f"  {key}: + {_wire_chars(l2_harness.prepared[key]['rendered'])}")


# ---------------------------------------------------------------------------
# (e) the switch key
# ---------------------------------------------------------------------------


def test_the_switch_key_accepts_cleaned_and_keeps_its_null_arm(tmp_path):
    from speech_aware_evidence_acquisition.rails.config_tables import (
        EPISODE_LEVEL_SWITCH_KEYS,
        is_episode_null_arm,
        resolve_episode_switch_key,
    )

    key = "native_episode.context_policy"
    assert key in EPISODE_LEVEL_SWITCH_KEYS
    assert resolve_episode_switch_key(key) == key
    assert is_episode_null_arm(key, _l2_policy()) is False
    assert is_episode_null_arm(key, None) is True
    assert is_episode_null_arm(key, "raw") is True
    assert json.loads(
        validate_node_context_policy_config(_l2_policy())
    )["boundaries"]["planner:review-finding"]["level"] == "cleaned"


def test_the_l2_policy_document_is_the_cell_b7b_config_surface():
    """The whole config difference between cell B7a and cell B7b: one boundary
    entry gains ``level: "cleaned"`` and its four-field cleaning block."""

    b7a = _policy_document()
    b7b = _l2_policy()
    assert set(b7b) - set(b7a) == {"boundaries"}
    assert b7a["level"] == b7b["level"] == "structured"
    assert b7a["policy_id"] == b7b["policy_id"] == "typed-slurp-node-context-v1"
    assert json.dumps(b7a["params"], sort_keys=True) == json.dumps(
        b7b["params"], sort_keys=True
    )
    assert b7b["boundaries"] == {
        "planner:review-finding": {
            "level": "cleaned",
            "template": "probes/ncp_slurp_review_finding_v1.txt",
            "on_parse_failure": "raw",
            "cleaning": {
                "phase_id": "context_clean_review",
                "instruction_template": CLEANING_INSTRUCTION_TEMPLATE,
                "response_format_id": "ncp-review-issues-v1",
                "on_invalid": "fallback-l1",
            },
        }
    }
    assert b7b["params"]["draft_response_schema"] == json.loads(
        json.dumps(DRAFT_SCHEMA)
    )
    assert b7b["params"]["legal_entity_types"] == list(LEGAL_ENTITY_TYPES)
    assert hashlib.sha256(
        (REPO_ROOT / "configs" / CLEANING_INSTRUCTION_TEMPLATE).read_bytes()
    ).hexdigest() == CLEANING_INSTRUCTION_TEMPLATE_SHA256
    assert Path(REPO_ROOT, "configs", CLEANING_INSTRUCTION_TEMPLATE).is_file()
