"""Stage-3 S3-4s (owner decision 106, 2026-09-23): the SYSTEM-level advantage
contact's v2 surface.

Three obligations:

1. The closed-form multi-block parser -- legal, illegal and MIXED responses
   -- never raises, retains every block it could read, and marks each one.
2. The v2 instruction renderer fills every placeholder of the committed
   template and refuses a template missing one.
3. The v2 response format and phase program are registered beside v1, and v1
   itself is untouched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.base import (
    AGENT_CONTROLLERS,
    RESPONSE_FORMATS,
)
from speech_aware_evidence_acquisition.rails import controllers as _controllers  # noqa: F401
from speech_aware_evidence_acquisition.rails.stage3_advantage import (
    LEGAL_DELTA_KINDS,
    LEGAL_DELTA_KINDS_V2,
    LEGAL_DELTA_NODES,
    MAX_ADVANTAGE_BLOCKS,
    STAGE3_ADVANTAGE_PROGRAM_ID_V2,
    STAGE3_ADVANTAGE_RESPONSE_FORMAT_ID_V2,
    STAGE3_ADVANTAGE_TEMPLATE_RELPATH_V2,
    V2_TEMPLATE_PLACEHOLDERS,
    AdvantagePair,
    AdvantagePairSample,
    Stage3AdvantageError,
    build_advantage_instruction_for_row_v2,
    parse_advantage_statement,
    parse_advantage_statements_v2,
    render_advantage_instruction_v2,
    stage3_advantage_response_format_v2,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

_LEGAL_BLOCK = (
    "NODE: solver\n"
    "DELTA-KIND: slot-contract\n"
    "TARGET: alarm_set\n"
    "STATEMENT: Keep the device slot only when the speech names a device.\n"
)
_SECOND_BLOCK = (
    "NODE: reviewer\n"
    "DELTA-KIND: reviewer-criterion\n"
    "TARGET: alarm_set\n"
    "STATEMENT: Reject a draft whose intent disagrees with every perception candidate.\n"
)
_PERCEPTION_BLOCK = (
    "NODE: perception\n"
    "DELTA-KIND: perception-hint\n"
    "TARGET: alarm_query\n"
    "STATEMENT: Propose the query intent whenever the utterance asks about an existing alarm.\n"
)


# ---------------------------------------------------------------------------
# 1. The parser
# ---------------------------------------------------------------------------


def test_one_legal_block_parses_and_carries_its_node_task_target() -> None:
    parsed = parse_advantage_statements_v2(_LEGAL_BLOCK)
    assert parsed.legal is True
    assert parsed.source_form == "lines"
    assert len(parsed.blocks) == 1
    block = parsed.blocks[0]
    assert (block.node, block.delta_kind, block.target) == (
        "solver", "slot-contract", "alarm_set",
    )
    assert block.task_target() == "solver:slot-contract:alarm_set"
    assert block.legal is True and block.illegal_reasons == ()


def test_three_blocks_parse_in_order() -> None:
    parsed = parse_advantage_statements_v2(
        _LEGAL_BLOCK + "\n" + _SECOND_BLOCK + "\n" + _PERCEPTION_BLOCK
    )
    assert parsed.legal is True
    assert [block.node for block in parsed.blocks] == ["solver", "reviewer", "perception"]
    assert [block.block_index for block in parsed.blocks] == [0, 1, 2]


def test_a_fourth_block_is_retained_and_marked_illegal() -> None:
    parsed = parse_advantage_statements_v2(
        _LEGAL_BLOCK + _SECOND_BLOCK + _PERCEPTION_BLOCK + _LEGAL_BLOCK
    )
    assert parsed.legal is False
    assert len(parsed.blocks) == 4  # retained, never dropped by the parser
    assert parsed.blocks[3].legal is False
    assert any("past the" in reason for reason in parsed.blocks[3].illegal_reasons)
    assert any("exceed" in reason for reason in parsed.illegal_reasons)
    # The first three are still individually legal, which is what lets
    # curation keep them and drop only the fourth.
    assert [block.legal for block in parsed.blocks[:3]] == [True, True, True]
    assert len(parsed.legal_blocks()) == MAX_ADVANTAGE_BLOCKS


def test_a_mixed_response_keeps_the_legal_block_and_marks_the_illegal_one() -> None:
    mixed = _LEGAL_BLOCK + (
        "NODE: oracle\n"
        "DELTA-KIND: telepathy\n"
        "TARGET: \n"
        "STATEMENT: \n"
    )
    parsed = parse_advantage_statements_v2(mixed)
    assert parsed.legal is False
    assert len(parsed.blocks) == 2
    assert parsed.blocks[0].legal is True
    bad = parsed.blocks[1]
    assert bad.legal is False
    assert any("illegal node" in reason for reason in bad.illegal_reasons)
    assert any("illegal delta-kind" in reason for reason in bad.illegal_reasons)
    assert "empty target" in bad.illegal_reasons
    assert "empty statement" in bad.illegal_reasons
    assert parsed.legal_blocks() == (parsed.blocks[0],)


@pytest.mark.parametrize(
    "text", ["", "   ", None, 17, "no keyed line at all", "\n\n\n"],
)
def test_the_parser_never_raises(text) -> None:
    parsed = parse_advantage_statements_v2(text)
    assert parsed.legal is False
    assert isinstance(parsed.raw_text_sha256, str) and len(parsed.raw_text_sha256) == 64


def test_a_block_missing_its_node_line_is_retained_as_block_zero() -> None:
    parsed = parse_advantage_statements_v2(
        "DELTA-KIND: exemplar-note\nTARGET: alarm_set\nSTATEMENT: A sentence.\n"
    )
    assert len(parsed.blocks) == 1
    assert parsed.blocks[0].legal is False
    assert any("missing keys: NODE" in r for r in parsed.blocks[0].illegal_reasons)


def test_a_repeated_key_inside_one_block_takes_the_first_occurrence() -> None:
    parsed = parse_advantage_statements_v2(
        "NODE: solver\nDELTA-KIND: slot-contract\nDELTA-KIND: exemplar-note\n"
        "TARGET: alarm_set\nSTATEMENT: One sentence.\n"
    )
    assert parsed.blocks[0].delta_kind == "slot-contract"


def test_an_over_long_statement_is_retained_and_marked() -> None:
    long_statement = " ".join(["word"] * 41)
    parsed = parse_advantage_statements_v2(
        f"NODE: planner\nDELTA-KIND: planner-rule\nTARGET: alarm_set\n"
        f"STATEMENT: {long_statement}\n"
    )
    assert parsed.blocks[0].legal is False
    assert any("exceeds 40 words" in r for r in parsed.blocks[0].illegal_reasons)


def test_a_structured_json_reply_reads_through_the_same_parser() -> None:
    document = {
        "blocks": [
            {
                "node": "solver",
                "delta_kind": "slot-contract",
                "target": "alarm_set",
                "statement": "Keep the device slot only when the speech names a device.",
            }
        ]
    }
    parsed = parse_advantage_statements_v2(json.dumps(document))
    assert parsed.source_form == "json"
    assert parsed.legal is True
    assert parsed.blocks[0].task_target() == "solver:slot-contract:alarm_set"


def test_the_receipt_carries_no_statement_text() -> None:
    parsed = parse_advantage_statements_v2(_LEGAL_BLOCK)
    receipt = json.dumps(parsed.receipt())
    assert "device" not in receipt
    assert parsed.blocks[0].statement_sha256() in receipt


# ---------------------------------------------------------------------------
# 2. The renderer
# ---------------------------------------------------------------------------


def _material() -> dict:
    return {
        "candidate_list_text": "1. alarm_set\n2. alarm_query",
        "best_answer_text": '{"scenario": "alarm", "action": "set"}',
        "worst_answer_text": '{"scenario": "alarm", "action": "query"}',
        "delivered_answer_text": '{"scenario": "alarm", "action": "query"}',
        "reviewer_verdicts_text": "1. ACCEPT",
        "planner_route_text": "1. ACCEPT",
        "gold_text": '{"scenario": "alarm", "action": "set"}',
    }


def test_the_committed_template_carries_every_placeholder() -> None:
    template = (REPO_ROOT / "configs" / STAGE3_ADVANTAGE_TEMPLATE_RELPATH_V2).read_text(
        encoding="utf-8"
    )
    for placeholder in V2_TEMPLATE_PLACEHOLDERS:
        assert placeholder in template
    rendered = render_advantage_instruction_v2(template, **_material())
    for placeholder in V2_TEMPLATE_PLACEHOLDERS:
        assert placeholder not in rendered
    assert "alarm_query" in rendered
    # The four-line form is stated verbatim in the instruction.
    for node in LEGAL_DELTA_NODES:
        assert node in rendered
    for kind in LEGAL_DELTA_KINDS_V2:
        assert kind in rendered


def test_the_renderer_refuses_a_template_missing_a_placeholder() -> None:
    with pytest.raises(Stage3AdvantageError):
        render_advantage_instruction_v2("{gold} only", **_material())


def test_build_for_row_validates_its_pair_first() -> None:
    template = (REPO_ROOT / "configs" / STAGE3_ADVANTAGE_TEMPLATE_RELPATH_V2).read_text(
        encoding="utf-8"
    )
    pair = AdvantagePair(
        sample_id="row-1",
        best=AdvantagePairSample(sample_index=0, response_text_sha256="a" * 64),
        worst=AdvantagePairSample(sample_index=0, response_text_sha256="b" * 64),
    )
    with pytest.raises(Stage3AdvantageError):
        build_advantage_instruction_for_row_v2(template, pair, **_material())


# ---------------------------------------------------------------------------
# 3. Registration, and v1 left alone
# ---------------------------------------------------------------------------


def test_v2_format_and_program_are_registered_beside_v1() -> None:
    names = RESPONSE_FORMATS.names()
    assert "stage3-advantage-statement-v1" in names
    assert STAGE3_ADVANTAGE_RESPONSE_FORMAT_ID_V2 in names
    assert "phase-stage3-advantage-v1" in AGENT_CONTROLLERS.names()
    assert STAGE3_ADVANTAGE_PROGRAM_ID_V2 in AGENT_CONTROLLERS.names()


def test_v2_schema_closes_the_node_and_kind_vocabularies() -> None:
    schema = stage3_advantage_response_format_v2({}, REPO_ROOT)
    items = schema["json_schema"]["schema"]["properties"]["blocks"]["items"]
    assert items["properties"]["node"]["enum"] == list(LEGAL_DELTA_NODES)
    assert items["properties"]["delta_kind"]["enum"] == list(LEGAL_DELTA_KINDS_V2)
    assert schema["json_schema"]["schema"]["properties"]["blocks"]["maxItems"] == (
        MAX_ADVANTAGE_BLOCKS
    )


def test_v1_parser_is_unchanged_by_v2() -> None:
    parsed = parse_advantage_statement(
        "DELTA-KIND: exemplar-note\nTARGET: alarm_set\nSTATEMENT: One sentence.\n"
    )
    assert parsed.legal is True
    assert parsed.delta_kind in LEGAL_DELTA_KINDS
    # v1's vocabulary is a strict prefix of v2's, never a rename of it.
    assert LEGAL_DELTA_KINDS_V2[: len(LEGAL_DELTA_KINDS)] == LEGAL_DELTA_KINDS
