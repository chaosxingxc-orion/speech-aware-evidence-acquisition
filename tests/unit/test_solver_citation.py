"""Gap G1 plumbing (``rails.solver_citation``): the Solver's cited-answer
contract, its delivery custody, its loader pairing and the per-entry credit
read it feeds. Pure, model-free; the live-wiring proof through the shared
runner is ``test_native_episode_runner_solver_citation.py``.
"""

from __future__ import annotations

import hashlib
import json
import random

import pytest
from jsonschema import Draft202012Validator, ValidationError

from speech_aware_evidence_acquisition.analysis.citation_credit import (
    CREDIT_TABLE_PER_ARM_SCHEMA,
    CREDIT_TABLE_SCHEMA,
    ArmCitationRow,
    CitationCreditError,
    CitationRow,
    arm_credit_table,
    arm_rows_from_citation_rows,
    credit_table,
    load_arm_rows,
    load_correctness_by_arm,
    main as credit_main,
    render_arm_credit_table,
    render_credit_table,
    rows_from_outputs,
)
from speech_aware_evidence_acquisition.core.base import DELIVERY_NORMALISERS, RESPONSE_FORMATS
from speech_aware_evidence_acquisition.rails import controllers  # noqa: F401 - registers formats
from speech_aware_evidence_acquisition.rails import slurp_projection_v3 as v3
from speech_aware_evidence_acquisition.rails.controllers import (
    PhaseProgram,
    PhaseSpec,
    seal_phase_response_state,
)
from speech_aware_evidence_acquisition.rails.delivery_normalisers import (
    DELIVER_NORMALISE_V3,
    DELIVER_NORMALISER_RECEIPT_SCHEMA,
)
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.solver_citation import (
    CITED_ANSWER_RESPONSE_FORMAT_ID,
    DELIVER_CITED_ANSWER_NORMALISE_V3_V1,
    DELIVER_CITED_ANSWER_V1,
    MAX_ENTITY_CITATIONS,
    MAX_EVIDENCE_IDS_PER_ENTITY,
    MAX_INTENT_CITATIONS,
    SolverCitationError,
    answer_span,
    bind_cited_completion,
    cited_answer_response_format,
    cited_answer_response_format_for,
    parse_cited_answer,
    validate_citations_supplied,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import legal_intent_inventory
from test_native_episode_config import config as _episode_values

#: The model's own answer bytes: irregular spacing and a non-canonical key
#: order, so a re-serialisation would be caught.
ANSWER = '{ "action":"set" ,"scenario": "alarm","entities":[{"type":"time","filler":"6:30AM"}]}'
SUPPLIED = ("value:a", "key:b", "value:c", "candidate-proposal:d")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def envelope(*, answer=ANSWER, intent=("value:a",), entities=((("time"), ("key:b", "value:c")),),
             schema=CITED_ANSWER_RESPONSE_FORMAT_ID, extra="", citations_extra=""):
    entity_text = ",".join(
        '{"type":%s,"evidence_ids":%s}' % (json.dumps(kind), json.dumps(list(ids)))
        for kind, ids in entities
    )
    return (
        '{"schema":%s, "answer" : %s ,"citations":{"intent":%s,"entities":[%s]%s}%s}'
        % (json.dumps(schema), answer, json.dumps(list(intent)), entity_text, citations_extra, extra)
    )


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------


def test_the_contract_is_registered_under_its_id_and_takes_no_parameters():
    assert CITED_ANSWER_RESPONSE_FORMAT_ID in RESPONSE_FORMATS.names()
    builder = RESPONSE_FORMATS.resolve(CITED_ANSWER_RESPONSE_FORMAT_ID)
    assert builder({}, None) == cited_answer_response_format()
    assert builder() == cited_answer_response_format()
    with pytest.raises(SolverCitationError, match="no parameters"):
        builder({}, None, max_ids=3)


def test_parse_cuts_the_answer_bytes_exactly_and_orders_the_union():
    text = envelope()
    parsed = parse_cited_answer(text)
    assert parsed.answer_text == ANSWER
    assert text[slice(*answer_span(text))] == ANSWER
    assert parsed.answer == json.loads(ANSWER)
    assert parsed.intent_evidence_ids == ("value:a",)
    assert parsed.entity_citations[0].type == "time"
    assert parsed.entity_citations[0].evidence_ids == ("key:b", "value:c")
    # First-citation order, intent first, each id once.
    text = envelope(intent=("value:c", "value:a"), entities=(("time", ("value:a", "key:b")),))
    assert parse_cited_answer(text).cited_value_ids == ("value:c", "value:a", "key:b")


def test_the_answer_member_is_found_wherever_the_model_put_it():
    text = '{"citations":{"intent":[],"entities":[]},"schema":"%s","answer":%s}' % (
        CITED_ANSWER_RESPONSE_FORMAT_ID, ANSWER,
    )
    assert parse_cited_answer(text).answer_text == ANSWER


@pytest.mark.parametrize(
    "text, reason",
    (
        ("", "nonempty"),
        ("   ", "nonempty"),
        ("x" * 20000, "nonempty"),
        (ANSWER, "JSON contract"),
        (envelope(schema="saea-review-findings-v1"), "JSON contract"),
        (envelope(extra=',"note":"x"'), "JSON contract"),
        (envelope(citations_extra=',"other":[]'), "JSON contract"),
        (envelope(answer='"a string"'), "JSON contract"),
        (envelope(answer="[1]"), "JSON contract"),
        (envelope(intent=("",)), "JSON contract"),
        (envelope(intent=tuple(f"v:{i}" for i in range(MAX_INTENT_CITATIONS + 1))), "JSON contract"),
        (envelope(entities=(("time", tuple(f"v:{i}" for i in range(MAX_EVIDENCE_IDS_PER_ENTITY + 1))),)), "JSON contract"),
        (envelope(entities=tuple(("t%d" % i, ("v:1",)) for i in range(MAX_ENTITY_CITATIONS + 1))), "JSON contract"),
        (envelope(entities=(("", ("v:1",)),)), "JSON contract"),
        (envelope(intent=(" ",)), "non-blank ids"),
        (envelope(intent=("v:1", " ", "v:1")), "non-blank ids"),
        (envelope(entities=(("time", ("v:1", " ")),)), "cannot be blank"),
        ('{"schema":"%s","schema":"%s","answer":{},"citations":{"intent":[],"entities":[]}}'
         % (CITED_ANSWER_RESPONSE_FORMAT_ID, CITED_ANSWER_RESPONSE_FORMAT_ID), "repeats a JSON key"),
        ('{"schema":"%s","answer":{"x":NaN},"citations":{"intent":[],"entities":[]}}'
         % CITED_ANSWER_RESPONSE_FORMAT_ID, "nonfinite"),
        (envelope()[:-3], "JSON contract"),
    ),
)
def test_the_parser_rejects_without_repair(text, reason):
    with pytest.raises(SolverCitationError, match=reason):
        parse_cited_answer(text)


def test_the_static_and_specialised_formats_are_valid_schemas_over_the_same_envelope():
    static = cited_answer_response_format()
    specialised = cited_answer_response_format_for(SUPPLIED)
    empty = cited_answer_response_format_for(())
    for document in (static, specialised, empty):
        assert document["type"] == "json_schema"
        assert document["json_schema"]["name"] == "saea_solver_cited_answer_v1"
        Draft202012Validator.check_schema(document["json_schema"]["schema"])
        assert "uniqueItems" not in json.dumps(document)
    citations = specialised["json_schema"]["schema"]["properties"]["citations"]["properties"]
    assert citations["intent"]["items"] == {"type": "string", "enum": list(SUPPLIED)}
    assert citations["intent"]["maxItems"] == MAX_INTENT_CITATIONS
    entity = citations["entities"]["items"]["properties"]["evidence_ids"]
    assert entity["items"] == {"type": "string", "enum": list(SUPPLIED)}
    assert entity["maxItems"] == MAX_EVIDENCE_IDS_PER_ENTITY
    static_items = static["json_schema"]["schema"]["properties"]["citations"]["properties"]["intent"]["items"]
    assert "enum" not in static_items and static_items["type"] == "string"
    empty_intent = empty["json_schema"]["schema"]["properties"]["citations"]["properties"]["intent"]
    assert empty_intent == {"type": "array", "maxItems": 0}
    # The specialisation admits a citing envelope over supplied ids and
    # excludes an unsupplied id at the schema level (what the grammar enforces).
    validator = Draft202012Validator(specialised["json_schema"]["schema"])
    validator.validate(json.loads(envelope()))
    with pytest.raises(ValidationError):
        validator.validate(json.loads(envelope(intent=("value:never",))))
    with pytest.raises(SolverCitationError, match="unique non-empty"):
        cited_answer_response_format_for(("value:a", "value:a"))


# The COMP-1 abort shape (docs/results/2026-09-28-slurp-comp1-citation-abort-
# diagnosis.md): a grammar-valid, stop-finished envelope whose intent list is
# ONE supplied id three times (3 items, 1 distinct) beside cited entities.
COMP1_ABORT_SHAPE = envelope(intent=("value:a", "value:a", "value:a"))


def test_the_specialised_grammar_admits_a_repeated_id():
    # Root cause: the per-contact format enumerates supplied ids but cannot
    # say "unique", so the constrained decoder may legally repeat one.
    specialised = cited_answer_response_format_for(SUPPLIED)["json_schema"]["schema"]
    Draft202012Validator(specialised).validate(json.loads(COMP1_ABORT_SHAPE))


def test_a_repeated_intent_id_is_collapsed_and_counted_not_refused():
    parsed = parse_cited_answer(COMP1_ABORT_SHAPE)
    assert parsed.answer_text == ANSWER
    assert parsed.intent_evidence_ids == ("value:a",)
    assert parsed.duplicate_ids_dropped == 2
    assert parsed.cited_value_ids == ("value:a", "key:b", "value:c")
    # Everything but the count equals the envelope without the repeat.
    clean = parse_cited_answer(envelope())
    assert clean.duplicate_ids_dropped == 0
    assert (parsed.answer_text, parsed.intent_evidence_ids, parsed.entity_citations) == (
        clean.answer_text, clean.intent_evidence_ids, clean.entity_citations,
    )


def test_a_repeated_entity_id_is_collapsed_and_counted_not_refused():
    parsed = parse_cited_answer(
        envelope(intent=("value:a", "value:a"), entities=(("time", ("key:b", "key:b", "value:c")),))
    )
    assert parsed.intent_evidence_ids == ("value:a",)
    assert parsed.entity_citations[0].evidence_ids == ("key:b", "value:c")
    assert parsed.duplicate_ids_dropped == 2


def test_bind_seals_the_comp1_abort_shape_and_records_the_collapse():
    capture = bind_cited_completion(
        COMP1_ABORT_SHAPE, finish_reason="stop", supplied_value_ids=SUPPLIED,
        contact_id="c:solver:s1", role_id="solver",
        response_text_sha256=_sha(COMP1_ABORT_SHAPE),
    )
    assert capture.state_content == ANSWER
    assert capture.cited_value_ids == ("value:a", "key:b", "value:c")
    assert capture.record["parse"] == "ok"
    assert capture.record["intent_evidence_ids"] == ["value:a"]
    assert capture.record["duplicate_citation_ids_dropped"] == 2
    # A record without a repeat carries no new key: byte-identical to before.
    clean = bind_cited_completion(
        envelope(), finish_reason="stop", supplied_value_ids=SUPPLIED,
        contact_id="c:solver:s1", role_id="solver", response_text_sha256=_sha(envelope()),
    )
    assert "duplicate_citation_ids_dropped" not in clean.record
    # A repeat of an UNSUPPLIED id is still refused, never dropped.
    with pytest.raises(SolverCitationError, match="never supplied"):
        bind_cited_completion(
            envelope(intent=("value:never", "value:never")), finish_reason="stop",
            supplied_value_ids=SUPPLIED, contact_id="c", role_id="solver",
            response_text_sha256=_sha(ANSWER),
        )


def test_the_unwrap_delivers_the_comp1_abort_shape_like_the_seal():
    outcome = DELIVERY_NORMALISERS.resolve(DELIVER_CITED_ANSWER_V1)(COMP1_ABORT_SHAPE)
    assert outcome.text == ANSWER
    assert outcome.receipt["applied"] is True


def test_a_citation_of_unsupplied_evidence_is_refused_not_dropped():
    parsed = parse_cited_answer(envelope(intent=("value:a", "value:never")))
    with pytest.raises(SolverCitationError, match=r"1 evidence id\(s\) this contact never supplied"):
        validate_citations_supplied(parsed, SUPPLIED)
    validate_citations_supplied(parse_cited_answer(envelope()), SUPPLIED)


def test_bind_seals_the_answer_bytes_and_the_union_and_records_the_contact():
    text = envelope()
    capture = bind_cited_completion(
        text, finish_reason="stop", supplied_value_ids=SUPPLIED,
        contact_id="c:solver:s1", role_id="solver", response_text_sha256=_sha(text),
    )
    assert capture.state_content == ANSWER
    assert capture.cited_value_ids == ("value:a", "key:b", "value:c")
    record = capture.record
    assert record["parse"] == "ok"
    assert record["supplied_value_ids"] == list(SUPPLIED)
    assert record["cited_value_ids"] == ["value:a", "key:b", "value:c"]
    assert record["intent_evidence_ids"] == ["value:a"]
    assert record["entity_citations"] == [{"type": "time", "evidence_ids": ["key:b", "value:c"]}]
    assert record["answer_sha256"] == _sha(ANSWER)
    assert record["response_text_sha256"] == _sha(text)
    with pytest.raises(SolverCitationError, match="never supplied"):
        bind_cited_completion(
            envelope(intent=("value:never",)), finish_reason="stop", supplied_value_ids=SUPPLIED,
            contact_id="c", role_id="solver", response_text_sha256=_sha(text),
        )
    with pytest.raises(SolverCitationError, match="JSON contract"):
        bind_cited_completion(
            ANSWER, finish_reason="stop", supplied_value_ids=SUPPLIED,
            contact_id="c", role_id="solver", response_text_sha256=_sha(ANSWER),
        )


def test_a_non_stop_finish_is_sealed_verbatim_without_a_citation():
    truncated = envelope()[:40]
    capture = bind_cited_completion(
        truncated, finish_reason="length", supplied_value_ids=SUPPLIED,
        contact_id="c", role_id="solver", response_text_sha256=_sha(truncated),
    )
    assert capture.state_content == truncated
    assert capture.cited_value_ids == ()
    assert capture.record["parse"] == "non-authoritative-finish"
    assert capture.record["finish_reason"] == "length"
    assert capture.record["cited_value_ids"] == [] and capture.record["answer_sha256"] is None


# ---------------------------------------------------------------------------
# Delivery custody (I7n): the registered unwrap and its v3 composition
# ---------------------------------------------------------------------------

INVENTORY = legal_intent_inventory({"alarm": ("set", "remove", "query")})


@pytest.fixture
def _synthetic_inventory(monkeypatch):
    monkeypatch.setattr(v3, "_default_legal_intent_inventory", lambda: INVENTORY)


def test_the_unwrap_normalisers_are_registered_with_identity_and_carrier():
    for name in (DELIVER_CITED_ANSWER_V1, DELIVER_CITED_ANSWER_NORMALISE_V3_V1):
        entry = DELIVERY_NORMALISERS.resolve(name)
        assert entry.id == name and entry.version == "1" and entry.carrier_lock_key == "slurp"


def test_the_unwrap_delivers_the_answers_own_bytes_and_binds_its_receipt():
    text = envelope()
    unwrap = DELIVERY_NORMALISERS.resolve(DELIVER_CITED_ANSWER_V1)
    outcome = unwrap(text)
    assert outcome.text == ANSWER and outcome.changed is True
    receipt = outcome.receipt
    assert receipt["schema"] == DELIVER_NORMALISER_RECEIPT_SCHEMA
    assert receipt["normaliser_id"] == DELIVER_CITED_ANSWER_V1
    assert receipt["rule_id"] == "cited-answer-unwrap-v1"
    assert receipt["applied"] is True and receipt["reason"] is None
    assert receipt["input_sha256"] == _sha(text) and receipt["output_sha256"] == _sha(ANSWER)
    assert receipt["cited_value_ids_count"] == 3
    assert receipt["cited_value_ids_sha256"] == _sha(json.dumps(["value:a", "key:b", "value:c"]))
    assert unwrap(text).text == outcome.text  # deterministic
    # Text the contract refuses is delivered verbatim with the reason recorded.
    passthrough = unwrap(ANSWER)
    assert passthrough.text == ANSWER and passthrough.changed is False
    assert passthrough.receipt["applied"] is False and "JSON contract" in passthrough.receipt["reason"]
    assert passthrough.receipt["cited_value_ids_count"] == 0
    with pytest.raises(TypeError):
        unwrap(None)


def test_the_v3_composition_is_v3_over_the_unwrapped_answer(_synthetic_inventory):
    text = envelope()
    composed = DELIVERY_NORMALISERS.resolve(DELIVER_CITED_ANSWER_NORMALISE_V3_V1)
    unwrap = DELIVERY_NORMALISERS.resolve(DELIVER_CITED_ANSWER_V1)
    projection = DELIVERY_NORMALISERS.resolve(DELIVER_NORMALISE_V3)
    outcome = composed(text)
    expected = projection(unwrap(text).text)
    assert outcome.text == expected.text
    assert outcome.text != ANSWER  # the filler rule repairs "6:30AM"
    receipt = outcome.receipt
    assert receipt["normaliser_id"] == DELIVER_CITED_ANSWER_NORMALISE_V3_V1
    assert receipt["rule_id"] == "cited-answer-unwrap-then-slurp-use-projection-v3"
    assert receipt["input_sha256"] == _sha(text)
    assert receipt["output_sha256"] == _sha(outcome.text)
    assert receipt["applied"] is True and receipt["changed"] is True
    assert receipt["fillers_changed"] == expected.receipt["fillers_changed"] == 1
    assert [stage["normaliser_id"] for stage in receipt["stages"]] == [
        DELIVER_CITED_ANSWER_V1, DELIVER_NORMALISE_V3,
    ]
    assert receipt["stages"][0]["output_sha256"] == receipt["stages"][1]["input_sha256"] == _sha(ANSWER)
    assert composed(text).text == outcome.text  # deterministic
    # Applied to its own output the composition is a fixed point: the
    # unwrap passes a plain answer through and v3 is idempotent.
    assert composed(outcome.text).text == outcome.text


# ---------------------------------------------------------------------------
# Loader pairing: contract <=> unwrapping normaliser, Solver only
# ---------------------------------------------------------------------------


def _program(**formats):
    return PhaseProgram(
        program_id="phase-native-role-cited-test",
        phases=tuple(
            PhaseSpec(name, name, "none", formats.get(name), False)
            for name in ("perception", "reviewer", "planner", "solver")
        ),
        max_contacts=4, stop_rule="native-role-episode",
    ).validate()


def _values(normaliser=None):
    values = _episode_values()
    values["carrier_lock_key"] = "slurp"
    if normaliser is not None:
        values["native_episode"]["deliver_normaliser"] = {"normaliser": normaliser}
    return values


def test_the_loader_accepts_the_pairing_and_leaves_the_off_arm_untouched():
    off = load_native_episode_config(_values(), _program())
    assert off.deliver_normaliser_id is None
    for normaliser in (DELIVER_CITED_ANSWER_V1, DELIVER_CITED_ANSWER_NORMALISE_V3_V1):
        on = load_native_episode_config(
            _values(normaliser), _program(solver=CITED_ANSWER_RESPONSE_FORMAT_ID)
        )
        assert on.deliver_normaliser_id == normaliser
        assert on.max_contacts == off.max_contacts


def test_the_loader_refuses_the_contract_without_its_normaliser_and_vice_versa():
    with pytest.raises(ValueError, match="requires native_episode.deliver_normaliser"):
        load_native_episode_config(_values(), _program(solver=CITED_ANSWER_RESPONSE_FORMAT_ID))
    with pytest.raises(ValueError, match="requires native_episode.deliver_normaliser"):
        load_native_episode_config(
            _values(DELIVER_NORMALISE_V3), _program(solver=CITED_ANSWER_RESPONSE_FORMAT_ID)
        )
    with pytest.raises(ValueError, match="Solver phase must declare"):
        load_native_episode_config(_values(DELIVER_CITED_ANSWER_V1), _program())
    with pytest.raises(ValueError, match="Solver phase only"):
        load_native_episode_config(
            _values(DELIVER_CITED_ANSWER_V1),
            _program(reviewer=CITED_ANSWER_RESPONSE_FORMAT_ID, solver=CITED_ANSWER_RESPONSE_FORMAT_ID),
        )


def test_the_committed_cited_program_declares_the_contract_on_the_solver_only():
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program

    program = default_phase_program("phase-native-candidates-review-revise-cited-v1")
    base = default_phase_program("phase-native-candidates-review-revise-v1")
    assert [phase.response_format_id for phase in program.phases] == [
        "slurp-intent-hypotheses-v1", None, None, CITED_ANSWER_RESPONSE_FORMAT_ID,
    ]
    assert program.max_contacts == base.max_contacts == 11
    assert [phase.name for phase in program.phases] == [phase.name for phase in base.phases]


# ---------------------------------------------------------------------------
# The seal round trip
# ---------------------------------------------------------------------------


def test_the_sealed_state_carries_the_citation_and_binds_the_raw_envelope():
    text = envelope()
    capture = bind_cited_completion(
        text, finish_reason="stop", supplied_value_ids=SUPPLIED,
        contact_id="c:solver:s1", role_id="solver", response_text_sha256=_sha(text),
    )
    state = seal_phase_response_state(
        phase_name="solver", sample_id="s1", state_content=capture.state_content,
        raw_response_text=text, source_query_state_sha256="a" * 64,
        producer_policy_id="p", state_namespace="c", cited_value_ids=capture.cited_value_ids,
    )
    assert state.content == ANSWER
    assert state.source_response_sha256 == _sha(text)
    assert state.cited_value_ids == ("value:a", "key:b", "value:c")
    document = state.as_json()
    assert document["cited_value_ids"] == ["value:a", "key:b", "value:c"]
    assert AgentStateArtifact.from_json(document) == state
    bare = seal_phase_response_state(
        phase_name="solver", sample_id="s1", state_content=capture.state_content,
        raw_response_text=text, source_query_state_sha256="a" * 64,
        producer_policy_id="p", state_namespace="c",
    )
    assert bare.cited_value_ids == () and bare.content_hash() != state.content_hash()


# ---------------------------------------------------------------------------
# The credit read
# ---------------------------------------------------------------------------

ROWS = (
    CitationRow("s1", ("e1", "e2", "e3"), ("e1",), True),
    CitationRow("s2", ("e1", "e2"), ("e1", "e2"), False),
    CitationRow("s3", ("e2", "e3"), (), True),
    CitationRow("s4", ("e1", "e3"), ("e3",), True),
)


def test_the_credit_table_counts_each_entry_and_is_byte_reproducible():
    table = credit_table(ROWS)
    assert table["schema"] == CREDIT_TABLE_SCHEMA
    assert table["entries"] == [
        {"value_id": "e1", "supplied": 3, "cited": 2, "cited_correct": 1, "supplied_uncited": 1},
        {"value_id": "e2", "supplied": 3, "cited": 1, "cited_correct": 0, "supplied_uncited": 2},
        {"value_id": "e3", "supplied": 3, "cited": 1, "cited_correct": 1, "supplied_uncited": 2},
    ]
    assert table["totals"] == {
        "rows": 4, "rows_correct": 3, "entries": 3, "supplied_slots": 9, "citations": 4,
    }
    shuffled = list(ROWS)
    random.Random(7).shuffle(shuffled)
    again = credit_table(shuffled)
    assert render_credit_table(again) == render_credit_table(table)
    assert again["table_sha256"] == table["table_sha256"] == hashlib.sha256(
        json.dumps(table["entries"], ensure_ascii=False, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def test_the_credit_table_refuses_what_the_seal_would_have_refused():
    with pytest.raises(CitationCreditError, match="never supplied"):
        credit_table([CitationRow("s1", ("e1",), ("e9",), True)])
    with pytest.raises(CitationCreditError, match="appears twice"):
        credit_table([ROWS[0], ROWS[0]])
    with pytest.raises(CitationCreditError, match="must be a bool"):
        CitationRow("s1", ("e1",), (), 1).validate()


def _outputs_row(sample_id, *, contact, supplied, cited, parse="ok", delivered=None):
    receipt = {
        "accepted_solver_receipt": {"final_contact": {"agent_contact_id": delivered or contact}},
        "solver_citations": {
            "schema": "saea-solver-citations-v1",
            "response_format_id": CITED_ANSWER_RESPONSE_FORMAT_ID,
            "contacts": [{
                "contact_id": contact, "role_id": "solver", "parse": parse,
                "supplied_value_ids": list(supplied), "cited_value_ids": list(cited),
            }],
        },
    }
    return {"sample_id": sample_id, "final_response_text": "", "native_episode_receipt": receipt}


def test_rows_are_read_from_a_sealed_outputs_file_and_the_cli_writes_the_table(tmp_path):
    outputs = tmp_path / "outputs.jsonl"
    rows = [
        _outputs_row("s1", contact="c1:solver:s1", supplied=("e1", "e2"), cited=("e1",)),
        _outputs_row("s2", contact="c1:solver:s2", supplied=("e1", "e2"), cited=("e2",),
                     delivered="c2:solver:s2"),  # delivered contact has no record: skipped
        _outputs_row("s3", contact="c1:solver:s3", supplied=("e2",), cited=(), parse="non-authoritative-finish"),
        {"sample_id": "s4", "final_response_text": "", "native_episode_receipt": {}},  # un-armed
    ]
    outputs.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    correctness = tmp_path / "correct.json"
    correctness.write_text(json.dumps({"s1": True, "s2": False, "s3": True}), encoding="utf-8")
    read, counts = rows_from_outputs(outputs, {"s1": True, "s2": False, "s3": True})
    assert [row.sample_id for row in read] == ["s1"]
    assert counts == {"outputs_rows": 4, "rows": 1, "skipped": 2, "unarmed": 1}
    with pytest.raises(CitationCreditError, match="no correctness entry"):
        rows_from_outputs(outputs, {})
    out = tmp_path / "table.json"
    assert credit_main(["--outputs", str(outputs), "--correctness", str(correctness), "--out", str(out)]) == 0
    table = json.loads(out.read_text(encoding="utf-8"))
    assert table["entries"] == [
        {"value_id": "e1", "supplied": 1, "cited": 1, "cited_correct": 1, "supplied_uncited": 0},
        {"value_id": "e2", "supplied": 1, "cited": 0, "cited_correct": 0, "supplied_uncited": 1},
    ]
    rows_file = tmp_path / "rows.jsonl"
    rows_file.write_text("".join(json.dumps(row.as_json()) + "\n" for row in ROWS), encoding="utf-8")
    out2 = tmp_path / "table2.json"
    assert credit_main(["--rows", str(rows_file), "--out", str(out2)]) == 0
    assert json.loads(out2.read_text(encoding="utf-8"))["table_sha256"] == credit_table(ROWS)["table_sha256"]


# ---------------------------------------------------------------------------
# Per-arm credit (owner decision 172, docs/superpowers/specs/2026-09-27-same-flight-supply-
# variant-instrument-design.md section 5, item 2): key (arm_id, value_id), correctness from
# each arm's OWN official per-row score.
# ---------------------------------------------------------------------------

ARM_ROWS = (
    ArmCitationRow("s1", "twin", ("e1", "e2"), ("e1",), True),
    ArmCitationRow("s1", "plan", ("e1", "e3"), ("e1", "e3"), True),
    ArmCitationRow("s2", "twin", ("e1", "e2"), ("e2",), False),
    ArmCitationRow("s2", "plan", ("e1", "e3"), ("e1",), False),
)


def test_the_arm_credit_table_keys_by_arm_and_value_and_is_byte_reproducible():
    table = arm_credit_table(ARM_ROWS)
    assert table["schema"] == CREDIT_TABLE_PER_ARM_SCHEMA
    assert table["entries"] == [
        {"arm_id": "plan", "value_id": "e1", "supplied": 2, "cited": 2, "cited_correct": 1,
         "supplied_uncited": 0},
        {"arm_id": "plan", "value_id": "e3", "supplied": 2, "cited": 1, "cited_correct": 1,
         "supplied_uncited": 1},
        {"arm_id": "twin", "value_id": "e1", "supplied": 2, "cited": 1, "cited_correct": 1,
         "supplied_uncited": 1},
        {"arm_id": "twin", "value_id": "e2", "supplied": 2, "cited": 1, "cited_correct": 0,
         "supplied_uncited": 1},
    ]
    assert table["totals"] == {
        "rows": 4, "rows_correct": 2, "entries": 4, "supplied_slots": 8, "citations": 5,
    }
    # order independence, exactly as the per-value_id table promises.
    shuffled = list(ARM_ROWS)
    random.Random(3).shuffle(shuffled)
    again = arm_credit_table(shuffled)
    assert render_arm_credit_table(again) == render_arm_credit_table(table)
    assert again["table_sha256"] == table["table_sha256"]
    # a same-flight table never collapses two arms' identical value ids into one row: "e1" is
    # supplied by both "twin" and "plan" and each keeps its own count.
    assert {(e["arm_id"], e["value_id"]) for e in table["entries"]} == {
        ("plan", "e1"), ("plan", "e3"), ("twin", "e1"), ("twin", "e2"),
    }


def test_the_arm_credit_table_refuses_a_repeated_arm_sample_pair_and_reuses_citation_rows_checks():
    with pytest.raises(CitationCreditError, match="appears twice"):
        arm_credit_table([ARM_ROWS[0], ARM_ROWS[0]])
    with pytest.raises(CitationCreditError, match="never supplied"):
        ArmCitationRow("s1", "twin", ("e1",), ("e9",), True).validate()
    with pytest.raises(CitationCreditError, match="needs an arm id"):
        ArmCitationRow("s1", "", ("e1",), (), True).validate()


def _citation_row(sample_id, arm_id, *, supplied, cited, ok=True):
    return {
        "sample_id": sample_id, "arm_id": arm_id,
        "supplied_value_ids": list(supplied), "cited_value_ids": list(cited),
        "cited_value_ids_ok": ok, "response_format_id": CITED_ANSWER_RESPONSE_FORMAT_ID,
    }


def test_arm_rows_are_read_from_the_renderers_citation_rows_and_joined_with_per_arm_correctness(
    tmp_path,
):
    path = tmp_path / "arm-citation-rows.jsonl"
    rows = [
        _citation_row("s1", "twin", supplied=("e1", "e2"), cited=("e1",)),
        _citation_row("s1", "plan", supplied=("e1", "e3"), cited=("e1", "e3")),
        # this arm's own contact never carried a parseable envelope: skipped, not invented.
        _citation_row("s2", "twin", supplied=("e2",), cited=(), ok=False),
        # "plan" has no correctness entry for s3: counted missing, never silently dropped.
        _citation_row("s3", "plan", supplied=("e1",), cited=("e1",)),
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    correctness_by_arm = {"twin": {"s1": True}, "plan": {"s1": True}}
    read, counts = arm_rows_from_citation_rows(path, correctness_by_arm)
    assert [(row.sample_id, row.arm_id) for row in read] == [("s1", "twin"), ("s1", "plan")]
    assert counts == {"citation_rows": 4, "rows": 2, "skipped": 1, "missing_correctness": 1}

    correctness_path = tmp_path / "correctness-by-arm.json"
    correctness_path.write_text(json.dumps(correctness_by_arm), encoding="utf-8")
    assert load_correctness_by_arm(correctness_path) == correctness_by_arm
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps({"twin": {"s1": "yes"}}), encoding="utf-8")
    with pytest.raises(CitationCreditError, match="correctness-by-arm"):
        load_correctness_by_arm(bad_path)

    out = tmp_path / "arm-table.json"
    assert credit_main([
        "--arm-citation-rows", str(path), "--correctness-by-arm", str(correctness_path),
        "--out", str(out),
    ]) == 0
    table = json.loads(out.read_text(encoding="utf-8"))
    assert table["schema"] == CREDIT_TABLE_PER_ARM_SCHEMA
    assert table["entries"] == [
        {"arm_id": "plan", "value_id": "e1", "supplied": 1, "cited": 1, "cited_correct": 1,
         "supplied_uncited": 0},
        {"arm_id": "plan", "value_id": "e3", "supplied": 1, "cited": 1, "cited_correct": 1,
         "supplied_uncited": 0},
        {"arm_id": "twin", "value_id": "e1", "supplied": 1, "cited": 1, "cited_correct": 1,
         "supplied_uncited": 0},
        # "twin" was SUPPLIED e2 but never cited it (it only cited e1): the entry still appears,
        # with cited 0, exactly as the per-value_id table lists every supplied id.
        {"arm_id": "twin", "value_id": "e2", "supplied": 1, "cited": 0, "cited_correct": 0,
         "supplied_uncited": 1},
    ]

    arm_rows_file = tmp_path / "arm-rows.jsonl"
    arm_rows_file.write_text(
        "".join(json.dumps(row.as_json()) + "\n" for row in ARM_ROWS), encoding="utf-8"
    )
    assert [row.as_json() for row in load_arm_rows(arm_rows_file)] == [
        row.as_json() for row in ARM_ROWS
    ]


def test_the_cli_refuses_an_ambiguous_or_incomplete_mode_selection(tmp_path):
    out = tmp_path / "out.json"
    with pytest.raises(SystemExit):
        credit_main(["--out", str(out)])
    rows_file = tmp_path / "rows.jsonl"
    rows_file.write_text("", encoding="utf-8")
    arm_rows_file = tmp_path / "arm-citation-rows.jsonl"
    arm_rows_file.write_text("", encoding="utf-8")
    correctness_by_arm = tmp_path / "correctness-by-arm.json"
    correctness_by_arm.write_text(json.dumps({}), encoding="utf-8")
    # two real modes named at once (--rows and --arm-citation-rows) is ambiguous.
    with pytest.raises(SystemExit):
        credit_main(["--rows", str(rows_file), "--arm-citation-rows", str(arm_rows_file),
                     "--correctness-by-arm", str(correctness_by_arm), "--out", str(out)])
    # --arm-citation-rows without --correctness-by-arm is an incomplete mode.
    with pytest.raises(SystemExit):
        credit_main(["--arm-citation-rows", str(arm_rows_file), "--out", str(out)])
