"""``rails.proposer``'s second artifact family, ``slurp-slot-schema``, direct.

The EVO-S1 dry run (``test_slurp_evolution_round_driver``) exercises this
family end to end, through a whole round; this file goes at it one function at
a time, because a fail-closed parser is only worth what its refusals are worth
and a round that never sees a malformed response never proves them.

Covered here: the block-grammar parser's refusals (a line outside the grammar,
an unknown entity type, non-ASCII, a devel word 6-gram in a filler, and the
structural rules beside them), the form validator's gates (the +20 % relative
token budget, the caps, the estimator refusal, the sample-identifier rule),
and the two deterministic controls -- the shares-only floor F2 and the
token-matched form twin F3, priced here with a FAKE counter, which is exactly
the estimator a registered candidate is refused for using: legal in a test,
never in a flight.

Every intent, entity type, filler and utterance below is synthetic. No real
SLURP sentence, gold entity or TRAIN count appears in this repository. Zero
model contacts.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.data.slurp import (
    SlurpIntentSlots,
    SlurpIntentSlotSchema,
)
from speech_aware_evidence_acquisition.rails.proposer import (
    SERVING_TOKENIZER_ID,
    SLURP_MAX_FILLERS_PER_TYPE,
    SLURP_RELATIVE_TOKEN_BUDGET,
    SLURP_SLOT_SCHEMA_FAMILY,
    ProposerError,
    candidate_text,
    parse_slurp_schema_response,
    slurp_block_texts,
    slurp_blocks_from_schema,
    slurp_candidate_schema,
    slurp_form_twin_candidate,
    slurp_proposer_candidate,
    slurp_shares_only_candidate,
    validate_slurp_candidate_artifact,
)

TARGET = "alarm"
INTENTS = ("alarm_set", "alarm_query")
ENTITY_TYPES = ("date", "event_name", "time")
PROMPT_SHA = "d" * 64
EXEMPLARS = ("slurp:train:000100:synthetic-0", "slurp:train:000101:synthetic-1")

#: ``intent -> (utterances, mentions, ((entity type, mentions, fillers), ...))``
#: The unfloored table is the whole thing; ``A_0`` keeps only the types at or
#: above the 0.15 share, exactly as the real mining does.
_TRAIN = {
    "alarm_set": (
        40,
        30,
        (
            ("time", 18, ("seven am", "half past six")),
            ("date", 9, ("tomorrow",)),
            ("event_name", 3, ("stand up",)),
        ),
    ),
    "alarm_query": (20, 10, (("time", 7, ("morning",)), ("date", 3, ("today",)))),
}
_MIN_SHARE = 0.15


def schema(*, floored: bool) -> SlurpIntentSlotSchema:
    intents: dict[str, SlurpIntentSlots] = {}
    for intent, (n, mentions, rows) in _TRAIN.items():
        kept = [
            (entity_type, count, count / mentions)
            for entity_type, count, _fillers in rows
            if not floored or count / mentions >= _MIN_SHARE
        ]
        names = {entity_type for entity_type, _c, _s in kept}
        intents[intent] = SlurpIntentSlots(
            intent=intent,
            n=n,
            mentions=mentions,
            types=tuple(kept),
            fillers={
                entity_type: tuple(examples)
                for entity_type, _count, examples in rows
                if entity_type in names
            },
        )
    return SlurpIntentSlotSchema(
        schema_id="synthetic-slot-schema-v1",
        source_split="train",
        source_identity_hash="e" * 64,
        utterance_count=sum(n for n, _m, _rows in _TRAIN.values()),
        min_share=_MIN_SHARE if floored else 0.0,
        examples_per_type=5,
        intents=intents,
    )


UNFLOORED = schema(floored=False)
BASE = schema(floored=True)
INCUMBENT_BLOCKS = slurp_blocks_from_schema(BASE, INTENTS)
INCUMBENT_TEXTS = slurp_block_texts(BASE, intents=INTENTS)


def words(text: str) -> int:
    """The fake tokenizer: one token per whitespace-separated word."""

    return len(text.split())


def characters(text: str) -> int:
    """A second fake tokenizer, for the case a word counter cannot show."""

    return len(text)


def candidate(blocks, *, k: int = 1):
    return slurp_proposer_candidate(
        blocks,
        target_id=TARGET,
        round=1,
        k=k,
        proposer_prompt_sha256=PROMPT_SHA,
        exemplar_ids=EXEMPLARS,
    )


def validate(artifact, *, counter=words, **overrides):
    kwargs = {
        "unfloored": UNFLOORED,
        "base": BASE,
        "incumbent_blocks": INCUMBENT_TEXTS,
        "token_counter": counter,
        "token_counter_id": "test:word-counter",
        "allow_estimator": True,
    }
    kwargs.update(overrides)
    return validate_slurp_candidate_artifact(artifact, **kwargs)


def response(*lines: str) -> str:
    return "\n".join(lines)


LEGAL_RESPONSE = response(
    "== alarm_set == 40 TRAIN utterances, 30 slot mentions",
    "- time (60.0 percent of slot mentions): quarter past six; seven in the morning",
    "- date (30.0 percent of slot mentions): tomorrow; next monday",
    "== alarm_query == 20 TRAIN utterances, 10 slot mentions",
    "- time (70.0 percent of slot mentions): morning",
    "- date (30.0 percent of slot mentions): today",
)


def parse(text: str, **overrides):
    kwargs = {
        "expected_intents": INTENTS,
        "allowed_entity_types": ENTITY_TYPES,
    }
    kwargs.update(overrides)
    return parse_slurp_schema_response(text, **kwargs)


# ---------------------------------------------------------------------------
# The block-grammar parser
# ---------------------------------------------------------------------------


def test_a_legal_response_parses_into_ordered_blocks_without_numbers():
    blocks = parse(LEGAL_RESPONSE)
    assert list(blocks) == list(INTENTS)
    assert [entry["entity_type"] for entry in blocks["alarm_set"]["types"]] == [
        "time",
        "date",
    ]
    assert blocks["alarm_set"]["types"][0]["fillers"] == [
        "quarter past six",
        "seven in the morning",
    ]
    # A candidate never carries a count or a share: the header's numbers and
    # the type line's percentage are parsed and thrown away.
    assert all(
        set(entry) == {"entity_type", "fillers"}
        for intent in blocks
        for entry in blocks[intent]["types"]
    )


def test_the_parsed_numbers_are_discarded_and_re_derived_from_train():
    """A hallucinated count cannot reach a flight."""

    lied = LEGAL_RESPONSE.replace(
        "== alarm_set == 40 TRAIN utterances, 30 slot mentions",
        "== alarm_set == 9999 TRAIN utterances, 8888 slot mentions",
    ).replace("- time (60.0 percent", "- time (99.9 percent")
    blocks = parse(lied)
    rendered = slurp_block_texts(
        slurp_candidate_schema(blocks, unfloored=UNFLOORED, base=BASE),
        intents=("alarm_set",),
    )["alarm_set"]
    assert rendered.startswith("== alarm_set == 40 TRAIN utterances, 30 slot mentions")
    assert "60.0 percent" in rendered
    assert "9999" not in rendered and "99.9" not in rendered


def test_a_line_outside_the_grammar_is_refused():
    with pytest.raises(ProposerError, match="outside the block grammar"):
        parse(response("Here are the rewritten blocks:", *LEGAL_RESPONSE.split("\n")))
    # Including prose that merely LOOKS like a type line.
    with pytest.raises(ProposerError, match="outside the block grammar"):
        parse(LEGAL_RESPONSE + "\n- time: seven am")


def test_a_type_line_before_any_header_is_refused():
    with pytest.raises(ProposerError, match="before any block header"):
        parse(
            response(
                "- time (60.0 percent of slot mentions): seven am",
                *LEGAL_RESPONSE.split("\n"),
            )
        )


def test_an_entity_type_outside_the_offered_list_is_refused():
    with pytest.raises(ProposerError, match="not one of the type names"):
        parse(LEGAL_RESPONSE.replace("- date (30.0", "- alarm_type (30.0", 1))


def test_non_ascii_anywhere_is_refused():
    with pytest.raises(ProposerError, match="non-ASCII"):
        parse(LEGAL_RESPONSE.replace("tomorrow", "tomorrow—ish"))


def test_a_filler_carrying_a_refused_devel_six_gram_is_refused():
    """The decontamination gate, at the parser rather than after the flight."""

    devel_gram = "quarter past six in the morning"
    with pytest.raises(ProposerError, match="refused word 6-gram"):
        parse(
            LEGAL_RESPONSE.replace(
                "quarter past six; seven in the morning",
                "a quarter past six in the morning",
            ),
            refuse_ngrams=(devel_gram,),
        )
    # The same response is legal when the gram is not one of the refused ones.
    assert parse(
        LEGAL_RESPONSE.replace(
            "quarter past six; seven in the morning",
            "a quarter past six in the morning",
        ),
        refuse_ngrams=("some other six word gram here",),
    )


def test_a_short_filler_cannot_trip_the_six_gram_gate():
    """Fewer than six words is no 6-gram at all, refused list or not."""

    assert parse(LEGAL_RESPONSE, refuse_ngrams=("quarter past six in the morning",))


def test_the_structural_rules_beside_the_grammar():
    blank = LEGAL_RESPONSE.replace(
        "== alarm_query", "\n== alarm_query"
    )
    with pytest.raises(ProposerError, match="blank"):
        parse(blank)
    with pytest.raises(ProposerError, match="trailing whitespace"):
        parse(LEGAL_RESPONSE.replace("): tomorrow; next monday", "): tomorrow; next  "))
    with pytest.raises(ProposerError, match="second block"):
        parse(response(*LEGAL_RESPONSE.split("\n"), *LEGAL_RESPONSE.split("\n")))
    with pytest.raises(ProposerError, match="lists entity type 'time' twice"):
        parse(LEGAL_RESPONSE.replace("- date (30.0", "- time (30.0", 1))
    with pytest.raises(ProposerError, match="carry no entity type line"):
        parse(
            response(
                "== alarm_set == 40 TRAIN utterances, 30 slot mentions",
                "== alarm_query == 20 TRAIN utterances, 10 slot mentions",
                "- time (70.0 percent of slot mentions): morning",
            )
        )


def test_blocks_out_of_the_asked_order_are_refused():
    reversed_response = response(
        *LEGAL_RESPONSE.split("\n")[3:], *LEGAL_RESPONSE.split("\n")[:3]
    )
    with pytest.raises(ProposerError, match="not exactly"):
        parse(reversed_response)
    # The same text IS legal when that is the order the draw asked for.
    assert list(parse(reversed_response, expected_intents=INTENTS[::-1])) == [
        "alarm_query",
        "alarm_set",
    ]


def test_more_than_five_fillers_on_a_line_is_refused_at_the_parser():
    fillers = "; ".join(f"filler {index}" for index in range(SLURP_MAX_FILLERS_PER_TYPE + 1))
    with pytest.raises(ProposerError, match="over the 5-filler cap"):
        parse(LEGAL_RESPONSE.replace("tomorrow; next monday", fillers))


# ---------------------------------------------------------------------------
# The form validator
# ---------------------------------------------------------------------------


def test_the_incumbent_itself_validates_at_zero_token_delta():
    report = validate(candidate(INCUMBENT_BLOCKS))
    assert report.artifact_family == SLURP_SLOT_SCHEMA_FAMILY
    assert [record["intent"] for record in report.per_key] == sorted(INTENTS)
    assert all(record["token_delta"] == 0 for record in report.per_key)
    assert all(record["lines"] <= record["line_cap"] for record in report.per_key)
    assert report.exemplar_overlap_count == 0


def test_a_block_over_the_relative_token_budget_is_refused():
    fat = {
        "alarm_set": {
            "types": [
                {
                    "entity_type": "time",
                    "fillers": [
                        f"a very long spoken time phrase number {index}"
                        for index in range(SLURP_MAX_FILLERS_PER_TYPE)
                    ],
                },
                {"entity_type": "date", "fillers": ["tomorrow"]},
            ]
        }
    }
    with pytest.raises(ProposerError, match="over the .*-token relative budget"):
        validate(candidate(fat))


def test_the_budget_is_relative_and_a_small_growth_passes():
    incumbent_tokens = words(INCUMBENT_TEXTS["alarm_set"])
    budget = int(incumbent_tokens * (1.0 + SLURP_RELATIVE_TOKEN_BUDGET))
    assert budget > incumbent_tokens, "a +20 % budget must leave room to grow"
    grown = {
        "alarm_set": {
            "types": [
                {"entity_type": "time", "fillers": ["seven am", "half past six"]},
                {"entity_type": "date", "fillers": ["tomorrow", "next monday"]},
            ]
        }
    }
    report = validate(candidate(grown))
    record = report.per_key[0]
    assert record["incumbent_tokens"] == incumbent_tokens
    assert record["token_budget"] == budget
    assert 0 < record["token_delta"] <= budget - incumbent_tokens


def test_the_line_cap_is_the_unfloored_train_type_count():
    """A candidate may add back a floored type, and stops exactly there.

    ``event_name`` is under the 0.15 floor, so ``A_0`` does not list it and a
    proposer that adds it is doing the thing this cell is for. The cap is one
    header plus every type the UNFLOORED table records, which is also the most
    a block can carry: :func:`slurp_candidate_schema` refuses a type TRAIN
    never records for that intent, so the cap cannot be passed from here --
    it is a belt over a braces, and this test pins where the buckle sits.
    """

    maximal = {
        "alarm_set": {
            "types": [
                {"entity_type": "time", "fillers": ["seven"]},
                {"entity_type": "date", "fillers": ["tomorrow"]},
                {"entity_type": "event_name", "fillers": ["standup"]},
            ]
        }
    }
    record = validate(candidate(maximal)).per_key[0]
    assert record["line_cap"] == 1 + len(UNFLOORED.intents["alarm_set"].types) == 4
    assert record["lines"] == record["line_cap"]
    with pytest.raises(ProposerError, match="TRAIN never records for it"):
        validate(
            candidate(
                {
                    "alarm_set": {
                        "types": [
                            {"entity_type": "time", "fillers": ["seven am"]},
                            {"entity_type": "news_topic", "fillers": ["local sport"]},
                        ]
                    }
                }
            )
        )


def test_more_than_five_fillers_per_type_is_refused_at_the_validator_too():
    """The parser is not the only door: a control could build one directly."""

    over = {
        "alarm_set": {
            "types": [
                {
                    "entity_type": "time",
                    "fillers": [f"time {index}" for index in range(6)],
                }
            ]
        }
    }
    with pytest.raises(ProposerError, match="over the 5-filler cap"):
        validate(candidate(over))


def test_a_filler_carrying_a_sample_identifier_is_refused():
    with pytest.raises(ProposerError, match="sample identifier"):
        validate(
            candidate(
                {
                    "alarm_set": {
                        "types": [
                            {
                                "entity_type": "time",
                                "fillers": ["seven am from slurp:train:000123"],
                            }
                        ]
                    }
                }
            )
        )


def test_a_filler_sharing_a_devel_six_gram_is_refused_unless_a0_carries_it():
    shared = "set an alarm for a quarter past six"
    leaky = {
        "alarm_set": {
            "types": [
                {"entity_type": "time", "fillers": ["an alarm for a quarter past six"]}
            ]
        }
    }
    with pytest.raises(ProposerError, match="word 6-gram"):
        validate(candidate(leaky), evaluation_sentence_texts=(shared,))
    # A_0's own fillers are TRAIN and were already sent, so they are exempt.
    assert validate(
        candidate(leaky),
        evaluation_sentence_texts=(shared,),
        baseline_filler_texts=("an alarm for a quarter past six",),
    )


def test_exemplar_overlap_is_counted_and_never_gated():
    exemplar = "please set an alarm for a quarter past six"
    report = validate(
        candidate(
            {
                "alarm_set": {
                    "types": [
                        {
                            "entity_type": "time",
                            "fillers": ["an alarm for a quarter past six"],
                        }
                    ]
                }
            }
        ),
        exemplar_texts=(exemplar,),
    )
    assert report.exemplar_overlap_count > 0
    assert all(len(gram.split()) == 6 for gram in report.exemplar_overlap_ngrams)


def test_an_estimator_priced_candidate_is_refused_for_registration():
    artifact = candidate(INCUMBENT_BLOCKS)
    with pytest.raises(ProposerError, match="not the serving geometry's own tokenizer"):
        validate(artifact, allow_estimator=False)
    report = validate(artifact, token_counter_id=SERVING_TOKENIZER_ID, allow_estimator=False)
    assert report.token_counter_id == SERVING_TOKENIZER_ID


def test_an_a2t_candidate_is_refused_by_the_slurp_validator():
    from speech_aware_evidence_acquisition.rails.proposer import proposer_candidate

    other = proposer_candidate(
        "a cue",
        {"toolA0": "a description", "toolA1": "another description"},
        target_id="pair-a",
        round=1,
        k=1,
        proposer_prompt_sha256=PROMPT_SHA,
        exemplar_ids=EXEMPLARS,
    )
    with pytest.raises(ProposerError, match="is a 'a2t-descriptions' artifact"):
        validate(other)


# ---------------------------------------------------------------------------
# The two deterministic controls
# ---------------------------------------------------------------------------


def test_f2_is_the_incumbent_with_every_filler_deleted():
    control = slurp_shares_only_candidate(
        INCUMBENT_BLOCKS, target_id=TARGET, round=1, k=4
    )
    assert control.family == "deterministic"
    assert control.artifact_family == SLURP_SLOT_SCHEMA_FAMILY
    assert control.proposer_prompt_sha256 is None
    assert control.exemplar_ids == ()
    for intent in INTENTS:
        incumbent = INCUMBENT_BLOCKS[intent]["types"]
        floor = control.descriptions[intent]["types"]
        assert [entry["entity_type"] for entry in floor] == [
            entry["entity_type"] for entry in incumbent
        ]
        assert all(entry["fillers"] == [] for entry in floor)
    rendered = slurp_block_texts(
        slurp_candidate_schema(control.descriptions, unfloored=UNFLOORED, base=BASE),
        intents=INTENTS,
    )
    assert "no example filler recorded" in rendered["alarm_set"]
    assert rendered["alarm_set"].startswith(INCUMBENT_TEXTS["alarm_set"].split("\n")[0])
    # Deterministic: the same inputs give the same id, and no contact was made.
    again = slurp_shares_only_candidate(
        INCUMBENT_BLOCKS, target_id=TARGET, round=1, k=4
    )
    assert again.candidate_id == control.candidate_id


def test_f3_is_a_token_matched_twin_of_the_incumbent_form():
    twin = slurp_form_twin_candidate(
        INCUMBENT_BLOCKS,
        unfloored=UNFLOORED,
        base=BASE,
        token_counter=words,
        target_id=TARGET,
        round=1,
        k=5,
    )
    assert twin.family == "placebo"
    assert twin.proposer_prompt_sha256 is None and twin.exemplar_ids == ()
    rendered = slurp_block_texts(
        slurp_candidate_schema(twin.descriptions, unfloored=UNFLOORED, base=BASE),
        intents=INTENTS,
    )
    for intent in INTENTS:
        incumbent = INCUMBENT_BLOCKS[intent]["types"]
        matched = twin.descriptions[intent]["types"]
        # The type list, its order and the filler COUNTS are the incumbent's.
        assert [entry["entity_type"] for entry in matched] == [
            entry["entity_type"] for entry in incumbent
        ]
        assert [len(entry["fillers"]) for entry in matched] == [
            len(entry["fillers"]) for entry in incumbent
        ]
        # ... and the content is neutral placeholder words, not the fillers.
        for entry, original in zip(matched, incumbent):
            assert not set(entry["fillers"]) & set(original["fillers"])
        assert words(rendered[intent]) == words(INCUMBENT_TEXTS[intent])
    again = slurp_form_twin_candidate(
        INCUMBENT_BLOCKS,
        unfloored=UNFLOORED,
        base=BASE,
        token_counter=words,
        target_id=TARGET,
        round=1,
        k=5,
    )
    assert again.candidate_id == twin.candidate_id


def test_f3_refuses_to_approximate_a_block_it_cannot_match_downward():
    """Padding is the only move, so an over-long twin is refused, not trimmed."""

    with pytest.raises(ProposerError, match="a shorter twin would have to delete"):
        slurp_form_twin_candidate(
            INCUMBENT_BLOCKS,
            unfloored=UNFLOORED,
            base=BASE,
            token_counter=characters,
            target_id=TARGET,
            round=1,
            k=5,
            placeholders=("a rather long placeholder phrase",),
        )


def test_f3_refuses_a_counter_that_is_not_a_counter():
    with pytest.raises(ProposerError, match="token_counter must be callable"):
        slurp_form_twin_candidate(
            INCUMBENT_BLOCKS,
            unfloored=UNFLOORED,
            base=BASE,
            token_counter="llama-server",
            target_id=TARGET,
            round=1,
            k=5,
        )


def test_the_two_controls_and_a_proposal_are_three_different_candidates():
    proposed = candidate(parse(LEGAL_RESPONSE), k=1)
    floor = slurp_shares_only_candidate(INCUMBENT_BLOCKS, target_id=TARGET, round=1, k=4)
    twin = slurp_form_twin_candidate(
        INCUMBENT_BLOCKS,
        unfloored=UNFLOORED,
        base=BASE,
        token_counter=words,
        target_id=TARGET,
        round=1,
        k=5,
    )
    assert len({proposed.candidate_id, floor.candidate_id, twin.candidate_id}) == 3


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_the_canonical_text_names_the_family_and_keeps_the_type_order():
    text = candidate_text(
        INCUMBENT_BLOCKS, None, artifact_family=SLURP_SLOT_SCHEMA_FAMILY
    )
    assert text.split("\n")[0] == f"artifact: {SLURP_SLOT_SCHEMA_FAMILY}"
    reordered = {
        "alarm_set": {
            "types": list(reversed(INCUMBENT_BLOCKS["alarm_set"]["types"])),
        }
    }
    straight = {"alarm_set": {"types": INCUMBENT_BLOCKS["alarm_set"]["types"]}}
    assert candidate(reordered).candidate_id != candidate(straight).candidate_id
