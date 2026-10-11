"""Proof obligations of the typed proposer seam (decision 263-A, E-T1).

Design: ``docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md``
sections 3.1-3.5 and 4.1. Every fixture is synthetic: no real utterance, gold
label or model output appears in this file.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.contracts import _parse_ledger_tables  # noqa: E402
from speech_aware_evidence_acquisition.core.base import (  # noqa: E402
    AGENT_CONTROLLERS,
    RESPONSE_FORMATS,
)
from speech_aware_evidence_acquisition.core.flight import runtime as flight_runtime  # noqa: E402
from speech_aware_evidence_acquisition.rails import controllers as _controllers  # noqa: E402,F401
from speech_aware_evidence_acquisition.rails import tfrl_typed_proposer as tp  # noqa: E402

TEMPLATE = (REPO_ROOT / "configs" / tp.TFRL_TYPED_TEMPLATE_RELPATH).read_text(encoding="utf-8")

SLOT_TYPES = ["date", "time", "place_name", "person", "event_name"]
INTENTS = ["alarm_set", "calendar_set", "weather_query"]


# ---------------------------------------------------------------------------
# Fixtures.
# ---------------------------------------------------------------------------


def make_tables(iteration: int = 1, *, extra: dict | None = None) -> dict:
    document = {
        "schema": tp.TABLES_SCHEMA_ID,
        "iteration": iteration,
        "enums": {
            "slot_types": SLOT_TYPES,
            "intents": INTENTS,
            "scenarios": list(tp.SCENARIOS),
        },
        "tables": {
            "failure_cube": {
                "columns": ["failure_class", "slot_type", "value_in_supply", "scenario",
                            "n_rows", "mass_pp"],
                "rows": [
                    ["MISSING", "date", "E1", "calendar", 41, 0.9],
                    ["SPURIOUS", "person", "none", "social", "<3", None],
                ],
            },
            "scenario_summary": {
                "columns": ["scenario", "n_rows", "slu", "intent_acc", "empty_share"],
                "rows": [["calendar", 90, 71.2, 88.1, 0.4]],
            },
            "state_credit": {
                "columns": ["state_id", "operator_class", "operator", "status", "d_slu_pp",
                            "d_slu_lo_pp", "d_slu_hi_pp", "d_intent_pp"],
                "rows": [["s0-lock", "none", "none", "accepted", 0.0, 0.0, 0.0, 0.0]],
            },
            "exchange_rates": {
                "columns": ["name", "pp"],
                "rows": [["missing_recovered", 0.062]],
            },
            "pool_after_selector": {
                "columns": ["scenario", "selector", "theta", "pool_size"],
                "rows": [
                    ["calendar", "entity-free-only", None, 120],
                    ["calendar", "slot-bearing-only", None, 0],
                    ["calendar", "drop-slot-bearing-if-entity-free-share", 0.5, 80],
                ],
            },
        },
    }
    if extra:
        document["tables"].update(extra)
    document["tables_sha256"] = tp.canonical_tables_sha256(document)
    return document


def make_context(iteration: int = 1) -> dict:
    return {
        "schema": tp.CONTEXT_SCHEMA_ID,
        "iteration": iteration,
        "parent_state_id": "s0-lock-v2.2",
        "archive_sha256": "a" * 64,
        "refused_buffer": [
            {"candidate_id": "c" * 16, "operator_class": "supply", "operator": "knob-set",
             "refusal_code": "refused-prediction", "predicted_slu_pp": 0.4},
        ],
        "meta_summary": {
            "supply": {"proposed": 1, "valid": 0, "flown": 0, "accepted": 0, "refused": 1,
                       "mean_realised_minus_predicted_pp": None},
        },
    }


ENUMS = tp.EnumContext(
    slot_types=tuple(SLOT_TYPES), intents=tuple(INTENTS), scenarios=tp.SCENARIOS
)


def make_archive(iteration: int = 1, **overrides) -> tp.ArchiveView:
    base = dict(
        iteration=iteration,
        parent_state_id="s0-lock-v2.2",
        known_state_ids=frozenset({"s0-lock-v2.2"}),
        entry_ids={"deliver-rule": frozenset({"rule-1"}), "slot-card": frozenset({"card-1"})},
    )
    base.update(overrides)
    return tp.ArchiveView(**base)


def target(**overrides) -> dict:
    base = {"failure_class": "MISSING", "slot_types": ["date"], "scenarios": ["calendar"],
            "value_in_supply": "E1"}
    base.update(overrides)
    return base


def candidate(operator_class: str, operator: str, applications: list, *, iteration: int = 1,
              **overrides) -> dict:
    base = {
        "schema": tp.CANDIDATE_SCHEMA_ID,
        "iteration": iteration,
        "parent_state_id": "s0-lock-v2.2",
        "operator_class": operator_class,
        "operator": operator,
        "target": target(),
        "hypothesis_code": "type-inventory",
        "applications": applications,
    }
    base.update(overrides)
    return base


EXEMPLAR = {"scenario": "calendar", "selector": "entity-free-only", "theta": None}
THETA_APP = {"scenario": "calendar", "selector": "drop-slot-bearing-if-entity-free-share",
             "theta": 0.5}
CARD = {"intent": "calendar_set", "drop_types": ["person"]}
KNOB = {"tail": "train-exemplars.phase_supply.solver.k", "value": 12}
RULE = {"family": "ee10", "guard": "wilson", "types": ["person"], "intents": []}
SCOPE_RULE = {"entry_kind": "deliver-rule", "entry_id": "rule-1", "scenarios": ["calendar"]}
SCOPE_CARD = {"entry_kind": "slot-card", "entry_id": "card-1", "scenarios": ["calendar"]}




class StubPredictor:
    def __init__(self, pp: float | None):
        self.pp = pp

    def predict(self, cand, cid):
        if self.pp is None:
            raise tp.PredictionUnavailable(cid)
        return tp.Prediction(self.pp, "stub")


def pools() -> dict:
    return tp.parse_tables(make_tables()).pool_sizes()


def run(cand, *, archive=None, pp: float | None = 2.0, **kwargs):
    return tp.validate_candidate(
        cand,
        enums=ENUMS,
        archive=archive or make_archive(),
        predictor=StubPredictor(pp),
        pool_sizes=pools(),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# 1. The schema has no free-text field and no effect field.
# ---------------------------------------------------------------------------


def _walk(node, path=""):
    if isinstance(node, dict):
        yield path, node
        for key, value in node.items():
            yield from _walk(value, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, f"{path}[{index}]")


def test_the_wire_schema_is_closed_and_has_no_free_text_or_effect_field():
    for enums in (None, ENUMS):
        schema = tp.candidate_schema(enums)
        text = json.dumps(schema)
        for banned in ("effect", "predicted", "rationale", "reason", "explanation", "score"):
            assert banned not in text
        for path, node in _walk(schema):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False, path
            if node.get("type") == "string":
                assert "enum" in node or "pattern" in node, f"free string at {path}"


def test_the_schema_enums_are_the_validator_vocabularies():
    schema = tp.candidate_schema(ENUMS)
    props = schema["properties"]
    assert props["operator_class"]["enum"] == list(tp.OPERATOR_CLASSES)
    assert props["operator"]["enum"] == list(tp.ALL_OPERATORS)
    assert props["hypothesis_code"]["enum"] == list(tp.HYPOTHESIS_CODES)
    assert props["target"]["properties"]["failure_class"]["enum"] == list(tp.FAILURE_CLASSES)
    assert props["target"]["properties"]["slot_types"]["items"]["enum"] == SLOT_TYPES
    assert len(tp.SCENARIOS) == 18
    assert "key-source" not in tp.ALL_OPERATORS


def test_the_registered_response_format_is_json_schema_and_caps_the_edit_budget():
    fmt = RESPONSE_FORMATS.resolve(tp.TFRL_TYPED_RESPONSE_FORMAT_ID)({}, REPO_ROOT, iteration=2)
    assert fmt["type"] == "json_schema" and fmt["json_schema"]["strict"] is True
    schema = fmt["json_schema"]["schema"]
    assert schema["properties"]["applications"]["maxItems"] == 1
    assert schema["properties"]["iteration"]["enum"] == [2]
    default = RESPONSE_FORMATS.resolve(tp.TFRL_TYPED_RESPONSE_FORMAT_ID)({}, REPO_ROOT)
    assert default["json_schema"]["schema"]["properties"]["applications"]["maxItems"] == 2
    from speech_aware_evidence_acquisition.rails import tfrl_ace_material

    ace = RESPONSE_FORMATS.resolve(tp.TFRL_ACE_RESPONSE_FORMAT_ID)({}, REPO_ROOT)
    assert ace["type"] == "json_schema"
    assert ace == tfrl_ace_material.response_format()  # one schema, one owner


def test_both_programs_and_controllers_are_registered():
    for program_id, phase, fmt in (
        (tp.TFRL_TYPED_PROGRAM_ID, tp.TFRL_TYPED_PHASE_NAME, tp.TFRL_TYPED_RESPONSE_FORMAT_ID),
        (tp.TFRL_ACE_PROGRAM_ID, tp.TFRL_ACE_PHASE_NAME, tp.TFRL_ACE_RESPONSE_FORMAT_ID),
    ):
        program = _controllers.default_phase_program(program_id)
        assert [p.name for p in program.phases] == [phase]
        assert program.max_contacts == 1
        assert program.phases[0].response_format_id == fmt
        assert program.phases[0].knowledge == "none"
        assert program_id in set(AGENT_CONTROLLERS.names())
        assert fmt in set(RESPONSE_FORMATS.names())


# ---------------------------------------------------------------------------
# 2. Accept and refuse, per operator class.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("cls", "operator", "apps", "read"),
    [
        ("construction", "exemplar-selection", [EXEMPLAR, THETA_APP], "sf"),
        ("construction", "slot-card-subset", [CARD], "sf"),
        ("supply", "knob-set", [KNOB], "sf"),
        ("delivery", "deliver-rule", [RULE], "offline"),
        ("scope", "scope-restrict", [SCOPE_RULE], "offline"),
        ("scope", "scope-restrict", [SCOPE_CARD], "sf"),
    ],
)
def test_a_legal_candidate_of_each_operator_class_is_accepted(cls, operator, apps, read):
    result = run(candidate(cls, operator, apps))
    assert result.accepted, result.refusals
    assert result.read == read
    assert result.candidate_id == tp.candidate_id(candidate(cls, operator, apps))


def test_delivery_and_rule_scope_candidates_are_not_gated_by_a_prediction():
    for cls, operator, apps in (("delivery", "deliver-rule", [RULE]),
                                ("scope", "scope-restrict", [SCOPE_RULE])):
        result = tp.validate_candidate(
            candidate(cls, operator, apps), enums=ENUMS, archive=make_archive(), predictor=None
        )
        assert result.accepted and result.prediction is None


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda c: c.update(operator_class="construction"), "class-operator-mismatch"),
        (lambda c: c["target"].update(slot_types=["not_a_slot"]), "enum"),
        (lambda c: c["target"].update(failure_class="EVERYTHING"), "enum"),
        (lambda c: c.update(hypothesis_code="because"), "enum"),
        (lambda c: c.pop("hypothesis_code"), "schema"),
        (lambda c: c.update(extra_field=1), "schema"),
        (lambda c: c.update(applications=[]), "schema"),
        (lambda c: c.update(iteration=2), "iteration-mismatch"),
        (lambda c: c.update(parent_state_id="s9-unknown"), "unknown-parent"),
    ],
)
def test_structural_refusals_are_named(mutate, code):
    cand = candidate("supply", "knob-set", [KNOB])
    mutate(cand)
    result = run(cand)
    assert not result.accepted
    assert code in result.codes


def test_operator_argument_spaces_are_closed():
    cases = [
        ("construction", "exemplar-selection", [{**EXEMPLAR, "scenario": "nowhere"}], "enum"),
        ("construction", "exemplar-selection", [{**EXEMPLAR, "selector": "everything"}], "enum"),
        ("construction", "exemplar-selection", [{**THETA_APP, "theta": 0.55}], "enum"),
        ("construction", "exemplar-selection", [{**EXEMPLAR, "theta": 0.5}], "schema"),
        ("construction", "slot-card-subset", [{**CARD, "intent": "made_up"}], "enum"),
        ("construction", "slot-card-subset", [{**CARD, "drop_types": []}], "schema"),
        ("construction", "slot-card-subset", [{**CARD, "drop_types": ["person", "person"]}], "schema"),
        ("supply", "knob-set", [{"tail": "train-exemplars.phase_supply.solver.q", "value": 3}], "enum"),
        ("supply", "knob-set", [{**KNOB, "value": 0}], "knob-range"),
        ("supply", "knob-set", [{**KNOB, "value": 61}], "knob-range"),
        ("supply", "knob-set", [{**KNOB, "value": True}], "knob-range"),
        ("supply", "knob-set",
         [{"tail": "slot-contracts.candidate_supply.solver.max_candidates", "value": 3}],
         "knob-range"),
        ("delivery", "deliver-rule", [{**RULE, "family": "free-form"}], "enum"),
        ("delivery", "deliver-rule", [{**RULE, "guard": "strict"}], "enum"),
        ("delivery", "deliver-rule", [{**RULE, "types": [], "intents": []}], "schema"),
        ("delivery", "deliver-rule", [{**RULE, "threshold": 0.5}], "schema"),
        ("scope", "scope-restrict", [{**SCOPE_RULE, "entry_kind": "template"}], "enum"),
        ("scope", "scope-restrict", [{**SCOPE_RULE, "scenarios": []}], "schema"),
        ("scope", "scope-restrict", [{**SCOPE_RULE, "entry_id": "rule-404"}], "enum"),
    ]
    for cls, operator, apps, code in cases:
        result = run(candidate(cls, operator, apps))
        assert not result.accepted and code in result.codes, (operator, apps, result.refusals)


def test_not_json_and_non_object_answers_are_refused_without_raising():
    for text in ("", "not json", "[1, 2]", b"\xff\xfe", "null"):
        result = tp.validate_candidate(text, enums=ENUMS, archive=make_archive())
        assert not result.accepted and result.codes == ("not-json",)
    parsed = tp.validate_candidate(
        json.dumps(candidate("delivery", "deliver-rule", [RULE])),
        enums=ENUMS, archive=make_archive(),
    )
    assert parsed.accepted


# ---------------------------------------------------------------------------
# 3. L_t, class masking, second-store swap, pools, duplicates, no-ops.
# ---------------------------------------------------------------------------


def test_the_edit_budget_is_two_then_one():
    assert [tp.edit_budget(t) for t in (1, 2, 3)] == [2, 1, 1]
    two = candidate("supply", "knob-set", [KNOB, {**KNOB, "value": 14}])
    assert run(two).accepted
    over = candidate("supply", "knob-set",
                     [KNOB, {**KNOB, "value": 14}, {**KNOB, "value": 16}])
    assert "edit-budget" in run(over).codes
    second = candidate("supply", "knob-set", [KNOB, {**KNOB, "value": 14}], iteration=2)
    result = run(second, archive=make_archive(2))
    assert not result.accepted and "edit-budget" in result.codes
    one = candidate("supply", "knob-set", [KNOB], iteration=3)
    assert run(one, archive=make_archive(3)).accepted


def test_decision_245_refuses_any_node_prompt_or_template_change():
    cand = candidate("supply", "knob-set", [KNOB])
    for key in ("node_prompt", "template", "instruction", "statement", "note_contract"):
        bad = {**cand, key: "x"}
        assert run(bad).codes == ("node-prompt-change-245",), key
    nested = copy.deepcopy(cand)
    nested["applications"][0]["prompt"] = "x"
    assert run(nested).codes == ("node-prompt-change-245",)
    for operator in ("edit-node-prompt", "template-swap", "note-contract-edit"):
        bad = candidate("supply", operator, [KNOB])
        assert run(bad).codes == ("node-prompt-change-245",), operator


def test_disabled_and_deferred_operators_are_refused_by_name():
    for operator in ("key-source", "per-scenario-k"):
        result = run(candidate("construction", operator, [KNOB]))
        assert result.codes == ("disabled-operator",)


def test_a_masked_class_and_a_disallowed_class_are_refused():
    cand = candidate("supply", "knob-set", [KNOB])
    assert "class-masked" in run(cand, archive=make_archive(masked_classes=frozenset({"supply"}))).codes
    assert "class-not-allowed" in run(cand, allowed_classes=["construction"]).codes
    assert run(cand, allowed_classes=["supply"]).accepted


def test_a_second_release_store_swap_needs_the_multi_store_build():
    card = candidate("construction", "slot-card-subset", [CARD])
    parent = make_archive(parent_stores=frozenset({"train-exemplars"}))
    assert "second-store-swap" in run(card, archive=parent).codes
    built = make_archive(parent_stores=frozenset({"train-exemplars"}), release_swaps_supported=True)
    assert run(card, archive=built).accepted
    same = make_archive(parent_stores=frozenset({"slot-contracts"}))
    assert run(card, archive=same).accepted


def test_a_selection_that_empties_a_pool_or_has_no_pool_figure_is_refused():
    empty = candidate("construction", "exemplar-selection",
                      [{"scenario": "calendar", "selector": "slot-bearing-only", "theta": None}])
    assert "empty-pool" in run(empty).codes
    unknown = candidate("construction", "exemplar-selection",
                        [{"scenario": "weather", "selector": "entity-free-only", "theta": None}])
    assert "pool-size-unknown" in run(unknown).codes


def test_duplicates_and_no_ops_are_refused():
    cand = candidate("supply", "knob-set", [KNOB])
    cid = tp.candidate_id(cand)
    assert "duplicate-archived" in run(cand, archive=make_archive(
        archived_candidate_ids=frozenset({cid}))).codes
    held = make_archive(parent_knobs={KNOB["tail"]: KNOB["value"]})
    assert "no-op-vs-parent" in run(cand, archive=held).codes
    selection = candidate("construction", "exemplar-selection",
                          [{"scenario": "calendar", "selector": "all", "theta": None}])
    assert "no-op-vs-parent" in run(selection).codes


def test_a_fit_checker_can_refuse():
    cand = candidate("supply", "knob-set", [KNOB])
    result = run(cand, fit_checker=lambda c, a: "over-slot")
    assert "fit" in result.codes


# ---------------------------------------------------------------------------
# 4. The predicted effect (decision 192).
# ---------------------------------------------------------------------------


def test_a_prediction_under_one_and_a_half_points_is_refused():
    cand = candidate("supply", "knob-set", [KNOB])
    below = run(cand, pp=1.49)
    assert not below.accepted and below.codes == ("refused-prediction",)
    assert below.prediction is not None and below.prediction.slu_pp == pytest.approx(1.49)
    assert run(cand, pp=1.5).accepted
    assert run(cand, pp=3.0).prediction.slu_pp == 3.0


def test_a_missing_prediction_or_predictor_refuses_a_predicted_class():
    cand = candidate("supply", "knob-set", [KNOB])
    assert run(cand, pp=None).codes == ("prediction-missing",)
    assert tp.validate_candidate(cand, enums=ENUMS, archive=make_archive()).codes == (
        "prediction-missing",
    )


def test_the_file_predictor_stub_is_deterministic(tmp_path):
    cand = candidate("supply", "knob-set", [KNOB])
    cid = tp.candidate_id(cand)
    path = tmp_path / "pred.json"
    path.write_text(json.dumps({
        "schema": tp.PREDICTIONS_SCHEMA_ID,
        "predictions": {cid: {"slu_pp": 2.25, "basis": "synthetic"}},
    }), encoding="utf-8")
    predictor = tp.FilePredictor(path)
    result = tp.validate_candidate(cand, enums=ENUMS, archive=make_archive(),
                                   predictor=predictor)
    assert result.accepted and result.prediction.slu_pp == 2.25
    other = candidate("supply", "knob-set", [{**KNOB, "value": 15}])
    assert tp.validate_candidate(other, enums=ENUMS, archive=make_archive(),
                                 predictor=predictor).codes == ("prediction-missing",)
    path.write_text(json.dumps({"schema": "wrong", "predictions": {}}), encoding="utf-8")
    with pytest.raises(tp.TfrlProposerError):
        tp.FilePredictor(path)


# ---------------------------------------------------------------------------
# 5. candidate_id determinism.
# ---------------------------------------------------------------------------


def test_candidate_id_is_the_sha256_of_the_canonical_json_and_order_independent():
    cand = candidate("supply", "knob-set", [KNOB])
    expected = hashlib.sha256(
        json.dumps(cand, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
    assert tp.candidate_id(cand) == expected
    shuffled = dict(reversed(list(cand.items())))
    assert tp.candidate_id(shuffled) == expected
    assert tp.candidate_id({**cand, "hypothesis_code": "rule-filter"}) != expected
    assert run(cand).candidate_id == expected == run(json.dumps(shuffled)).candidate_id


# ---------------------------------------------------------------------------
# 6. The prompt renderer reads aggregates only.
# ---------------------------------------------------------------------------


def test_the_prompt_renders_with_every_placeholder_filled():
    tables = tp.parse_tables(make_tables())
    context = tp.parse_context(make_context())
    text = tp.render_typed_proposer_request(
        TEMPLATE, tables=tables, context=context, allowed_classes=["construction", "supply"]
    )
    assert "{{" not in text
    assert tables.tables_sha256 in text
    assert "construction, supply" in text and "s0-lock-v2.2" in text
    assert "saea-tfrl-typed-candidate-v1" in text
    assert "TABLE failure_cube (2 rows)" in text and "<3" in text
    assert "refusal_code=refused-prediction" in text
    assert "at most 2 application" in text
    # Iteration 2 shrinks the budget and the embedded schema.
    tables2 = tp.parse_tables(make_tables(2))
    text2 = tp.render_typed_proposer_request(TEMPLATE, tables=tables2,
                                             context=tp.parse_context(make_context(2)))
    assert "at most 1 application" in text2


def test_the_renderer_refuses_a_template_missing_a_placeholder_and_an_iteration_mismatch():
    tables = tp.parse_tables(make_tables())
    context = tp.parse_context(make_context())
    with pytest.raises(tp.TfrlProposerError):
        tp.render_typed_proposer_request(TEMPLATE.replace("{{TABLES}}", ""), tables=tables,
                                         context=context)
    with pytest.raises(tp.TfrlProposerError):
        tp.render_typed_proposer_request(TEMPLATE, tables=tables,
                                         context=tp.parse_context(make_context(2)))
    with pytest.raises(tp.TfrlProposerError):
        tp.render_typed_proposer_request(TEMPLATE, tables=tables, context=context,
                                         allowed_classes=["prompt"])


@pytest.mark.parametrize("key", ["text", "transcript", "gold", "value_text", "utterance",
                                 "gold_label", "answer_text", "query"])
def test_a_tables_artefact_with_an_utterance_bearing_key_is_refused(key):
    document = make_tables()
    document["tables"]["failure_cube"]["columns"].append(key)
    for row in document["tables"]["failure_cube"]["rows"]:
        row.append("x")
    document["tables_sha256"] = tp.canonical_tables_sha256(document)
    with pytest.raises(tp.TfrlProposerError):
        tp.parse_tables(document)
    nested = make_tables()
    nested[key] = "x"
    nested["tables_sha256"] = tp.canonical_tables_sha256(nested)
    with pytest.raises(tp.TfrlProposerError):
        tp.parse_tables(nested)


def test_a_tables_artefact_with_prose_cells_a_bad_hash_or_an_unknown_table_is_refused():
    document = make_tables()
    document["tables"]["failure_cube"]["rows"][0][1] = "set an alarm for seven"
    document["tables_sha256"] = tp.canonical_tables_sha256(document)
    with pytest.raises(tp.TfrlProposerError):
        tp.parse_tables(document)
    document = make_tables()
    document["tables_sha256"] = "0" * 64
    with pytest.raises(tp.TfrlProposerError):
        tp.parse_tables(document)
    document = make_tables(extra={"raw_rows": {"columns": ["a"], "rows": []}})
    with pytest.raises(tp.TfrlProposerError):
        tp.parse_tables(document)
    document = make_tables()
    del document["tables"]["exchange_rates"]
    document["tables_sha256"] = tp.canonical_tables_sha256(document)
    with pytest.raises(tp.TfrlProposerError):
        tp.parse_tables(document)


def test_a_context_artefact_may_carry_counts_and_codes_only():
    bad = make_context()
    bad["refused_buffer"][0]["text"] = "x"
    with pytest.raises(tp.TfrlProposerError):
        tp.parse_context(bad)
    bad = make_context()
    bad["refused_buffer"][0]["refusal_code"] = "a long sentence about the failures seen"
    with pytest.raises(tp.TfrlProposerError):
        tp.parse_context(bad)
    bad = make_context()
    bad["meta_summary"]["supply"]["notes"] = 1
    with pytest.raises(tp.TfrlProposerError):
        tp.parse_context(bad)


def test_the_rendered_prompt_contains_no_field_outside_the_artefacts():
    tables = tp.parse_tables(make_tables())
    context = tp.parse_context(make_context())
    text = tp.render_typed_proposer_request(TEMPLATE, tables=tables, context=context)
    for banned in ("transcript", "utterance text", "gold label"):
        # The template only mentions them to forbid them.
        assert banned not in text.split("AGGREGATE TABLES", 1)[1]


def test_load_tables_verifies_the_file_pin(tmp_path):
    path = tmp_path / "tables.json"
    path.write_text(json.dumps(make_tables()), encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    artefact = tp.load_tables(path, digest)
    assert artefact.file_sha256 == digest
    with pytest.raises(tp.TfrlProposerError):
        tp.load_tables(path, "0" * 64)


# ---------------------------------------------------------------------------
# 7. Delivery-time readers.
# ---------------------------------------------------------------------------


def test_the_typed_reader_seals_a_legal_candidate_and_never_raises():
    cand = candidate("supply", "knob-set", [KNOB])
    receipt = tp.read_typed_candidate_receipt(json.dumps(cand))
    assert receipt["legal"] is True and receipt["candidate_id"] == tp.candidate_id(cand)
    for bad in ("", "nonsense", json.dumps({"schema": "x"}),
                json.dumps({**cand, "prompt": "x"})):
        receipt = tp.read_typed_candidate_receipt(bad)
        assert receipt["legal"] is False and receipt["refusal_codes"]
        assert "candidate" not in receipt


# ---------------------------------------------------------------------------
# 8. The resolver dispatch.
# ---------------------------------------------------------------------------


class _Sample:
    def __init__(self, sample_id):
        self.sample_id = sample_id


@pytest.fixture
def typed_fixture(tmp_path):
    data_root = tmp_path / "data"
    data_root.mkdir()
    tables_path = data_root / "tables.json"
    tables_path.write_text(json.dumps(make_tables()), encoding="utf-8")
    context_path = data_root / "context.json"
    context_path.write_text(json.dumps(make_context()), encoding="utf-8")

    def pin(path):
        return {"relpath": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    values = {
        "arm": "construction-proposer-text",
        "policy": tp.TFRL_TYPED_PROGRAM_ID,
        "phase_material": {
            tp.TFRL_TYPED_PHASE_NAME: {"instruction_template": tp.TFRL_TYPED_TEMPLATE_RELPATH}
        },
        "tfrl_proposer": {
            "tables": pin(tables_path),
            "context": pin(context_path),
            "carriers": [
                {"sample_id": "row-a", "allowed_classes": ["construction"]},
                {"sample_id": "row-b", "allowed_classes": ["supply"]},
                {"sample_id": "row-c", "allowed_classes": ["delivery", "scope"]},
            ],
        },
    }
    return {"values": values, "data_root": data_root,
            "samples": [_Sample("row-a"), _Sample("row-b"), _Sample("row-c")]}


def test_the_runtime_dispatches_the_typed_program_to_its_material(typed_fixture):
    material = flight_runtime._default_construction_material(
        typed_fixture["values"], lock={}, data_root=typed_fixture["data_root"],
        repo_root=REPO_ROOT, samples=typed_fixture["samples"],
    )
    assert isinstance(material, tp.TfrlProposerMaterial)
    assert [c.sample_id for c in material.contacts] == ["row-a", "row-b", "row-c"]
    assert [c.group for c in material.contacts] == ["construction", "supply", "delivery+scope"]
    assert all(c.construction_target_ids == (c.sample_id,) for c in material.contacts)
    assert {e["target"] for e in material.bound_targets} == {tp.AGGREGATE_ONLY_TARGET}
    blob = json.dumps(material.as_json())
    assert "TABLE failure_cube" not in blob and "s0-lock-v2.2" not in blob
    assert material.contacts[0].instruction != material.contacts[1].instruction
    assert hashlib.sha256(
        material.contacts[0].instruction.encode()
    ).hexdigest() == material.contacts[0].prompt_sha256


def test_the_runtime_accepts_the_new_material_type(typed_fixture):
    material = flight_runtime._default_construction_material(
        typed_fixture["values"], lock={}, data_root=typed_fixture["data_root"],
        repo_root=REPO_ROOT, samples=typed_fixture["samples"],
    )
    runtime = object.__new__(flight_runtime.FlightRuntime)
    runtime._construction_material = None
    runtime._composed = SimpleNamespace(values=typed_fixture["values"])
    runtime._lock = {}
    runtime._data_root = typed_fixture["data_root"]
    runtime._repo_root = REPO_ROOT
    runtime._samples = typed_fixture["samples"]
    runtime._construction_material_resolver = lambda *a, **k: material
    assert runtime.construction_material() is material


def test_a_drifted_input_is_refused_as_a_flight_error(typed_fixture):
    values = copy.deepcopy(typed_fixture["values"])
    values["tfrl_proposer"]["tables"]["sha256"] = "0" * 64
    with pytest.raises(flight_runtime.FlightRuntimeError):
        flight_runtime._default_construction_material(
            values, lock={}, data_root=typed_fixture["data_root"], repo_root=REPO_ROOT,
            samples=typed_fixture["samples"],
        )
    with pytest.raises(flight_runtime.FlightRuntimeError):
        flight_runtime._default_construction_material(
            typed_fixture["values"], lock={}, data_root=typed_fixture["data_root"],
            repo_root=REPO_ROOT, samples=typed_fixture["samples"][:2],
        )


def _fake_ace_module(monkeypatch, calls):
    """A stand-in for ``rails.tfrl_ace_material`` with E-T2's real signatures."""

    module = types.ModuleType("speech_aware_evidence_acquisition.rails.tfrl_ace_material")

    def render_reflector_request(material_path, playbook_path, token_cap):
        scenario = json.loads(Path(material_path).read_text(encoding="utf-8"))["scenario"]
        calls.append((Path(material_path).name, Path(playbook_path).name, token_cap))
        return {
            "schema": tp.ACE_REQUEST_SCHEMA,
            "messages": [{"role": "user", "content": f"RENDER-{scenario}"}],
            "request_sha256": "r" * 64,
        }

    def parse_reflector_response(payload):
        return [dict(item) for item in payload["deltas"]]

    module.render_reflector_request = render_reflector_request
    module.parse_reflector_response = parse_reflector_response
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.rails.tfrl_ace_material", module, raising=False
    )


