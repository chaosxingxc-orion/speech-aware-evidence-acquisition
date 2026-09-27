"""Gap G1 plumbing through the ACTUAL shared ``rails.runner`` episode
invocation -- no network and no model.

Complements ``test_solver_citation.py`` (the pure contract, its custody and
its credit read) with the live-wiring proof the seam owes:

* un-armed, the episode is byte-identical to its prior self -- no
  ``solver_citations`` block, the Solver's raw answer delivered under I7;
* armed, the ONLY request byte that moves is the Solver contact's own
  ``response_format`` (specialised to the ids that contact rendered); every
  message of every contact -- Perception, Solver, Reviewer, Planner -- is the
  un-armed contact's own, because the sealed Solver state is the ANSWER's
  bytes and the citation is metadata beside it;
* the delivered text is the answer's own bytes, re-derived from the recorded
  envelope by the registered unwrap normaliser (I7n), i.e. the same bytes
  the un-armed arm delivers;
* the citation round-trips: sealed on the Solver state's ``cited_value_ids``,
  carried in the next contact's request payload, and recorded in the row's
  ``solver_citations`` receipt block beside the ids that contact was shown;
* a citation of evidence the contact never rendered is a refusal.

Run through the SAME ``_ActualEpisodeHarness`` fake transport
``test_native_episode_runner.py`` and the E11 proof already use.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from functools import partial

import pytest

from speech_aware_evidence_acquisition.rails.controllers import PhaseProgram
from speech_aware_evidence_acquisition.rails.delivery_normalisers import (
    DELIVER_NORMALISER_RECEIPT_SCHEMA,
)
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.runner import run_speech_native_agent_loop
from speech_aware_evidence_acquisition.rails.solver_citation import (
    CITED_ANSWER_RESPONSE_FORMAT_ID,
    DELIVER_CITED_ANSWER_V1,
    SOLVER_CITATIONS_RECEIPT_SCHEMA,
    cited_answer_response_format,
    cited_answer_response_format_for,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

# pytest module-scoped autouse fixture (spawns the fake llama-server-shaped
# process the transport dials): must be IMPORTED into this module's own
# namespace, exactly as test_native_episode_runner.py itself does.
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
import test_native_episode_runner as harness_module
from test_native_episode_runner import _ActualEpisodeHarness

#: The one value the harness's fake TRAIN snapshot holds; seeded into every
#: row's query state so each contact renders exactly one ``[evidence ...]``.
SUPPLIED = ("value:dim-light",)
RAW_ANSWER = json.dumps(
    {"scenario": "alarm", "action": "set", "entities": [{"type": "time", "filler": "six thirty am"}]},
    ensure_ascii=False, sort_keys=True,
)


def _envelope(intent, entity):
    return (
        '{"schema":"saea-solver-cited-answer-v1","answer":%s,"citations":{"intent":%s,'
        '"entities":[{"type":"time","evidence_ids":%s}]}}'
        % (RAW_ANSWER, json.dumps(list(intent)), json.dumps(list(entity)))
    )


CITING = _envelope(SUPPLIED, SUPPLIED)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class _CitingHarness(_ActualEpisodeHarness):
    """The shared harness with the Solver phase optionally declaring the
    cited-answer contract (and the unwrap normaliser the loader pairs it
    with), and the request PAYLOAD history kept beside the rendered body."""

    def __init__(self, tmp_path, *, armed: bool, solver_output: str):
        super().__init__(
            tmp_path, sample_count=1, max_revisions=0, max_contacts=4,
            planner_actions=("ACCEPT",), arm="speech-feature-query",
        )
        self.armed = armed
        self.solver_output = solver_output
        self.payload_histories = {}
        if armed:
            self.program = PhaseProgram(
                program_id=self.program.program_id,
                phases=tuple(
                    dataclasses.replace(phase, response_format_id=CITED_ANSWER_RESPONSE_FORMAT_ID)
                    if phase.name == "solver" else phase
                    for phase in self.program.phases
                ),
                max_contacts=self.program.max_contacts,
                stop_rule=self.program.stop_rule,
            ).validate()
            self.config = dataclasses.replace(
                self.config, deliver_normaliser_id=DELIVER_CITED_ANSWER_V1
            )

    def _output(self, key):
        sample_id, phase, visit, _turn = key
        if phase == "solver":
            return self.solver_output
        if phase == "planner":
            return "ACCEPT"
        return f"{phase}-analysis:{sample_id}:visit:{visit}"

    def material_for_phase(self, phase, context, sealed):
        material = super().material_for_phase(phase, context, sealed)
        if self.armed and phase == "solver":
            material = PhaseMaterial(
                instruction=material.instruction,
                response_format=cited_answer_response_format(),
                contact_id=material.contact_id,
                purpose=material.purpose,
            ).validate()
        return material

    def request_gate(self, prepared_request):
        super().request_gate(prepared_request)
        rendered = self.transport.render_request(prepared_request.payload_bytes)
        material_key = self._material_key(rendered)
        self.payload_histories[material_key] = list(
            prepared_request.as_payload().get("history", [])
        )


def _run(tmp_path, monkeypatch, *, armed: bool, solver_output: str):
    monkeypatch.setattr(
        harness_module, "run_speech_native_agent_loop",
        partial(run_speech_native_agent_loop, bootstrap_value_ids=SUPPLIED),
    )
    harness = _CitingHarness(tmp_path, armed=armed, solver_output=solver_output)
    try:
        summary = harness.run()
    finally:
        harness.close()
    dispatched = [key for event, key in harness.events if event == "dispatch"]
    bodies = [harness.prepared[key]["rendered"] for key in dispatched]
    return summary, dispatched, bodies, harness


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_contract_moves_only_the_solver_decoding_and_seals_the_citation(tmp_path, monkeypatch):
    off_summary, off_keys, off_bodies, off_harness = _run(
        tmp_path / "off", monkeypatch, armed=False, solver_output=RAW_ANSWER,
    )
    on_summary, on_keys, on_bodies, on_harness = _run(
        tmp_path / "on", monkeypatch, armed=True, solver_output=CITING,
    )
    assert [key[1] for key in off_keys] == ["perception", "solver", "reviewer", "planner"]
    assert [key[1] for key in on_keys] == [key[1] for key in off_keys]

    # 1. Every MESSAGE byte of every contact is identical with and without
    #    the contract; the ONLY difference in any request is the Solver's
    #    own response format, specialised to the ids that contact rendered.
    for key, off_body, on_body in zip(on_keys, off_bodies, on_bodies, strict=True):
        off_rest, on_rest = dict(off_body), dict(on_body)
        off_format, on_format = off_rest.pop("response_format", None), on_rest.pop("response_format", None)
        assert on_rest == off_rest, key
        if key[1] == "solver":
            assert off_format is None
            assert on_format == cited_answer_response_format_for(SUPPLIED)
        else:
            assert on_format == off_format

    off_result, on_result = off_summary.results[0], on_summary.results[0]

    # 2. The un-armed arm is its prior self: raw answer delivered, no block.
    assert off_result.final_response_text == RAW_ANSWER
    assert "solver_citations" not in off_result.native_episode_receipt
    assert "deliver_normaliser" not in off_result.native_episode_receipt

    # 3. The armed arm delivers the SAME answer bytes, re-derived from the
    #    recorded envelope by the registered unwrap (I7n).
    assert on_result.final_response_text == RAW_ANSWER
    normalised = on_result.native_episode_receipt["deliver_normaliser"]
    assert normalised["schema"] == DELIVER_NORMALISER_RECEIPT_SCHEMA
    assert normalised["normaliser_id"] == DELIVER_CITED_ANSWER_V1
    assert normalised["applied"] is True and normalised["changed"] is True
    assert normalised["input_sha256"] == _sha(CITING)
    assert normalised["output_sha256"] == _sha(RAW_ANSWER)
    assert normalised["cited_value_ids_count"] == 1
    accepted = on_result.native_episode_receipt["accepted_solver_receipt"]["final_contact"]
    assert accepted["response_text_sha256"] == _sha(CITING)

    # 4. The row's receipt names what the contact was shown and what it cited.
    block = on_result.native_episode_receipt["solver_citations"]
    assert block["schema"] == SOLVER_CITATIONS_RECEIPT_SCHEMA
    assert block["response_format_id"] == CITED_ANSWER_RESPONSE_FORMAT_ID
    assert len(block["contacts"]) == 1
    record = block["contacts"][0]
    assert record["contact_id"] == accepted["agent_contact_id"]
    assert record["role_id"] == "solver" and record["parse"] == "ok"
    assert record["supplied_value_ids"] == list(SUPPLIED)
    assert record["cited_value_ids"] == list(SUPPLIED)
    assert record["intent_evidence_ids"] == list(SUPPLIED)
    assert record["entity_citations"] == [{"type": "time", "evidence_ids": list(SUPPLIED)}]
    assert record["answer_sha256"] == _sha(RAW_ANSWER)
    assert record["response_text_sha256"] == _sha(CITING)
    # The supplied set IS the evidence the Solver request rendered.
    solver_key = next(key for key in on_keys if key[1] == "solver")
    rendered_evidence = [
        part.get("evidence_id") for part in on_harness.prepared[solver_key]["rendered"]["messages"][1]["content"]
        if isinstance(part, dict) and part.get("evidence_id")
    ] if isinstance(on_harness.prepared[solver_key]["rendered"].get("messages", [None, {}])[1].get("content"), list) else None
    if rendered_evidence:
        assert rendered_evidence == list(SUPPLIED)

    # 5. Round trip: the sealed Solver state reaches the Reviewer's request
    #    payload with the answer as its content and the citation beside it.
    reviewer_key = next(key for key in on_keys if key[1] == "reviewer")
    history = on_harness.payload_histories[reviewer_key[:3]]
    solver_states = [
        item for item in history
        if item.get("role") == "agent_state" and item.get("state_kind") == "phase:solver"
    ]
    assert len(solver_states) == 1
    assert solver_states[0]["content"] == RAW_ANSWER
    assert solver_states[0]["cited_value_ids"] == list(SUPPLIED)
    assert solver_states[0]["source_response_sha256"] == _sha(CITING)
    off_history = off_harness.payload_histories[reviewer_key[:3]]
    off_solver = [item for item in off_history if item.get("state_kind") == "phase:solver"]
    assert off_solver[0]["content"] == RAW_ANSWER and off_solver[0]["cited_value_ids"] == []

    # 6. Everything else about the episode is unchanged: the same visits in
    #    the same order and the same Planner routes. The Solver visit's own
    #    request/response digests legitimately differ (its request carries
    #    the specialised response format and its response is the envelope);
    #    every other visit's digests are identical, which restates (1).
    assert len(on_result.contacts) == len(off_result.contacts) == 4
    on_visits = on_result.native_episode_receipt["role_visits"]
    off_visits = off_result.native_episode_receipt["role_visits"]
    assert [
        {key: value for key, value in visit.items() if key != "execution_receipt"}
        for visit in on_visits
    ] == [
        {key: value for key, value in visit.items() if key != "execution_receipt"}
        for visit in off_visits
    ]
    for on_visit, off_visit in zip(on_visits, off_visits, strict=True):
        if on_visit["role_id"] != "solver":
            # The same fake response to the same rendered body; the request
            # digest itself may bind payload custody fields (the Solver
            # state's source hash and citation) that never reach the wire.
            assert (
                on_visit["execution_receipt"]["final_contact"]["response_text_sha256"]
                == off_visit["execution_receipt"]["final_contact"]["response_text_sha256"]
            )
    assert on_result.native_episode_receipt["planner_routes"] == off_result.native_episode_receipt["planner_routes"]
    assert on_result.solver_group is None


def _chain(error):
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        yield error
        error = error.__cause__ or error.__context__


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_citation_of_unsupplied_evidence_is_refused_at_the_seal(tmp_path, monkeypatch):
    """The fake core ignores the grammar, so this exercises the seal-time
    refusal the constrained decoder would otherwise make unreachable."""

    with pytest.raises(Exception) as excinfo:
        _run(
            tmp_path, monkeypatch, armed=True,
            solver_output=_envelope(("value:never-supplied",), ()),
        )
    assert any("never supplied" in str(error) for error in _chain(excinfo.value))


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_solver_answer_that_is_not_an_envelope_is_refused_when_the_contract_is_armed(
    tmp_path, monkeypatch,
):
    with pytest.raises(Exception) as excinfo:
        _run(tmp_path, monkeypatch, armed=True, solver_output=RAW_ANSWER)
    assert any("cited-answer contract refused" in str(error) for error in _chain(excinfo.value))
