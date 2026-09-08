"""The substitution-only delivery rule (``core.repair_alignment``).

KC-E1f's whole claim rests on one property: the delivered hypothesis can
differ from its sealed pass-1 predecessor by SUBSTITUTIONS only, so the
non-entity deletion profile the KC-E1 verdict rejected the brief for is the
comparator's by construction. These tests are that property's proof, on
synthetic pairs -- an accepted substitution, a rejected insertion, a rejected
deletion, a refused garbage response -- plus the invariant every outcome must
satisfy.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.core.base import (
    RESPONSE_POSTPROCESSORS,
    RepairAlignmentError,
)
from speech_aware_evidence_acquisition.core.repair_alignment import (
    E21_ENTITY_REPAIR_SUBSTITUTIONS_V1,
    REFUSAL_REASONS,
    REJECTION_CLASSES,
    accept_entity_repair,
    entity_repair_substitutions_v1,
    summarize_outcomes,
)

# A pass-1 hypothesis long enough that a single edit stays under the 10 %
# substituted-token ceiling: 40 tokens, so up to 4 substituted tokens pass.
PASS1 = (
    "Thank you and good morning everyone welcome to the fourth quarter earnings "
    "call I would like to turn the call over to our President and Chief Executive "
    "Officer Brett Ponton who will walk you through the results for the quarter"
)


def test_pass1_is_the_length_these_cases_assume():
    assert len(PASS1.split()) == 40


class TestAcceptedSubstitution:
    def test_a_one_token_name_repair_is_accepted_and_spliced_in_place(self):
        returned = PASS1.replace("Ponton", "Pontone")
        outcome = accept_entity_repair(PASS1, returned)
        assert not outcome.refused
        assert outcome.refusal_reason is None
        assert outcome.text == returned
        assert [(item.before, item.after) for item in outcome.substitutions] == [
            ("Ponton", "Pontone")
        ]
        assert outcome.substituted_tokens == 1
        assert outcome.anchor_tokens == 39

    def test_a_two_token_name_repair_within_the_span_bound_is_accepted(self):
        returned = PASS1.replace("Brett Ponton", "Brent Pontone")
        outcome = accept_entity_repair(PASS1, returned)
        assert not outcome.refused
        assert outcome.text == returned
        assert outcome.substituted_tokens == 2

    def test_untouched_bytes_survive_exactly_including_punctuation(self):
        pass1 = "Welcome, everyone. With that, I hand over to Brett Ponton -- thanks."
        returned = "Welcome, everyone. With that, I hand over to Brent Ponton -- thanks."
        outcome = accept_entity_repair(pass1, returned, max_substituted_fraction=1.0)
        assert outcome.text == returned
        assert outcome.text.count(",") == pass1.count(",")

    def test_an_unchanged_response_delivers_the_predecessor_and_is_not_a_refusal(self):
        outcome = accept_entity_repair(PASS1, PASS1)
        assert not outcome.refused
        assert not outcome.changed
        assert outcome.text == PASS1
        assert outcome.anchor_tokens == 40

    def test_a_span_longer_than_the_bound_is_rejected_not_spliced(self):
        # Seven consecutive tokens replaced by seven novel ones: a balanced
        # replace, so only the span bound can stop it -- and it does.
        tokens = PASS1.split()
        returned = " ".join(
            tokens[:20] + [f"zzz{index}" for index in range(7)] + tokens[27:]
        )
        outcome = accept_entity_repair(PASS1, returned, max_substituted_fraction=1.0)
        assert outcome.text == PASS1
        assert outcome.substitutions == ()
        assert outcome.rejected["oversized_replace"] == 1


class TestRejectedInsertion:
    def test_added_words_are_dropped_and_counted(self):
        returned = PASS1.replace(
            "welcome to the fourth quarter",
            "welcome once again to the fourth quarter",
        )
        outcome = accept_entity_repair(PASS1, returned)
        assert not outcome.refused
        assert outcome.text == PASS1
        assert outcome.rejected["insertion"] == 1
        assert outcome.substitutions == ()

    def test_a_read_aloud_brief_appended_to_the_transcript_never_reaches_the_delivery(self):
        returned = PASS1 + " Participants Brett Ponton Chief Executive Officer"
        outcome = accept_entity_repair(PASS1, returned)
        assert outcome.text == PASS1
        assert outcome.rejected["insertion"] == 1

    def test_an_insertion_beside_a_legal_substitution_keeps_only_the_substitution(self):
        returned = PASS1.replace("Ponton", "Pontone").replace(
            "good morning everyone", "good morning to everyone"
        )
        outcome = accept_entity_repair(PASS1, returned)
        assert not outcome.refused
        assert outcome.rejected["insertion"] == 1
        assert [item.after for item in outcome.substitutions] == ["Pontone"]
        assert outcome.text == PASS1.replace("Ponton", "Pontone")


class TestRejectedDeletion:
    def test_dropped_words_are_restored_from_the_predecessor(self):
        returned = PASS1.replace("who will walk you through the results ", "")
        outcome = accept_entity_repair(PASS1, returned, min_anchor_ratio=0.0)
        assert outcome.text == PASS1
        assert outcome.rejected["deletion"] == 1
        assert outcome.substitutions == ()

    def test_a_deletion_disguised_as_a_replace_is_rejected_as_unbalanced(self):
        returned = PASS1.replace("our President and Chief Executive Officer", "our CEO")
        outcome = accept_entity_repair(PASS1, returned, min_anchor_ratio=0.0)
        assert outcome.text == PASS1
        assert outcome.rejected["unbalanced_replace"] == 1

    def test_the_deletion_the_kc_e1_verdict_measured_cannot_be_expressed(self):
        # KC-E1 bought 152 PERSON substitutions with 2,242 extra non-entity
        # deletions. A pass-2 response that transcribes LESS is exactly that
        # failure, and here it changes nothing at all.
        returned = " ".join(PASS1.split()[:12])
        outcome = accept_entity_repair(PASS1, returned, min_anchor_ratio=0.0)
        assert outcome.text == PASS1
        assert len(outcome.text.split()) == 40


class TestRefusedGarbage:
    def test_an_unrelated_answer_is_refused_by_the_anchor_floor(self):
        returned = (
            "Here are the corrected named entities: Brett Ponton, Chief Executive "
            "Officer; the fourth quarter results follow in the attached table."
        )
        outcome = accept_entity_repair(PASS1, returned)
        assert outcome.refused
        assert outcome.refusal_reason == "anchor_ratio_below_floor"
        assert outcome.text == PASS1
        assert outcome.substitutions == ()

    def test_an_empty_response_is_refused_by_name(self):
        outcome = accept_entity_repair(PASS1, "   \n\t ")
        assert outcome.refused
        assert outcome.refusal_reason == "empty_response"
        assert outcome.text == PASS1

    def test_a_wholesale_rewrite_that_preserves_token_counts_is_still_refused(self):
        # Five single-token substitutions, each individually legal, spread far
        # enough apart that difflib keeps them separate. Five of forty tokens
        # is 12.5 %, above the 10 % ceiling: legal edits in illegal quantity.
        tokens = PASS1.split()
        for offset, index in enumerate(range(1, 40, 8)):
            tokens[index] = f"zzz{offset}"
        outcome = accept_entity_repair(PASS1, " ".join(tokens))
        assert outcome.refused
        assert outcome.refusal_reason == "substituted_fraction_above_ceiling"
        assert outcome.substituted_tokens == 5
        assert outcome.text == PASS1

    def test_an_empty_predecessor_stays_empty_and_says_why(self):
        # A pass-1 window the comparator quarantined at the decode cap
        # contributed the empty string to its own stitch; a pass-2 answer may
        # not fill that hole in.
        outcome = accept_entity_repair("", "Some transcript the second pass invented")
        assert outcome.refused
        assert outcome.refusal_reason == "empty_predecessor"
        assert outcome.text == ""

    def test_every_named_refusal_reason_is_reachable(self):
        spread = PASS1.split()
        for offset, index in enumerate(range(1, 40, 8)):
            spread[index] = f"zzz{offset}"
        seen = {
            accept_entity_repair("", "x").refusal_reason,
            accept_entity_repair(PASS1, "").refusal_reason,
            accept_entity_repair(PASS1, "totally different sentence entirely").refusal_reason,
            accept_entity_repair(PASS1, " ".join(spread)).refusal_reason,
        }
        assert seen == set(REFUSAL_REASONS)


class TestInvariant:
    @pytest.mark.parametrize(
        "returned",
        [
            PASS1,
            PASS1.replace("Ponton", "Pontone"),
            PASS1 + " and thank you all again for joining",
            " ".join(PASS1.split()[:5]),
            "",
            "   ",
            "completely unrelated text about something else entirely",
            PASS1.replace("fourth quarter", "4th qtr of fiscal"),
            PASS1.upper(),
            "\n".join(PASS1.split()),
        ],
    )
    def test_the_delivered_token_count_always_equals_the_predecessors(self, returned):
        outcome = accept_entity_repair(PASS1, returned)
        assert len(outcome.text.split()) == len(PASS1.split())

    def test_a_refusal_delivers_the_predecessor_byte_for_byte(self):
        pass1 = "  leading and   irregular   spacing  is preserved  "
        outcome = accept_entity_repair(pass1, "nothing like the predecessor at all here")
        assert outcome.refused
        assert outcome.text == pass1


class TestRegistryEntry:
    def test_the_id_resolves_in_the_core_base_registry(self):
        entry = RESPONSE_POSTPROCESSORS.resolve(E21_ENTITY_REPAIR_SUBSTITUTIONS_V1)
        rule = entry()
        outcome = rule(PASS1, PASS1.replace("Ponton", "Pontone"))
        assert not outcome.refused
        assert outcome.substituted_tokens == 1

    def test_params_ride_through_the_factory(self):
        rule = entity_repair_substitutions_v1(max_span_tokens=1)
        returned = PASS1.replace("Brett Ponton", "Brent Pontone")
        assert rule(PASS1, returned).text == PASS1

    def test_an_unknown_param_is_refused(self):
        with pytest.raises(RepairAlignmentError):
            entity_repair_substitutions_v1(max_spam_tokens=3)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"max_span_tokens": 0},
            {"min_anchor_ratio": 1.5},
            {"max_substituted_fraction": -0.1},
        ],
    )
    def test_bad_parameters_refuse_rather_than_guess(self, kwargs):
        with pytest.raises(RepairAlignmentError):
            accept_entity_repair(PASS1, PASS1, **kwargs)


class TestSummary:
    def test_the_roll_up_reports_a_complete_table(self):
        outcomes = [
            accept_entity_repair(PASS1, PASS1),
            accept_entity_repair(PASS1, PASS1.replace("Ponton", "Pontone")),
            accept_entity_repair(PASS1, ""),
            accept_entity_repair(PASS1, PASS1 + " extra words appended here"),
        ]
        summary = summarize_outcomes(outcomes)
        assert summary["windows"] == 4
        assert summary["windows_refused"] == 1
        assert summary["windows_changed"] == 1
        assert summary["substitutions"] == 1
        assert set(summary["refusal_reasons"]) == set(REFUSAL_REASONS)
        assert set(summary["rejected_opcodes"]) == set(REJECTION_CLASSES)
        assert summary["rejected_opcodes"]["insertion"] == 1

    def test_the_trace_view_carries_no_surface_forms(self):
        outcome = accept_entity_repair(PASS1, PASS1.replace("Ponton", "Pontone"))
        view = outcome.trace_view()
        assert "Pontone" not in repr(view)
        assert view["obs_repair_substitutions"] == 1
        assert view["obs_repair_refused"] is False