@pytest.fixture
def ace_fixture(tmp_path):
    data_root = tmp_path / "data"
    data_root.mkdir()
    playbook = data_root / "playbook.json"
    playbook.write_text("[]", encoding="utf-8")

    def pin(path):
        return {"relpath": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    carriers = []
    for sample_id, scenario in (("row-w", "weather"), ("row-c", "calendar")):
        material = data_root / f"material-{scenario}.json"
        material.write_text(json.dumps({"scenario": scenario}), encoding="utf-8")
        carriers.append({"sample_id": sample_id, "scenario": scenario, "material": pin(material)})
    values = {
        "arm": "construction-proposer-text",
        "policy": tp.TFRL_ACE_PROGRAM_ID,
        "tfrl_ace_reflector": {"playbook": pin(playbook), "token_cap": 1880, "carriers": carriers},
    }
    return {"values": values, "data_root": data_root,
            "samples": [_Sample("row-w"), _Sample("row-c")]}


def test_the_runtime_dispatches_the_ace_program_through_a_lazy_import(monkeypatch, ace_fixture):
    calls: list = []
    _fake_ace_module(monkeypatch, calls)
    material = flight_runtime._default_construction_material(
        ace_fixture["values"], lock={}, data_root=ace_fixture["data_root"],
        repo_root=REPO_ROOT, samples=ace_fixture["samples"],
    )
    assert calls == [
        ("material-weather.json", "playbook.json", 1880),
        ("material-calendar.json", "playbook.json", 1880),
    ]
    assert isinstance(material, tp.TfrlProposerMaterial) and material.kind == "ace"
    # One contact per carrier, in flown order, the instruction being the request's message.
    assert [(c.sample_id, c.group) for c in material.contacts] == [
        ("row-w", "weather"), ("row-c", "calendar")
    ]
    assert material.contacts[0].instruction == "RENDER-weather"
    assert "RENDER-" not in json.dumps(material.as_json())
    assert all(c.construction_target_ids == (c.sample_id,) for c in material.contacts)


def test_the_ace_dispatch_refuses_drift_and_a_population_mismatch(monkeypatch, ace_fixture):
    _fake_ace_module(monkeypatch, [])
    root = ace_fixture["data_root"]
    drifted = copy.deepcopy(ace_fixture["values"])
    drifted["tfrl_ace_reflector"]["playbook"]["sha256"] = "0" * 64
    twice = copy.deepcopy(ace_fixture["values"])
    twice["tfrl_ace_reflector"]["carriers"][0]["scenario"] = "calendar"
    for values, samples in (
        (drifted, ace_fixture["samples"]),
        (twice, ace_fixture["samples"]),
        (ace_fixture["values"], ace_fixture["samples"][:1]),
    ):
        with pytest.raises(flight_runtime.FlightRuntimeError):
            flight_runtime._default_construction_material(
                values, lock={}, data_root=root, repo_root=REPO_ROOT, samples=samples
            )


def test_the_ace_reader_uses_the_reflector_parser_and_seals_no_text(monkeypatch):
    _fake_ace_module(monkeypatch, [])
    reply = json.dumps({"deltas": [{"op": "add", "section": "pitfall", "text": "never seal this"}]})
    receipt = tp.read_ace_reflector_receipt(reply)
    assert receipt["legal"] is True and receipt["delta_count"] == 1
    assert "never seal this" not in json.dumps(receipt)
    assert tp.read_ace_reflector_receipt("garbage")["legal"] is False


def test_the_real_ace_module_parses_and_renders_through_the_dispatch(tmp_path):
    """Contract check against E-T2's real module (merged on master)."""

    from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace

    reply = json.dumps({"deltas": [{
        "op": "add", "target_id": "", "section": "pitfall",
        "scope": {"scenarios": ["calendar"], "slot_types": []},
        "text": "Keep a bare number out of the date slot.", "rationale": "synthetic",
    }]})
    receipt = tp.read_ace_reflector_receipt(reply)
    assert receipt["legal"] is True and receipt["delta_count"] == 1
    assert "bare number" not in json.dumps(receipt)
    assert tp.read_ace_reflector_receipt(json.dumps({"deltas": [], "extra": 1}))["legal"] is False
    assert RESPONSE_FORMATS.resolve(tp.TFRL_ACE_RESPONSE_FORMAT_ID)({}, REPO_ROOT) == ace.response_format()


# ---------------------------------------------------------------------------
# 9. The exposure row.
# ---------------------------------------------------------------------------


def _row(**overrides):
    base = dict(
        date="2026-10-12", run_id="SAEA-SLURP-STAGE3-TFRL-PROPOSER-I1-V1",
        carrier_roster_id="SLURP-TFRL-PROPOSER-FOLD-B-CARRIERS-I1-V1",
        split_identity_hash="b" * 64, carriers=3,
        model_files_sha256={"core.gguf": "d" * 64},
        llama_cpp_build_commit="04ccc72a", prompt_sha256="e" * 64, tables_sha256="f" * 64,
        archive_sha256="a" * 64, geometry="np4 x 24,576",
    )
    base.update(overrides)
    return tp.draft_exposure_row(**base)


def test_the_exposure_row_carries_the_registered_fields_and_parses_as_a_ledger_row():
    row = _row()
    assert tuple(row) == tp.LEDGER_COLUMNS
    assert row["consumed"] == "no" and row["speech audio seconds"] == "0"
    assert row["calls"] == str(tp.planned_model_calls(3)) == "9"
    for needle in ("d" * 64, "04ccc72a", "e" * 64, "f" * 64, "np4 x 24,576", "pending"):
        assert needle in " ".join(row.values())
    assert "no per-row gold, no utterance text, no output text" in row["scope"]
    assert _row(output_sha256="9" * 64)["artifacts"].endswith("9" * 64)
    header = "| " + " | ".join(tp.LEDGER_COLUMNS) + " |\n| " + " | ".join(
        "---" for _ in tp.LEDGER_COLUMNS) + " |\n"
    parsed = _parse_ledger_tables(header + tp.ledger_markdown_row(row) + "\n")
    assert len(parsed) == 1
    assert parsed[0]["run/experiment id"] == row["run/experiment id"]
    assert parsed[0]["consumed"] == "no" and parsed[0]["split role"] == "discovery"
    assert "slurp" in parsed[0]["speech carrier + split"].split()
    with pytest.raises(tp.TfrlProposerError):
        _row(kind="other")


# ---------------------------------------------------------------------------
# E-T6: multi-store release_swaps lands; the archive view contract flips the flag
# ---------------------------------------------------------------------------


def _view_mapping(**extra) -> dict:
    document = {
        "iteration": 1, "parent_state_id": "s0-lock-v2.2",
        "known_state_ids": ["s0-lock-v2.2"],
        "entry_ids": {"deliver-rule": ["rule-1"], "slot-card": ["card-1"]},
        "parent_stores": ["train-exemplars"],
    }
    document.update(extra)
    return document


def test_a_two_store_candidate_is_accepted_when_the_archive_view_says_swaps_are_supported():
    from speech_aware_evidence_acquisition.rails.supply_variants import (
        MULTI_STORE_RELEASE_SWAPS_SUPPORTED,
    )

    card = candidate("construction", "slot-card-subset", [CARD])  # touches slot-contracts
    supported = tp.ArchiveView.from_mapping(
        _view_mapping(release_swaps_supported=MULTI_STORE_RELEASE_SWAPS_SUPPORTED))
    assert supported.release_swaps_supported is True
    assert run(card, archive=supported).accepted
    # a view that does not carry the key (or carries false) still refuses it
    for document in (_view_mapping(), _view_mapping(release_swaps_supported=False)):
        refused = run(card, archive=tp.ArchiveView.from_mapping(document))
        assert not refused.accepted and "second-store-swap" in refused.codes
    # a one-store candidate never needed the flag
    same = tp.ArchiveView.from_mapping(_view_mapping(parent_stores=["slot-contracts"]))
    assert run(card, archive=same).accepted
