"""Plan v3: the context bounds, on synthetic turns.

No sealed artifact, no audio file and no reference is opened here. v3 moves no
turn, so these tests are about one function -- ``context_bounds`` -- its three
rules, its two clamps, and the invariants ``assert_context`` refuses to write
a plan without.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.analysis import e21_speaker_turn_units as stu


def _unit(index: int, start: float, end: float, **kwargs) -> stu.UnitV2:
    return stu.UnitV2(
        sample_id="CALL",
        unit_index=index,
        start_seconds=start,
        end_seconds=end,
        speaker=kwargs.get("speaker", "speaker_1"),
        speaker_share=1.0,
        speaker_count=1,
        start_cut=kwargs.get("start_cut", stu.CUT_PAUSE),
        end_cut=kwargs.get("end_cut", stu.CUT_PAUSE),
        ends_active=False,
        flags=(),
    )


def _tiling(edges, duration):
    bounds = [0.0, *edges, duration]
    units = [
        _unit(
            index,
            low,
            high,
            start_cut=stu.CUT_CALL_START if index == 1 else stu.CUT_PAUSE,
            end_cut=stu.CUT_CALL_END if high == duration else stu.CUT_PAUSE,
        )
        for index, (low, high) in enumerate(zip(bounds, bounds[1:]), start=1)
    ]
    return units


class TestContextBounds:
    def test_an_interior_turn_gets_the_nominal_margin_on_both_sides(self):
        start, end = stu.context_bounds(100.0, 130.0, 600.0)
        assert (start, end) == (95.0, 135.0)

    def test_a_turn_at_the_call_start_spends_its_whole_margin_on_the_right(self):
        start, end = stu.context_bounds(0.0, 30.0, 600.0)
        assert (start, end) == (0.0, 40.0)

    def test_a_turn_at_the_call_end_spends_its_whole_margin_on_the_left(self):
        start, end = stu.context_bounds(570.0, 600.0, 600.0)
        assert (start, end) == (560.0, 600.0)

    def test_a_short_turn_gets_more_context_not_less(self):
        start, end = stu.context_bounds(100.0, 101.0, 600.0)
        assert (start, end) == (95.0, 106.0)
        assert end - start >= stu.MIN_DELIVERED_CUT_SECONDS

    def test_the_floor_binds_only_when_two_margins_cannot_reach_it(self):
        # With the standard 5 s margin a 1 s turn already delivers 11 s, so the
        # floor is inert; halve the margin and it becomes the binding rule.
        start, end = stu.context_bounds(100.0, 101.0, 600.0, margin=1.0)
        assert end - start == pytest.approx(stu.MIN_DELIVERED_CUT_SECONDS)
        assert (start, end) == (pytest.approx(95.5), pytest.approx(105.5))

    def test_a_long_turn_is_capped_and_a_full_length_one_gets_nothing(self):
        start, end = stu.context_bounds(100.0, 186.0, 600.0)
        assert end - start == pytest.approx(stu.MAX_DELIVERED_CUT_SECONDS)
        assert (start, end) == (pytest.approx(98.0), pytest.approx(188.0))
        assert stu.context_bounds(100.0, 190.0, 600.0) == (100.0, 190.0)

    def test_a_call_shorter_than_the_floor_delivers_the_whole_call(self):
        assert stu.context_bounds(2.0, 5.0, 6.0) == (0.0, 6.0)

    def test_a_non_positive_turn_is_refused(self):
        with pytest.raises(stu.SpeakerTurnUnitError):
            stu.context_bounds(10.0, 10.0, 100.0)


class TestAddContext:
    def test_v3_moves_no_turn(self):
        units = _tiling([30.0, 31.0, 100.0, 160.0], 200.0)
        widened = stu.add_context(units, 200.0)
        assert len(widened) == len(units)
        for before, after in zip(units, widened):
            assert (after.start_seconds, after.end_seconds) == (
                before.start_seconds,
                before.end_seconds,
            )
            assert after.identifier == before.identifier
            assert (after.start_cut, after.end_cut) == (before.start_cut, before.end_cut)
            assert after.speaker == before.speaker

    def test_every_boundary_sits_inside_the_audio_both_units_received(self):
        units = _tiling([30.0, 31.0, 100.0, 160.0], 200.0)
        widened = stu.add_context(units, 200.0)
        for previous, following in zip(widened, widened[1:]):
            low = max(previous.context_start_seconds, following.context_start_seconds)
            high = min(previous.context_end_seconds, following.context_end_seconds)
            assert low <= previous.end_seconds <= high

    def test_context_bounds_need_not_be_ordered_across_units(self):
        # The measured case (call 4320211): a long first turn has no room on
        # its left, spends its whole margin on the right, and swallows the
        # short unit that follows it.
        widened = stu.add_context(_tiling([37.39, 39.05], 100.0), 100.0)
        assert widened[0].context_end_seconds > widened[1].context_end_seconds
        stu.assert_context(widened, 100.0)

    def test_the_as_dict_record_carries_the_six_context_fields(self):
        widened = stu.add_context(_tiling([30.0], 100.0), 100.0)
        document = widened[0].as_dict()
        for key in (
            "context_start_seconds",
            "context_end_seconds",
            "context_left_seconds",
            "context_right_seconds",
            "delivered_cut_seconds",
            "delivered_seconds",
        ):
            assert key in document
        assert document["delivered_seconds"] == pytest.approx(
            document["delivered_cut_seconds"] + stu.TAIL_SILENCE_SECONDS
        )

    def test_a_v1_v2_unit_dict_is_a_strict_subset_of_the_v3_one(self):
        plain = _tiling([30.0], 100.0)[0]
        widened = stu.add_context(_tiling([30.0], 100.0), 100.0)[0]
        base = plain.as_dict()
        derived = widened.as_dict()
        for key, value in base.items():
            if key in ("delivered_seconds",):
                continue  # v3 delivers the context too, and says so
            assert derived[key] == value


class TestAssertContext:
    def _widened(self):
        return list(stu.add_context(_tiling([30.0, 100.0], 160.0), 160.0))

    def test_context_outside_the_call_is_refused(self):
        units = self._widened()
        broken = [
            stu.UnitV3(
                **{
                    **{
                        field: getattr(units[0], field)
                        for field in (
                            "sample_id",
                            "unit_index",
                            "start_seconds",
                            "end_seconds",
                            "speaker",
                            "speaker_share",
                            "speaker_count",
                            "start_cut",
                            "end_cut",
                            "ends_active",
                            "flags",
                            "absorbed_units",
                        )
                    },
                    "context_start_seconds": -1.0,
                    "context_end_seconds": units[0].context_end_seconds,
                }
            ),
            *units[1:],
        ]
        with pytest.raises(stu.SpeakerTurnUnitError, match="before the call"):
            stu.assert_context(broken, 160.0)

    def test_a_delivered_cut_under_the_floor_is_refused(self):
        shrunk = [
            stu.UnitV3(
                sample_id="CALL",
                unit_index=1,
                start_seconds=0.0,
                end_seconds=1.0,
                speaker="speaker_1",
                speaker_share=1.0,
                speaker_count=1,
                start_cut=stu.CUT_CALL_START,
                end_cut=stu.CUT_PAUSE,
                ends_active=False,
                flags=(),
                context_start_seconds=0.0,
                context_end_seconds=2.0,
            )
        ]
        with pytest.raises(stu.SpeakerTurnUnitError, match="minimum"):
            stu.assert_context(shrunk, 160.0)

    def test_a_context_that_does_not_cover_its_own_turn_is_refused(self):
        units = self._widened()
        broken = [
            stu.UnitV3(
                sample_id=units[1].sample_id,
                unit_index=units[1].unit_index,
                start_seconds=units[1].start_seconds,
                end_seconds=units[1].end_seconds,
                speaker=units[1].speaker,
                speaker_share=units[1].speaker_share,
                speaker_count=units[1].speaker_count,
                start_cut=units[1].start_cut,
                end_cut=units[1].end_cut,
                ends_active=units[1].ends_active,
                flags=units[1].flags,
                context_start_seconds=units[1].start_seconds + 1.0,
                context_end_seconds=units[1].context_end_seconds,
            )
        ]
        with pytest.raises(stu.SpeakerTurnUnitError, match="turn's start"):
            stu.assert_context(broken, 160.0)


class TestRulesBlock:
    def test_v3_rules_carry_v2s_unchanged_and_name_the_context_rule(self):
        v2, v3 = stu.rules_block_v2(), stu.rules_block_v3()
        for key, value in v2.items():
            assert v3[key] == value
        assert v3["context_margin_seconds"] == stu.CONTEXT_MARGIN_SECONDS
        assert v3["min_delivered_cut_seconds"] == stu.MIN_DELIVERED_CUT_SECONDS
        assert v3["max_delivered_cut_seconds"] == stu.MAX_UNIT_SECONDS
        assert "saea-obs-context-ownership-v1" in str(v3["text_ownership"])

    def test_the_plan_document_carries_source_plan_only_when_given_one(self):
        common = dict(
            carrier_lock_key="earnings21-original",
            split_identity_hash="0" * 64,
            source_run_id="RUN",
            source_attempt_id="ATTEMPT",
            diarization_run_id="DIAR",
            window_rows_sha256="1" * 64,
            calls=[{"sample_id": "CALL"}],
            corpus={"calls": 1},
        )
        assert "source_plan" not in stu.plan_document(**common)
        derived = stu.plan_document(
            **common, schema=stu.PLAN_SCHEMA_V3, source_plan={"path": "p", "sha256": "2" * 64}
        )
        assert derived["source_plan"]["sha256"] == "2" * 64
        assert derived["schema"] == stu.PLAN_SCHEMA_V3
