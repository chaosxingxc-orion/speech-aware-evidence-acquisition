"""Item E37 (owner decision 84, 2026-09-22): the Reviewer's verdict becomes a
closed set of primitives.

Design: ``docs/superpowers/specs/2026-09-22-slurp-reviewer-primitive-verdict-design.md``.

What this module proves, all of it model-free -- zero model, tokenizer,
encoder, scorer, network and GPU contact, and no ``SPEECHRL_DATA_DIR`` read --
except the graph-level proofs, which run against the fake transport of
``test_native_episode_runner`` and in-memory role nodes (the E18/E22 pattern):

1. the parser: every vocabulary token; leading blank lines; trailing
   rationale kept byte-exact; near-miss tokens illegal; empty text illegal;
2. the config switch: the key resolves in the episode class, its OFF arm is
   the key's absence, the loader accepts the one registered vocabulary and
   refuses every other shape;
3. the spec field's own default and validation;
4. the NCP hook: ``PARSER_IDS["review-primitive"]`` is registered;
5. the wire proof through the real role graph: three Reviewer visits --
   legal, illegal and react_exhaustion -- each write their own
   ``reviewer_verdicts`` mark, and an unarmed episode's receipt carries no
   such key at all;
6. the verifier script's ``primitive_verdict_stats`` pure function, on a
   synthetic receipt set with known precision.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.config_tables import (
    EPISODE_LEVEL_SWITCH_KEYS,
    ConfigTableError,
    is_episode_null_arm,
    resolve_episode_switch_key,
)
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.node_context_policy import PARSER_IDS
from speech_aware_evidence_acquisition.rails.review_primitives import (
    ACCEPT,
    REVIEW_PRIMITIVE_TOKENS,
    REVIEW_PRIMITIVES_VOCABULARY,
    REVIEW_VERDICT_ILLEGAL,
    REVISE_FORMAT,
    REVISE_INTENT,
    REVISE_SLOT_EXTRA,
    REVISE_SLOT_MISSING,
    REVISE_SLOT_VALUE,
    UNSURE,
    ReviewPrimitiveError,
    parse_review_primitive,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from speech_aware_evidence_acquisition.reproduction.ojw.native_episode import (
    REACT_EXHAUSTION_DISPOSITION,
    REVIEWER_VERDICT_ILLEGAL_DISPOSITION,
    REVIEWER_VERDICT_LEGAL,
    REVIEWER_VERDICTS_KEY,
    NativeEpisodeActions,
    NativeEpisodeSpec,
)

from test_native_episode_runner import _ActualEpisodeHarness, _program
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401

REPO_ROOT = Path(__file__).resolve().parents[2]
SWITCH_KEY = "native_episode.reviewer_verdict"


# ---------------------------------------------------------------------------
# 1. The parser.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("token", REVIEW_PRIMITIVE_TOKENS)
def test_every_vocabulary_token_parses_legal(token):
    parsed_token, rationale, head = parse_review_primitive(
        f"{token}\nBecause the speech supports it."
    )
    assert parsed_token == token
    assert rationale == "Because the speech supports it."
    assert head is None


def test_vocabulary_is_the_registered_id_in_the_fixed_order():
    assert REVIEW_PRIMITIVES_VOCABULARY == "saea-review-primitives-v1"
    assert REVIEW_PRIMITIVE_TOKENS == (
        ACCEPT,
        REVISE_INTENT,
        REVISE_SLOT_MISSING,
        REVISE_SLOT_EXTRA,
        REVISE_SLOT_VALUE,
        REVISE_FORMAT,
        UNSURE,
    )


def test_leading_blank_lines_are_skipped():
    token, rationale, head = parse_review_primitive("\n\n   \nACCEPT\nfine as is")
    assert token == ACCEPT
    assert rationale == "fine as is"
    assert head is None


def test_trailing_rationale_is_kept_byte_exact_across_many_lines():
    rationale = "line one\nline two\n\nline four with  double  spaces"
    token, parsed_rationale, head = parse_review_primitive(f"REVISE-FORMAT\n{rationale}")
    assert token == REVISE_FORMAT
    assert parsed_rationale == rationale
    assert head is None


def test_a_token_alone_carries_empty_rationale():
    token, rationale, head = parse_review_primitive("ACCEPT")
    assert token == ACCEPT
    assert rationale == ""
    assert head is None


@pytest.mark.parametrize(
    "near_miss", ["Accept", "REVISE", "REVISE-SLOT", "accept", "revise-format", "UNSURE!"]
)
def test_near_miss_tokens_are_illegal(near_miss):
    token, rationale, head = parse_review_primitive(f"{near_miss}\nrationale text")
    assert token == REVIEW_VERDICT_ILLEGAL
    assert rationale is None
    assert head == near_miss[:32]


def test_empty_text_is_illegal():
    token, rationale, head = parse_review_primitive("")
    assert token == REVIEW_VERDICT_ILLEGAL
    assert rationale is None
    assert head == ""


def test_whitespace_only_text_is_illegal():
    text = "   \n\n  \t\n"
    token, rationale, head = parse_review_primitive(text)
    assert token == REVIEW_VERDICT_ILLEGAL
    assert rationale is None
    # No non-empty line exists at all, so the bounded head is the whole
    # (short) offending text, exactly as an empty string's head is itself.
    assert head == text[:32]


def test_head_is_bounded_to_32_chars():
    long_line = "X" * 80
    token, rationale, head = parse_review_primitive(long_line)
    assert token == REVIEW_VERDICT_ILLEGAL
    assert head == long_line[:32]
    assert len(head) == 32


def test_non_text_input_is_refused_not_silently_coerced():
    with pytest.raises(ReviewPrimitiveError):
        parse_review_primitive(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 2. The config switch.
# ---------------------------------------------------------------------------


def test_the_key_resolves_in_the_closed_episode_class():
    assert SWITCH_KEY in EPISODE_LEVEL_SWITCH_KEYS
    assert len(EPISODE_LEVEL_SWITCH_KEYS) == 13
    assert resolve_episode_switch_key(SWITCH_KEY) == SWITCH_KEY
    # OFF is the key's absence; there is no third shape.
    assert is_episode_null_arm(SWITCH_KEY, None) is True
    assert (
        is_episode_null_arm(SWITCH_KEY, {"vocabulary": REVIEW_PRIMITIVES_VOCABULARY})
        is False
    )


def test_an_unregistered_episode_key_is_refused():
    with pytest.raises(ConfigTableError):
        resolve_episode_switch_key("native_episode.reviewer_verdicts")


_UNSET = object()


def _episode_values(reviewer_verdict=_UNSET):
    block = {
        "schema": "saea-native-episode-config-v1",
        "episode_id": "e37-proof-v1",
        "max_revisions": 0,
        "actions": {"accept": "ACCEPT", "revise": "REVISE", "acquire": "ACQUIRE"},
        "roles": {
            kind: {"phase_id": kind, "max_iterations": 1}
            for kind in ("perception", "solver", "reviewer", "planner")
        },
    }
    if reviewer_verdict is not _UNSET:
        block["reviewer_verdict"] = reviewer_verdict
    return {"native_episode": block}


#: perception 1 + 1 x (solver 1 + reviewer 1 + planner 1) at max_revisions 0.
CEILING = 4


def test_the_key_parses_and_defaults_to_none():
    program = _program(max_contacts=CEILING)
    assert (
        load_native_episode_config(_episode_values(), program).reviewer_verdict_vocabulary
        is None
    )
    armed = load_native_episode_config(
        _episode_values({"vocabulary": REVIEW_PRIMITIVES_VOCABULARY}), program
    )
    assert armed.reviewer_verdict_vocabulary == REVIEW_PRIMITIVES_VOCABULARY


def test_the_loader_refuses_unknown_vocabularies():
    program = _program(max_contacts=CEILING)
    with pytest.raises(ValueError, match="reviewer_verdict"):
        load_native_episode_config(
            _episode_values({"vocabulary": "saea-review-findings-v1"}), program
        )


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"vocabulary": REVIEW_PRIMITIVES_VOCABULARY, "extra": 1},
        "saea-review-primitives-v1",
        ["saea-review-primitives-v1"],
        None,
    ],
)
def test_the_loader_refuses_a_malformed_block(bad):
    program = _program(max_contacts=CEILING)
    with pytest.raises(ValueError):
        load_native_episode_config(_episode_values(bad), program)


# ---------------------------------------------------------------------------
# 3. The spec field.
# ---------------------------------------------------------------------------


def test_the_spec_defaults_to_none_and_validates_a_non_empty_string():
    actions = NativeEpisodeActions("ACCEPT", "REVISE", "ACQUIRE")
    assert NativeEpisodeSpec("e37", 0, actions).reviewer_verdict_vocabulary is None
    spec = NativeEpisodeSpec(
        "e37", 0, actions, reviewer_verdict_vocabulary=REVIEW_PRIMITIVES_VOCABULARY,
    )
    assert spec.reviewer_verdict_vocabulary == REVIEW_PRIMITIVES_VOCABULARY
    with pytest.raises(ValueError, match="reviewer_verdict_vocabulary"):
        NativeEpisodeSpec("e37", 0, actions, reviewer_verdict_vocabulary="")


# ---------------------------------------------------------------------------
# 4. The NCP hook.
# ---------------------------------------------------------------------------


def test_the_ncp_parser_id_is_registered():
    assert (
        PARSER_IDS["review-primitive"]
        == "rails.review_primitives.parse_review_primitive"
    )


# ---------------------------------------------------------------------------
# 5. The graph, through the actual runner (E18/E22 pattern).
# ---------------------------------------------------------------------------


LEGAL_TEXT = "REVISE-SLOT-VALUE\nThe date filler looks wrong given the utterance."
ILLEGAL_TEXT = "This is not a listed token."


def _armed_harness(tmp_path):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=2,
        max_contacts=13,
        planner_actions=("REVISE", "REVISE", "ACCEPT"),
        reviewer_task_tool=True,
    )
    harness.config = replace(
        harness.config,
        reviewer_verdict_vocabulary=REVIEW_PRIMITIVES_VOCABULARY,
        react_exhaustion_policy="continue-without-answer",
    )
    original = harness._output

    def output(key):
        _sample_id, phase, visit, _turn = key
        if phase == "reviewer":
            if visit == 1:
                return LEGAL_TEXT
            if visit == 2:
                return ILLEGAL_TEXT
            if visit == 3:
                return None  # a tool call on every turn -> exhaustion
        return original(key)

    harness._output = output
    return harness


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_three_reviewer_visits_each_write_their_own_receipt_mark(tmp_path):
    harness = _armed_harness(tmp_path)
    try:
        summary = harness.run()
    finally:
        harness.close()

    row = summary.results[0]
    receipt = row.native_episode_receipt
    # The row delivered through the ordinary explicit ACCEPT, the same
    # disposition an unarmed row would have taken.
    assert "accepted_solver_receipt" in receipt
    assert "terminal_disposition" not in receipt
    assert row.final_response_text == "solver-answer:s1:visit:3"

    marks = receipt[REVIEWER_VERDICTS_KEY]
    assert len(marks) == 3
    # "visit" is the Reviewer's OWN 0-based visit count -- the revision
    # round index, directly usable against planner_routes[visit] -- NOT the
    # global role_visits index Planner routes key on.
    assert [mark["visit"] for mark in marks] == [0, 1, 2]

    legal, illegal, exhausted = marks
    assert legal == {
        "visit": 0, "token": "REVISE-SLOT-VALUE",
        "disposition": REVIEWER_VERDICT_LEGAL, "head": None,
    }
    assert illegal == {
        "visit": 1, "token": None,
        "disposition": REVIEWER_VERDICT_ILLEGAL_DISPOSITION, "head": ILLEGAL_TEXT[:32],
    }
    assert exhausted == {
        "visit": 2, "token": None,
        "disposition": REACT_EXHAUSTION_DISPOSITION, "head": None,
    }

    # The Reviewer's exhaustion still carries the shared react_exhaustion
    # block too (item E22): two marks, one shared cause.
    assert receipt[REACT_EXHAUSTION_DISPOSITION]["count"] == 1

    # Planner routing is driven by _output's own planner_actions table here
    # (this harness's role_input is a synthetic marker, not the SLURP query
    # builder that embeds state["review"] text), and the delivered draft
    # above proves the row completed through the ordinary ACCEPT despite
    # one legal, one illegal and one exhausted Reviewer visit -- the E8c/E22
    # "never raise on a malformed or exhausted role output" discipline this
    # module extends. That state["review"] itself renders UNCHANGED into
    # whatever the Planner's query builder embeds is a property of the
    # diff, not of this harness: reproduction.ojw.native_episode._ApplyRole
    # sets ``updated[self._kind] = output`` (kind "review") unconditionally,
    # BEFORE the E37 branch below it ever runs, and that branch never
    # reassigns it -- only rails.review_findings' declared JSON contract and
    # this module's own primitive parse ever read ``output``, and neither
    # writes it back.
    assert [entry["action"] for entry in receipt["planner_routes"]] == [
        "REVISE", "REVISE", "ACCEPT",
    ]


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_an_unarmed_episode_carries_no_reviewer_verdicts_key(tmp_path):
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=4,
        planner_actions=("ACCEPT",),
    )
    # reviewer_verdict_vocabulary is unset -- the dataclass default, None --
    # exactly the shape every episode built before E37 has.
    assert harness.config.reviewer_verdict_vocabulary is None
    try:
        summary = harness.run()
    finally:
        harness.close()
    receipt = summary.results[0].native_episode_receipt
    assert REVIEWER_VERDICTS_KEY not in receipt


# ---------------------------------------------------------------------------
# 6. The verifier script's primitives stage, on a synthetic receipt set.
# ---------------------------------------------------------------------------


VERIFIER_PATH = REPO_ROOT / "scripts" / "analysis" / "slurp_verifier_measurement.py"


def _load_verifier_module():
    spec = importlib.util.spec_from_file_location("slurp_verifier_measurement", VERIFIER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # dataclasses on 3.12 resolves annotations via sys.modules[cls.__module__];
    # the module must be registered there before exec_module runs its
    # @dataclass(frozen=True) class bodies.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


verifier = _load_verifier_module()


def _mark(visit, token, disposition, head=None):
    return {"visit": visit, "token": token, "disposition": disposition, "head": head}


def test_primitive_verdict_stats_on_a_synthetic_receipt_set_with_known_precision():
    # "visit" is the Reviewer's OWN 0-based visit count -- the revision round
    # index -- exactly as reproduction.ojw.native_episode._ApplyRole writes
    # it, so ``planner_routes[visit]`` reads the SAME round's route.
    rows = {
        # ACCEPT, delivered correct: a true negative for the REVISE-* signal.
        "row-accept-correct": {
            "reviewer_verdicts": [_mark(0, "ACCEPT", "legal")],
            "planner_routes": ["ACCEPT"],
            "official_correct": True,
        },
        # REVISE-SLOT-VALUE, delivered WRONG: a true positive.
        "row-revise-wrong": {
            "reviewer_verdicts": [_mark(0, "REVISE-SLOT-VALUE", "legal")],
            "planner_routes": ["REVISE", "ACCEPT"],
            "official_correct": False,
        },
        # REVISE-INTENT, delivered correct anyway: a false positive.
        "row-revise-correct": {
            "reviewer_verdicts": [_mark(0, "REVISE-INTENT", "legal")],
            "planner_routes": ["REVISE", "ACCEPT"],
            "official_correct": True,
        },
        # ACCEPT, delivered WRONG: a false negative (missed by the primitive).
        "row-accept-wrong": {
            "reviewer_verdicts": [_mark(0, "ACCEPT", "legal")],
            "planner_routes": ["ACCEPT"],
            "official_correct": False,
        },
        # Illegal verdict, delivered correct: no legal token at all.
        "row-illegal": {
            "reviewer_verdicts": [_mark(0, None, "review_verdict_illegal", "garbage")],
            "planner_routes": ["ACCEPT"],
            "official_correct": True,
        },
        # Two visits that AGREE (both ACCEPT); the Planner still revises the
        # first round -- the verdict is a recommendation, never a route.
        "row-two-visits-agree": {
            "reviewer_verdicts": [
                _mark(0, "ACCEPT", "legal"), _mark(1, "ACCEPT", "legal"),
            ],
            "planner_routes": ["REVISE", "ACCEPT"],
            "official_correct": True,
        },
        # Two visits that DISAGREE (ACCEPT then REVISE-FORMAT).
        "row-two-visits-disagree": {
            "reviewer_verdicts": [
                _mark(0, "ACCEPT", "legal"), _mark(1, "REVISE-FORMAT", "legal"),
            ],
            "planner_routes": ["REVISE", "ACCEPT"],
            "official_correct": True,
        },
        # Unarmed row -- never touches the stats at all.
        "row-unarmed": {
            "reviewer_verdicts": None,
            "planner_routes": ["ACCEPT"],
            "official_correct": True,
        },
    }

    stats = verifier.primitive_verdict_stats(rows)

    assert stats["armed_rows"] == 7
    assert stats["total_rows"] == 8
    # 9 visits total, 1 illegal -> 8 legal.
    assert stats["total_visits"] == 9
    assert stats["legal_visits"] == 8
    assert stats["parse_rate"] == pytest.approx(8 / 9)

    # ACCEPT: accept-correct(1) + accept-wrong(1) + two-visits-agree(2) +
    # two-visits-disagree's first mark(1) = 5.
    assert stats["token_counts"]["ACCEPT"] == 5
    assert stats["token_counts"]["REVISE-SLOT-VALUE"] == 1
    assert stats["token_counts"]["REVISE-INTENT"] == 1
    assert stats["token_counts"]["REVISE-FORMAT"] == 1
    assert stats["token_counts"]["review_verdict_illegal"] == 1

    # Precision: of the rows predicting wrong (revise-wrong, revise-correct,
    # two-visits-disagree), only revise-wrong is actually wrong -> 1/3.
    assert stats["predicted_wrong_rows"] == 3
    assert stats["revise_precision"] == pytest.approx(1 / 3)
    # Recall: of the rows actually wrong (revise-wrong, accept-wrong), only
    # revise-wrong was predicted -> 1/2.
    assert stats["actual_wrong_rows"] == 2
    assert stats["revise_recall"] == pytest.approx(1 / 2)

    # ACCEPT confusion: correct on accept-correct(1) + both two-visits-agree
    # marks(2) + two-visits-disagree's first mark(1) = 4; incorrect on
    # accept-wrong(1).
    assert stats["confusion"]["ACCEPT"] == {"correct": 4, "incorrect": 1}
    assert stats["confusion"]["REVISE-SLOT-VALUE"] == {"correct": 0, "incorrect": 1}

    # Cross-visit agreement: two multi-visit rows, one agrees.
    assert stats["multi_visit_rows"] == 2
    assert stats["cross_visit_agreement_rate"] == pytest.approx(0.5)

    # Planner route conditioned on the token, read at the SAME round each
    # mark's own visit names: an ACCEPT mark at round 0 (accept-correct,
    # accept-wrong, two-visits-disagree's first mark) sits beside a REVISE
    # route twice (both two-visits rows revise round 0 regardless of what
    # the Reviewer said) and an ACCEPT route twice (accept-correct,
    # accept-wrong); an ACCEPT mark at round 1 (two-visits-agree's second)
    # sits beside that round's ACCEPT route.
    assert stats["route_by_token"]["ACCEPT"] == {"ACCEPT": 3, "REVISE": 2}
    assert stats["route_by_token"]["REVISE-SLOT-VALUE"] == {"REVISE": 1}
    assert stats["route_by_token"]["REVISE-INTENT"] == {"REVISE": 1}
    assert stats["route_by_token"]["REVISE-FORMAT"] == {"ACCEPT": 1}
    assert stats["route_by_token"]["review_verdict_illegal"] == {"ACCEPT": 1}


def test_primitive_verdict_stats_on_zero_armed_rows_returns_none_rates():
    stats = verifier.primitive_verdict_stats(
        {"row-unarmed": {"reviewer_verdicts": None, "planner_routes": [], "official_correct": True}}
    )
    assert stats["armed_rows"] == 0
    assert stats["parse_rate"] is None
    assert stats["revise_precision"] is None
    assert stats["revise_recall"] is None
    assert stats["cross_visit_agreement_rate"] is None


def test_primitive_arms_is_empty_until_r_prim_flies():
    # The living-receipt discipline: this module never invents a sealed arm. Empty before R-PRIM flew; since
    # 0bd8157e (2026-09-22) it binds exactly the sealed R-PRIM arm, whose run id carries a committed exposure-ledger
    # row and whose verdict document is committed.
    ledger = (REPO_ROOT / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    assert [arm.key for arm in verifier.PRIMITIVE_ARMS] in ([], ["rprim"])
    for arm in verifier.PRIMITIVE_ARMS:
        assert f"| {arm.run_id} |" in ledger, arm.run_id
        assert (REPO_ROOT / arm.verdict).is_file(), arm.verdict
