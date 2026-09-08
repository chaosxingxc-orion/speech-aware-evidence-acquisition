"""``reproduction.obs_ownership``: which words of a context-delivered unit are
the unit's own.

Pure inputs, pure outputs, no sealed artifact and no audio. The properties
under test are the ones the OBS-E1b preregistration leans on: a plan with no
context bounds behaves exactly as v1/v2 did, an anchored cut is gapless and
duplication-free, the two cuts of one unit can never cross, and every rule the
stitch used is on the record.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.reproduction import obs_ownership as own


def _unit(index: int, start: float, end: float, text: str, *, margin: float = 5.0):
    return own.OwnershipUnit(
        unit_id=f"CALL#u{index:04d}",
        turn_start_seconds=start,
        turn_end_seconds=end,
        context_start_seconds=max(0.0, start - margin),
        context_end_seconds=end + margin,
        text=text,
    )


def _abutting(index: int, start: float, end: float, text: str):
    return own.OwnershipUnit(
        unit_id=f"CALL#u{index:04d}",
        turn_start_seconds=start,
        turn_end_seconds=end,
        context_start_seconds=start,
        context_end_seconds=end,
        text=text,
    )


class TestNoContext:
    def test_units_with_no_context_deliver_their_responses_unchanged(self):
        units = [
            _abutting(1, 0.0, 10.0, "alpha bravo charlie"),
            _abutting(2, 10.0, 20.0, "delta echo"),
            _abutting(3, 20.0, 30.0, "foxtrot golf hotel"),
        ]
        decisions = own.resolve_ownership(units)
        assert [d.delivered_text for d in decisions] == [u.text for u in units]
        assert own.stitch(decisions) == "alpha bravo charlie delta echo foxtrot golf hotel"
        assert {d.right_rule for d in decisions[:-1]} == {own.RULE_NO_OVERLAP}

    def test_internal_whitespace_survives_an_untrimmed_unit(self):
        units = [_abutting(1, 0.0, 10.0, "alpha  bravo\ncharlie")]
        (decision,) = own.resolve_ownership(units)
        assert decision.delivered_text == "alpha  bravo\ncharlie"

    def test_an_empty_unit_contributes_nothing_and_is_counted(self):
        units = [
            _abutting(1, 0.0, 10.0, "alpha bravo"),
            _abutting(2, 10.0, 20.0, ""),
            _abutting(3, 20.0, 30.0, "charlie"),
        ]
        decisions = own.resolve_ownership(units)
        assert own.stitch(decisions) == "alpha bravo charlie"
        assert own.ownership_summary(decisions)["empty_units"] == 1


class TestAnchoredCut:
    def _pair(self):
        # Ten words a second apart. Unit 1 owns [0, 10), unit 2 owns [10, 20),
        # and each hears five seconds of the other's speech.
        words = [f"w{index:02d}" for index in range(20)]
        left = own.OwnershipUnit(
            unit_id="CALL#u0001",
            turn_start_seconds=0.0,
            turn_end_seconds=10.0,
            context_start_seconds=0.0,
            context_end_seconds=15.0,
            text=" ".join(words[:15]),
        )
        right = own.OwnershipUnit(
            unit_id="CALL#u0002",
            turn_start_seconds=10.0,
            turn_end_seconds=20.0,
            context_start_seconds=5.0,
            context_end_seconds=20.0,
            text=" ".join(words[5:20]),
        )
        return [left, right], words

    def test_the_turn_gets_its_own_words_back(self):
        units, words = self._pair()
        decisions = own.resolve_ownership(units)
        assert decisions[0].delivered_text == " ".join(words[:10])
        assert decisions[1].delivered_text == " ".join(words[10:])
        assert own.stitch(decisions) == " ".join(words)
        assert decisions[0].right_rule == own.RULE_ANCHOR

    def test_the_stitch_is_gapless_wherever_the_anchor_lands(self):
        # Force the anchor away from the true boundary by lying about the turn
        # bounds; the stitch must still cover every word once.
        units, words = self._pair()
        shifted = [
            own.OwnershipUnit(
                unit_id=units[0].unit_id,
                turn_start_seconds=0.0,
                turn_end_seconds=7.0,
                context_start_seconds=0.0,
                context_end_seconds=15.0,
                text=units[0].text,
            ),
            own.OwnershipUnit(
                unit_id=units[1].unit_id,
                turn_start_seconds=7.0,
                turn_end_seconds=20.0,
                context_start_seconds=5.0,
                context_end_seconds=20.0,
                text=units[1].text,
            ),
        ]
        decisions = own.resolve_ownership(shifted)
        assert own.stitch(decisions) == " ".join(words)

    def test_a_disagreeing_overlap_still_anchors_on_the_run_it_has(self):
        words = [f"w{index:02d}" for index in range(20)]
        left_words = list(words[:15])
        left_words[12] = "MISHEARD"
        left = own.OwnershipUnit(
            unit_id="CALL#u0001",
            turn_start_seconds=0.0,
            turn_end_seconds=10.0,
            context_start_seconds=0.0,
            context_end_seconds=15.0,
            text=" ".join(left_words),
        )
        right = own.OwnershipUnit(
            unit_id="CALL#u0002",
            turn_start_seconds=10.0,
            turn_end_seconds=20.0,
            context_start_seconds=5.0,
            context_end_seconds=20.0,
            text=" ".join(words[5:20]),
        )
        decisions = own.resolve_ownership([left, right])
        assert decisions[0].right_rule in (own.RULE_ANCHOR, own.RULE_SHORT_ANCHOR)
        assert own.stitch(decisions) == " ".join(words)

    def test_no_shared_word_falls_back_to_the_proportional_rule(self):
        left = own.OwnershipUnit(
            unit_id="CALL#u0001",
            turn_start_seconds=0.0,
            turn_end_seconds=10.0,
            context_start_seconds=0.0,
            context_end_seconds=15.0,
            text="aa bb cc dd ee ff",
        )
        right = own.OwnershipUnit(
            unit_id="CALL#u0002",
            turn_start_seconds=10.0,
            turn_end_seconds=20.0,
            context_start_seconds=5.0,
            context_end_seconds=20.0,
            text="pp qq rr ss tt uu",
        )
        decisions = own.resolve_ownership([left, right])
        assert decisions[0].right_rule == own.RULE_PROPORTIONAL
        assert own.ownership_summary(decisions)["rules"] == {own.RULE_PROPORTIONAL: 1}


class TestOrderAndRefusals:
    def test_the_two_cuts_of_a_unit_never_cross(self):
        words = [f"w{index:02d}" for index in range(30)]
        units = [
            own.OwnershipUnit(
                unit_id=f"CALL#u{index:04d}",
                turn_start_seconds=float(index * 3),
                turn_end_seconds=float((index + 1) * 3),
                context_start_seconds=max(0.0, index * 3 - 6.0),
                context_end_seconds=min(30.0, (index + 1) * 3 + 6.0),
                text=" ".join(
                    words[max(0, index * 3 - 6) : min(30, (index + 1) * 3 + 6)]
                ),
            )
            for index in range(10)
        ]
        decisions = own.resolve_ownership(units)
        for decision in decisions:
            assert decision.keep_from <= decision.keep_to
            assert 0 <= decision.keep_from <= decision.words_total
            assert decision.keep_to <= decision.words_total

    def test_units_that_do_not_abut_are_refused(self):
        units = [_abutting(1, 0.0, 10.0, "a b"), _abutting(2, 11.0, 20.0, "c d")]
        with pytest.raises(own.OwnershipError, match="do not abut"):
            own.resolve_ownership(units)

    def test_a_unit_whose_context_misses_its_own_turn_is_refused(self):
        bad = own.OwnershipUnit(
            unit_id="CALL#u0001",
            turn_start_seconds=10.0,
            turn_end_seconds=20.0,
            context_start_seconds=12.0,
            context_end_seconds=25.0,
            text="a b",
        )
        with pytest.raises(own.OwnershipError, match="turn's start"):
            own.resolve_ownership([bad])

    def test_an_empty_call_is_refused(self):
        with pytest.raises(own.OwnershipError):
            own.resolve_ownership([])


class TestRecords:
    def test_the_trace_fields_carry_the_delivered_text_and_the_rules(self):
        units = [_abutting(1, 0.0, 10.0, "alpha bravo")]
        (decision,) = own.resolve_ownership(units)
        fields = decision.trace_fields()
        assert fields["obs_delivered_text"] == "alpha bravo"
        assert fields["obs_ownership_protocol"] == own.OWNERSHIP_PROTOCOL
        assert fields["obs_ownership_keep_from"] == 0
        assert fields["obs_ownership_keep_to"] == 2

    def test_the_summary_counts_boundaries_not_units(self):
        units = [
            _abutting(1, 0.0, 10.0, "a b"),
            _abutting(2, 10.0, 20.0, "c d"),
            _abutting(3, 20.0, 30.0, "e f"),
        ]
        summary = own.ownership_summary(own.resolve_ownership(units))
        assert summary["units"] == 3
        assert summary["boundaries"] == 2
        assert summary["words_total"] == 6
        assert summary["words_kept"] == 6
        assert summary["words_dropped"] == 0


class TestHelpers:
    def test_the_ownership_key_ignores_case_and_punctuation(self):
        assert own.ownership_key("Hello,") == own.ownership_key("hello")
        assert own.ownership_key("Don't") == "don't"
        assert own.ownership_key("--") == ""

    def test_common_runs_finds_contiguous_blocks_only(self):
        left = ["a", "b", "c", "d", "e"]
        right = ["x", "b", "c", "d", "y"]
        runs = own.common_runs(left, right, minimum=3)
        assert runs == [(1, 1, 3)]
        assert own.common_runs(left, right, minimum=4) == []

    def test_words_with_offsets_round_trips_the_original_string(self):
        text = "  alpha   bravo\tcharlie "
        entries = own.words_with_offsets(text)
        assert [word for word, _s, _e in entries] == ["alpha", "bravo", "charlie"]
        assert text[entries[0][1] : entries[-1][2]] == "alpha   bravo\tcharlie"
