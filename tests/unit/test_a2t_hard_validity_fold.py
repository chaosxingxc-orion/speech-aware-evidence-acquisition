"""WAVE R7: the hard-validity fold, proved against the SEALED G3 flight.

``rails.a2t_hard_validity.HardValidityRepairController`` is gone. Its
sequencing is ``phase-hard-validity-repair-v1`` on
``rails.controllers.EvidenceAgentController``, built by
``rails.controllers.make_hard_validity_phase_controller``.

The claim this file proves, on the flight's own bytes and without re-running
it:

**Wire equivalence.** For every row of the sealed
``SAEA-A2T-G3-PLAIN-ENGLISH-V1`` matched arm, replaying that row's own sealed
responses through the folded program produces the same number of contacts, in
the same order, with the same ``contact_id``, the same CONTROL-turn
instruction bytes, the same AGENT_STATE content bytes, the same declared arm
identity, and the same final-response contact. Those are exactly the fields
the frozen core reads.

**Declared identity deltas.** Three fields change, and must: the sealed
state's ``state_id`` (``state:hard-validity:<sample>:<hash12>`` ->
``draft:<sample>``), its ``state_kind`` (``hard-validity-report`` ->
``phase:draft``) and its ``producer_policy_id`` (``hard_validity_v1`` ->
``phase-hard-validity-repair-v1``). They are receipt identity, not request
content, and a receipt that still claimed ``hard_validity_v1`` would be naming
a controller this repository no longer has. The test pins the new values so
the delta is measured rather than waved at, and asserts the fourth consequence
(the repair contact's ``query_state_sha256`` moves with the state id).

The flight is NOT re-run and no model is contacted: the sealed trace carries
every response text, and the fold is driven over them in process. Without
``$SPEECHRL_DATA_DIR`` the sealed half skips and the synthetic half still runs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.a2t_hard_validity import (
    DRAFT_CONTACT_ID,
    DRAFT_INSTRUCTION,
    REPAIR_CONTACT_ID,
    REPAIR_INSTRUCTION,
    hard_validity_repair_state_view,
)
from speech_aware_evidence_acquisition.rails.controllers import (
    HARD_VALIDITY_PROGRAM_ID,
    make_hard_validity_phase_controller,
)
from speech_aware_evidence_acquisition.rails.knowledge import QueryState
from speech_aware_evidence_acquisition.rails.runner import AgentRuntimeContext

REPO_ROOT = Path(__file__).resolve().parents[2]

#: The sealed G3 matched arm this fold is proved against: the flight whose
#: agent trace ``docs/checks/.../2026-09-02-a2t-g3-plain-english-v1/analysis.md``
#: names as the source of the terminal composite.
SEALED_TRACE_RELPATH = (
    "runs/SAEA-A2T-G3-PLAIN-ENGLISH-V1/flight-20260902T180333Z/matched/"
    "agent-trace/SAEA-A2T-G3-PLAIN-ENGLISH-V1.trace.jsonl"
)
SEALED_KEY_REPRESENTATION_ID = "a2t-g3-plain-english-k32-v1"
SEALED_MATCHER_POLICY_ID = "a2t-g3-construction-bm25-k32-matched-v1"
SEALED_CONTROLLER_POLICY_ID = "hard_validity_v1"
SEALED_STATE_KIND = "hard-validity-report"

_SHA = "a" * 64


# ---------------------------------------------------------------------------
# Sealed-flight fixtures
# ---------------------------------------------------------------------------


def _sealed_trace() -> list[dict] | None:
    root = os.environ.get("SPEECHRL_DATA_DIR")
    if not root:
        return None
    path = Path(root) / SEALED_TRACE_RELPATH
    if not path.is_file():
        return None
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _registry_rows():
    from speech_aware_evidence_acquisition.data.lock import (
        AssetResolutionError,
        asset_dir,
        data_root,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.data.audio2tool import load_tool_registry

    try:
        lock = load_lock(umbrella_lock_path(REPO_ROOT))
        if not (asset_dir(lock, "audio2tool", data_root()) / "tools_registry.csv").is_file():
            return None
        return load_tool_registry(lock, data_root())
    except (AssetResolutionError, OSError, ValueError, KeyError):
        return None


def _sealed_rows(trace: list[dict]) -> dict[str, dict]:
    """``sample_id -> {"contacts": [...], "responses": [...]}`` from the sealed
    USE and MODEL_RESPONSE records."""

    responses = {
        record["record_id"].rsplit("/", 1)[0]: record["payload"]["text"]
        for record in trace
        if record["channel"] == "MODEL_RESPONSE"
    }
    requests = {
        record["record_id"].rsplit("/", 1)[0]: record["payload"]["payload"]
        for record in trace
        if record["channel"] == "MODEL_REQUEST"
    }
    rows: dict[str, dict] = {}
    for record in trace:
        # Two USE shapes share the channel: the runtime-use record carrying the
        # contact plans, and a consumption/metrics record that does not.
        if record["channel"] != "USE" or "use_contacts" not in record["payload"]:
            continue
        sample_id = record["record_id"].split("/", 1)[0]
        contacts = record["payload"]["use_contacts"]
        ordered = [
            request_id
            for request_id, payload in sorted(requests.items())
            if payload["sample_id"] == sample_id
        ]
        rows[sample_id] = {
            "contacts": contacts,
            "requests": [requests[request_id] for request_id in ordered],
            "responses": [responses[request_id] for request_id in ordered],
        }
    return rows


def _initial_context(sample_id: str) -> AgentRuntimeContext:
    state = QueryState(
        query_id=f"g3:{sample_id}:step0",
        query_sample_id=sample_id,
        speech_packet_id=f"speech/{sample_id}",
        speech_packet_sha256=_SHA,
        use_split_identity_hash=_SHA,
        loop_step=0,
    ).validate()
    return AgentRuntimeContext(
        sample_id=sample_id,
        knowledge_snapshot_sha256="c" * 64,
        catalog_facet_ids=(),
        catalog_value_ids=(),
        query_state=state,
        task_contract="Return the requested calls as JSON.",
        agent_states=(),
        prior_response_sha256s=(),
        contact_index=0,
    )


def _replay(controller, sample_id: str, responses: list[str]) -> list[dict]:
    """Drive the folded controller over one row's SEALED responses.

    Returns one record per contact: what was dispatched, and what the wave
    sealed. No model, no network, no data read -- the responses are the
    flight's own bytes.
    """

    context = _initial_context(sample_id)
    contact = controller.initial_contact(context)
    dispatched: list[dict] = []
    for index, response in enumerate(responses):
        entry = {
            "contact_id": contact.contact_id,
            "instruction": contact.instruction,
            "key_representation_id": contact.key_representation_id,
            "matcher_policy_id": contact.matcher_policy_id,
            "query_state_sha256": contact.query_state_sha256,
            "decoding_params": dict(contact.decoding_params),
            "agent_state_contents": [
                artifact.content for artifact in context.agent_states
            ],
        }
        advance = controller.advance(context, contact, response)
        entry["action_kind"] = advance.transition.action_kind
        entry["final_response_contact_id"] = advance.final_response_contact_id
        entry["sealed"] = [
            {
                "state_id": artifact.state_id,
                "state_kind": artifact.state_kind,
                "producer_policy_id": artifact.producer_policy_id,
                "content": artifact.content,
            }
            for artifact in advance.new_agent_states
        ]
        dispatched.append(entry)
        if advance.next_contact is None:
            break
        assert index + 1 < len(responses), "the fold asked for a contact the flight never made"
        context = AgentRuntimeContext(
            sample_id=context.sample_id,
            knowledge_snapshot_sha256=context.knowledge_snapshot_sha256,
            catalog_facet_ids=context.catalog_facet_ids,
            catalog_value_ids=context.catalog_value_ids,
            query_state=advance.next_query_state,
            task_contract=context.task_contract,
            agent_states=context.agent_states + advance.new_agent_states,
            prior_response_sha256s=context.prior_response_sha256s + (_SHA,),
            contact_index=context.contact_index + 1,
        )
        contact = advance.next_contact
    return dispatched


# ---------------------------------------------------------------------------
# 1. Wire equivalence against the sealed flight
# ---------------------------------------------------------------------------


def test_the_fold_reproduces_the_sealed_g3_flight_contact_for_contact():
    trace = _sealed_trace()
    if trace is None:
        pytest.skip(
            "the sealed G3 agent trace is absent on this machine "
            f"($SPEECHRL_DATA_DIR/{SEALED_TRACE_RELPATH})"
        )
    rows = _registry_rows()
    if rows is None:
        pytest.skip(
            "the locked Audio2Tool tools_registry.csv is absent on this machine"
        )
    factory = make_hard_validity_phase_controller(
        registry_rows=rows,
        key_representation_id=SEALED_KEY_REPRESENTATION_ID,
        matcher_policy_id=SEALED_MATCHER_POLICY_ID,
        decoding_params={},
    )
    sealed = _sealed_rows(trace)
    assert len(sealed) == 40, f"expected the sealed 40-row matched arm, got {len(sealed)}"

    repaired_rows = 0
    for sample_id, row in sorted(sealed.items()):
        replayed = _replay(factory(sample_id), sample_id, row["responses"])

        # (a) same number of contacts, in the same order, with the same ids.
        assert len(replayed) == len(row["contacts"]), sample_id
        for entry, sealed_contact in zip(replayed, row["contacts"], strict=True):
            plan = sealed_contact["plan"]
            assert entry["contact_id"] == plan["contact_id"], sample_id
            # (b) the CONTROL turn: byte-identical instruction.
            assert entry["instruction"] == plan["instruction"], sample_id
            # (c) the declared arm identity travels unchanged.
            assert entry["key_representation_id"] == plan["key_representation_id"]
            assert entry["matcher_policy_id"] == plan["matcher_policy_id"]

        # (d) the AGENT_STATE turn: byte-identical content. The sealed repair
        #     request carries it as history turn 1; the fold carries the same
        #     bytes as the draft phase's sealed state.
        if len(replayed) == 2:
            repaired_rows += 1
            sealed_state_turns = [
                turn
                for turn in row["requests"][1]["history"]
                if turn["role"] == "agent_state"
            ]
            assert len(sealed_state_turns) == 1, sample_id
            assert replayed[1]["agent_state_contents"] == [
                sealed_state_turns[0]["content"]
            ], sample_id
            assert replayed[0]["action_kind"] == "organize", sample_id
        else:
            assert replayed[0]["action_kind"] == "stop", sample_id

        # (e) the same final answer, from the same contact.
        assert replayed[-1]["final_response_contact_id"] == replayed[-1]["contact_id"]
        assert replayed[-1]["action_kind"] == "stop", sample_id

    # The flight spent a repair contact on exactly five of its forty rows; a
    # fold that repaired none, or all, would pass every equality above.
    assert repaired_rows == 5


def test_the_declared_identity_deltas_are_exactly_the_three_named_fields():
    trace = _sealed_trace()
    if trace is None:
        pytest.skip("the sealed G3 agent trace is absent on this machine")
    rows = _registry_rows()
    if rows is None:
        pytest.skip("the locked Audio2Tool tools_registry.csv is absent on this machine")
    factory = make_hard_validity_phase_controller(
        registry_rows=rows,
        key_representation_id=SEALED_KEY_REPRESENTATION_ID,
        matcher_policy_id=SEALED_MATCHER_POLICY_ID,
        decoding_params={},
    )
    sealed = _sealed_rows(trace)
    repaired = [
        (sample_id, row)
        for sample_id, row in sorted(sealed.items())
        if len(row["contacts"]) == 2
    ]
    assert repaired, "no sealed row spent a repair contact"
    for sample_id, row in repaired:
        replayed = _replay(factory(sample_id), sample_id, row["responses"])
        state = replayed[0]["sealed"][0]
        # what changed, exactly:
        assert state["state_id"] == f"draft:{sample_id}"
        assert state["state_kind"] == "phase:draft"
        assert state["state_kind"] != SEALED_STATE_KIND
        assert state["producer_policy_id"] == HARD_VALIDITY_PROGRAM_ID
        assert state["producer_policy_id"] != SEALED_CONTROLLER_POLICY_ID
        # and its one consequence: the repair contact binds a successor
        # QueryState whose hash moved with the state id.
        assert (
            replayed[1]["query_state_sha256"] != replayed[0]["query_state_sha256"]
        )
        # what did NOT change: the report bytes the repair contact reads.
        assert state["content"] == replayed[1]["agent_state_contents"][0]


# ---------------------------------------------------------------------------
# 2. The same properties, without the controlled data root
# ---------------------------------------------------------------------------


SYNTHETIC_ROWS = (
    {
        "tool_name": "getBatteryStatus",
        "signature": "getBatteryStatus()",
        "argument_constraints": "",
    },
)
VALID_DRAFT = json.dumps([{"name": "getBatteryStatus", "arguments": {}}])


def _synthetic_factory():
    return make_hard_validity_phase_controller(
        registry_rows=SYNTHETIC_ROWS,
        key_representation_id="k-rep-v1",
        matcher_policy_id="matcher-v1",
        decoding_params={},
    )


def test_a_valid_draft_spends_one_contact_and_seals_no_state():
    replayed = _replay(_synthetic_factory()("s1"), "s1", [VALID_DRAFT, "unused"])
    assert len(replayed) == 1
    assert replayed[0]["contact_id"] == DRAFT_CONTACT_ID
    assert replayed[0]["instruction"] == DRAFT_INSTRUCTION
    assert replayed[0]["action_kind"] == "stop"
    assert replayed[0]["sealed"] == []
    assert replayed[0]["final_response_contact_id"] == DRAFT_CONTACT_ID


def test_a_hard_invalid_draft_spends_two_and_carries_the_registered_report():
    replayed = _replay(_synthetic_factory()("s1"), "s1", ["[]", VALID_DRAFT])
    assert [entry["contact_id"] for entry in replayed] == [
        DRAFT_CONTACT_ID,
        REPAIR_CONTACT_ID,
    ]
    assert replayed[1]["instruction"] == REPAIR_INSTRUCTION
    expected = hard_validity_repair_state_view("[]", SYNTHETIC_ROWS)
    assert replayed[0]["sealed"][0]["content"] == expected
    assert replayed[1]["agent_state_contents"] == [expected]
    assert replayed[1]["final_response_contact_id"] == REPAIR_CONTACT_ID


def test_the_contact_carries_no_decoding_params_because_the_run_does():
    replayed = _replay(_synthetic_factory()("s1"), "s1", [VALID_DRAFT])
    assert replayed[0]["decoding_params"] == {}


def test_the_registered_state_view_is_the_only_derivation_and_it_is_pure():
    from speech_aware_evidence_acquisition.core.base import PHASE_STATE_VIEWS

    assert "a2t-hard-validity-repair-report-v1" in PHASE_STATE_VIEWS.names()
    view = PHASE_STATE_VIEWS.resolve("a2t-hard-validity-repair-report-v1")(
        SYNTHETIC_ROWS
    )
    assert view("[]") == view("[]")
    assert view("[]") == hard_validity_repair_state_view("[]", SYNTHETIC_ROWS)


def test_no_loop_step_arithmetic_survives_in_the_folded_module():
    """The W2 caveat, closed: the module reads no ``loop_step`` and defines no
    controller. Asserted on the AST, so the prose that EXPLAINS the removal
    cannot satisfy the test."""

    import ast

    path = (
        REPO_ROOT
        / "src/speech_aware_evidence_acquisition/rails/a2t_hard_validity.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    attributes = {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    classes = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
    }
    assert "loop_step" not in attributes | names
    assert "HardValidityRepairController" not in classes
    # ... and it defines no controller-shaped class at all.
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = {
                item.name
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            assert not {"initial_contact", "advance"} <= methods, node.name
