"""The free refresh delivery rule (``core.repair_alignment.accept_free_refresh``).

DR-1f's whole claim is the opposite of KC-E1f's: it delivers what the core
said, so a verdict can price the risk KC-E1 paid 2,242 non-entity deletions
for. These tests fix that behaviour, and -- more importantly -- fix the
narrow set of places where the free rule and the bounded rule must AGREE, so
the DR-1c/DR-1f contrast stays a contrast about edits rather than about
saturation handling or empty drafts.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.core.base import (
    RESPONSE_POSTPROCESSORS,
    RepairAlignmentError,
)
from speech_aware_evidence_acquisition.core.repair_alignment import (
    E21_FREE_REFRESH_DELIVERY_V1,
    FREE_REFRESH_REFUSAL_REASONS,
    REFUSAL_REASONS,
    REJECTION_CLASSES,
    accept_entity_repair,
    accept_free_refresh,
    free_refresh_delivery_v1,
    summarize_outcomes,
)

DRAFT = (
    "Thank you and good morning everyone welcome to the fourth quarter earnings "
    "call I would like to turn the call over to our President and Chief Executive "
    "Officer Brett Ponton who will walk you through the results for the quarter"
)


def test_the_rule_is_registered_under_its_own_id():
    assert RESPONSE_POSTPROCESSORS.resolve(E21_FREE_REFRESH_DELIVERY_V1) is not None


def test_the_registered_entry_refuses_parameters():
    # A fragment pinning a span bound here would declare a constraint the rule
    # does not apply, and the cell's one factor would be false in its own hash.
    with pytest.raises(RepairAlignmentError):
        free_refresh_delivery_v1(max_span_tokens=4)
    assert callable(free_refresh_delivery_v1())


class TestTheFreeDelivery:
    def test_a_response_is_delivered_verbatim(self):
        response = "Completely different words, punctuated differently!"
        outcome = accept_free_refresh(DRAFT, response)
        assert outcome.text == response
        assert outcome.refused is False
        assert outcome.delivery == "verbatim-response"
        assert outcome.changed is True

    def test_a_deletion_is_delivered_and_not_refused(self):
        # This is the KC-E1 failure mode. The bounded rule refuses it; the free
        # rule delivers it, which is the risk DR-1f exists to measure.
        response = " ".join(DRAFT.split()[:20])
        bounded = accept_entity_repair(DRAFT, response)
        free = accept_free_refresh(DRAFT, response)
        assert bounded.text == DRAFT
        assert free.text == response
        assert len(free.text.split()) < len(DRAFT.split())

    def test_a_runaway_answer_is_delivered_where_the_bounded_rule_refuses_it(self):
        response = "yes yes yes " * 40
        assert accept_entity_repair(DRAFT, response).refusal_reason == (
            "anchor_ratio_below_floor"
        )
        free = accept_free_refresh(DRAFT, response)
        assert free.refused is False
        assert free.text == response

    def test_an_unchanged_response_is_reported_unchanged(self):
        outcome = accept_free_refresh(DRAFT, DRAFT)
        assert outcome.text == DRAFT
        assert outcome.changed is False
        assert outcome.refused is False


class TestWhereTheTwoRulesMustAgree:
    """The two arms differ in ONE thing. These are the places they do not."""

    def test_an_empty_response_delivers_the_draft_under_both_rules(self):
        # The base policy's saturation/skip quarantine arrives as "".
        for response in ("", "   \n  "):
            bounded = accept_entity_repair(DRAFT, response)
            free = accept_free_refresh(DRAFT, response)
            assert bounded.text == DRAFT
            assert free.text == DRAFT
            assert bounded.refusal_reason == "empty_response"
            assert free.refusal_reason == "empty_response"

    def test_an_empty_draft_delivers_nothing_under_both_rules(self):
        # The two windows of the 1,593 whose stitched unit draft is empty.
        bounded = accept_entity_repair("", "some words the core heard")
        free = accept_free_refresh("", "some words the core heard")
        assert bounded.text == ""
        assert free.text == ""
        assert bounded.refusal_reason == "empty_predecessor"
        assert free.refusal_reason == "empty_predecessor"

    def test_the_free_refusal_set_is_a_strict_subset(self):
        assert set(FREE_REFRESH_REFUSAL_REASONS) < set(REFUSAL_REASONS)
        assert set(REFUSAL_REASONS) - set(FREE_REFRESH_REFUSAL_REASONS) == {
            "anchor_ratio_below_floor",
            "substituted_fraction_above_ceiling",
        }


class TestTheLedger:
    def test_the_opcodes_the_bounded_rule_would_reject_are_counted(self):
        response = DRAFT + " and one more sentence entirely"
        outcome = accept_free_refresh(DRAFT, response)
        assert set(outcome.rejected) == set(REJECTION_CLASSES)
        assert outcome.rejected["insertion"] == 1
        # Counted, never acted on.
        assert outcome.text == response

    def test_the_trace_view_names_the_delivery_and_carries_no_surface_forms(self):
        outcome = accept_free_refresh(DRAFT, DRAFT.replace("Ponton", "Pontone"))
        view = outcome.trace_view()
        assert view["obs_repair_delivery"] == "verbatim-response"
        assert view["obs_repair_changed"] is True
        assert "Pontone" not in repr(view)

    def test_the_bounded_rule_still_names_itself(self):
        outcome = accept_entity_repair(DRAFT, DRAFT.replace("Ponton", "Pontone"))
        assert outcome.delivery == "substitution-splice"
        assert outcome.changed is True
        assert outcome.trace_view()["obs_repair_delivery"] == "substitution-splice"

    def test_a_summary_names_which_rule_delivered(self):
        outcomes = [
            accept_free_refresh(DRAFT, "a wholly new transcript of the window"),
            accept_free_refresh(DRAFT, ""),
            accept_free_refresh(DRAFT, DRAFT),
        ]
        summary = summarize_outcomes(outcomes)
        assert summary["deliveries"] == {"verbatim-response": 3}
        assert summary["windows_refused"] == 1
        assert summary["windows_changed"] == 1
        assert summary["windows_unchanged_and_accepted"] == 1
        assert summary["substitutions"] == 0
