"""``reproduction.diarization``: the ``saea-diarization-v1`` OBS artifact reader.

The artifact's per-window block is a DERIVATION of its own segment list, so the
reader re-derives it and refuses any disagreement -- a hand-edited stratum, a
truncated segment list or a window grid that does not tile the call is a load-time
error, never a silently wrong stratum in a verdict table.

Everything here runs on a synthetic artifact. Nothing loads a model, reads corpus
audio or names a real speaker.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.reproduction.diarization import (
    DIARIZATION_SCHEMA,
    DOMINATED,
    MANY_SPEAKERS,
    NO_SPEECH,
    SHARED,
    SINGLE_SPEAKER,
    TWO_SPEAKERS,
    DiarizationError,
    SpeakerSegment,
    build_call_block,
    load_diarization,
    speaker_roster_mapping,
    window_grid,
    window_speakers,
)

WINDOW_SECONDS = 90.0


def _segment(start, end, speaker):
    return SpeakerSegment(start_seconds=start, end_seconds=end, speaker=speaker)


SEGMENTS = (
    # window 1: one speaker holds it outright
    _segment(0.0, 80.0, "speaker_0"),
    # window 2: two speakers, neither dominant, with 10s of crosstalk
    _segment(90.0, 140.0, "speaker_0"),
    _segment(130.0, 180.0, "speaker_1"),
    # window 3 (the short tail): three speakers
    _segment(180.0, 190.0, "speaker_0"),
    _segment(190.0, 200.0, "speaker_1"),
    _segment(200.0, 215.0, "speaker_2"),
)
AUDIO_SECONDS = 215.0


def _artifact(tmp_path, **overrides):
    call = build_call_block(
        sample_id="4320211",
        audio_seconds=AUDIO_SECONDS,
        segments=SEGMENTS,
        window_seconds=WINDOW_SECONDS,
    )
    document = {
        "schema": DIARIZATION_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "run_id": "SAEA-E21-TOOL-DIARIZATION-V1",
        "carrier_lock_key": "earnings21-original",
        "tool": {
            "lock_key": "diar-sortformer-4spk-v2",
            "model_sha256": "0" * 64,
            "runtime": "nemo-speech.cpp",
            "runtime_binary_sha256": "1" * 64,
            "device": "cuda:0",
            "max_speakers": 4,
        },
        "window_seconds": WINDOW_SECONDS,
        "calls": [call],
    }
    document.update(overrides)
    path = tmp_path / "diarization.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path, document


# ---------------------------------------------------------------------------
# The window grid is the OBS loop's own grid.
# ---------------------------------------------------------------------------


def test_the_window_grid_tiles_the_call_with_a_short_tail():
    grid = window_grid(215.0, 90.0)
    assert grid == ((0.0, 90.0), (90.0, 180.0), (180.0, 215.0))


def test_a_call_shorter_than_one_window_is_one_window():
    assert window_grid(45.0, 90.0) == ((0.0, 45.0),)


def test_a_non_positive_duration_refuses():
    with pytest.raises(DiarizationError, match="must be positive"):
        window_grid(0.0, 90.0)


# ---------------------------------------------------------------------------
# Per-window derivation.
# ---------------------------------------------------------------------------


def test_a_single_speaker_window_is_dominated():
    window = window_speakers(
        SEGMENTS, window_id="w1", window_index=1, start_seconds=0.0, end_seconds=90.0
    )
    assert window.speaker_count == 1
    assert window.dominant_speaker == "speaker_0"
    assert window.dominant_share == pytest.approx(1.0)
    assert window.overlap_share == pytest.approx(0.0)
    assert window.count_stratum == SINGLE_SPEAKER
    assert window.dominance_stratum == DOMINATED


def test_a_two_speaker_window_reports_its_crosstalk_and_reads_as_shared():
    window = window_speakers(
        SEGMENTS, window_id="w2", window_index=2, start_seconds=90.0, end_seconds=180.0
    )
    assert window.speaker_count == 2
    # speaker_0 holds 90-140 (50s), speaker_1 holds 130-180 (50s)
    assert window.speaker_seconds == {"speaker_0": pytest.approx(50.0), "speaker_1": pytest.approx(50.0)}
    assert window.dominant_share == pytest.approx(0.5)
    # 130-140 is doubly attributed: 10s of 90s
    assert window.overlap_share == pytest.approx(10.0 / 90.0)
    assert window.count_stratum == TWO_SPEAKERS
    assert window.dominance_stratum == SHARED


def test_a_three_speaker_tail_window():
    window = window_speakers(
        SEGMENTS, window_id="w3", window_index=3, start_seconds=180.0, end_seconds=215.0
    )
    assert window.speaker_count == 3
    assert window.count_stratum == MANY_SPEAKERS
    assert window.dominant_speaker == "speaker_2"


def test_a_silent_window_is_its_own_stratum():
    window = window_speakers(
        (), window_id="w9", window_index=9, start_seconds=0.0, end_seconds=90.0
    )
    assert window.speaker_count == 0
    assert window.dominant_speaker is None
    assert window.count_stratum == NO_SPEECH
    assert window.dominance_stratum == NO_SPEECH


def test_dominance_is_a_share_of_attributed_time_not_of_wall_clock():
    """A window with one speaker for five seconds and silence elsewhere is
    DOMINATED by that speaker -- silence is not a competitor."""

    window = window_speakers(
        (_segment(0.0, 5.0, "speaker_0"),),
        window_id="w",
        window_index=1,
        start_seconds=0.0,
        end_seconds=90.0,
    )
    assert window.dominant_share == pytest.approx(1.0)
    assert window.dominance_stratum == DOMINATED


# ---------------------------------------------------------------------------
# Loading a well-formed artifact.
# ---------------------------------------------------------------------------


def test_a_well_formed_artifact_loads_and_yields_strata(tmp_path):
    path, _document = _artifact(tmp_path)
    artifact = load_diarization(path)
    assert set(artifact.calls) == {"4320211"}
    call = artifact.calls["4320211"]
    assert call.speakers == ("speaker_0", "speaker_1", "speaker_2")
    assert [window.window_id for window in call.windows] == [
        "4320211#w0001",
        "4320211#w0002",
        "4320211#w0003",
    ]
    assert artifact.window_strata("count") == {
        "4320211#w0001": SINGLE_SPEAKER,
        "4320211#w0002": TWO_SPEAKERS,
        "4320211#w0003": MANY_SPEAKERS,
    }
    assert artifact.window_strata("dominance")["4320211#w0002"] == SHARED
    assert artifact.window_strata("both")["4320211#w0001"] == f"{SINGLE_SPEAKER}/{DOMINATED}"


def test_window_ids_can_share_the_paired_analysis_id_space(tmp_path):
    """The diarization windows and the paired-analysis windows must be the SAME
    objects; ``build_call_block`` takes the analysis module's own namer."""

    from speech_aware_evidence_acquisition.analysis.e21_window_pairing import (
        call_of,
        window_id,
    )

    call = build_call_block(
        sample_id="4320211",
        audio_seconds=AUDIO_SECONDS,
        segments=SEGMENTS,
        window_seconds=WINDOW_SECONDS,
        window_id_of=window_id,
    )
    ids = [window["window_id"] for window in call["windows"]]
    assert ids == ["4320211#w0001", "4320211#w0002", "4320211#w0003"]
    assert {call_of(identifier) for identifier in ids} == {"4320211"}


def test_an_unknown_stratum_grain_refuses(tmp_path):
    path, _document = _artifact(tmp_path)
    with pytest.raises(DiarizationError, match="unknown stratum grain"):
        load_diarization(path).window_strata("speaker_name")


# ---------------------------------------------------------------------------
# The artifact is self-checking.
# ---------------------------------------------------------------------------


def _tamper(tmp_path, mutate):
    path, document = _artifact(tmp_path)
    mutate(document)
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_a_hand_edited_dominant_speaker_refuses(tmp_path):
    def mutate(document):
        document["calls"][0]["windows"][0]["dominant_speaker"] = "speaker_3"

    with pytest.raises(DiarizationError, match="claims dominant_speaker"):
        load_diarization(_tamper(tmp_path, mutate))


def test_a_hand_edited_overlap_share_refuses(tmp_path):
    def mutate(document):
        document["calls"][0]["windows"][1]["overlap_share"] = 0.0

    with pytest.raises(DiarizationError, match="claims overlap_share"):
        load_diarization(_tamper(tmp_path, mutate))


def test_a_hand_edited_speaker_count_refuses(tmp_path):
    def mutate(document):
        document["calls"][0]["windows"][1]["speaker_count"] = 1

    with pytest.raises(DiarizationError, match="claims speaker_count"):
        load_diarization(_tamper(tmp_path, mutate))


def test_a_truncated_segment_list_refuses(tmp_path):
    """Dropping segments silently changes every stratum that depended on them;
    the re-derivation catches it because the window rows still claim the old
    facts."""

    def mutate(document):
        document["calls"][0]["segments"] = document["calls"][0]["segments"][:1]

    with pytest.raises(DiarizationError, match="claims"):
        load_diarization(_tamper(tmp_path, mutate))


def test_a_window_grid_that_does_not_tile_the_call_refuses(tmp_path):
    def mutate(document):
        document["calls"][0]["windows"] = document["calls"][0]["windows"][:2]

    with pytest.raises(DiarizationError, match="tile into"):
        load_diarization(_tamper(tmp_path, mutate))


def test_a_shifted_window_boundary_refuses(tmp_path):
    def mutate(document):
        document["calls"][0]["windows"][1]["start_seconds"] = 95.0

    with pytest.raises(DiarizationError, match="fixed 90.0s grid"):
        load_diarization(_tamper(tmp_path, mutate))


def test_out_of_order_segments_refuse(tmp_path):
    def mutate(document):
        document["calls"][0]["segments"].reverse()

    with pytest.raises(DiarizationError, match="not in start order"):
        load_diarization(_tamper(tmp_path, mutate))


def test_a_missing_tool_block_refuses(tmp_path):
    def mutate(document):
        document["tool"].pop("runtime_binary_sha256")

    with pytest.raises(DiarizationError, match="lacks 'runtime_binary_sha256'"):
        load_diarization(_tamper(tmp_path, mutate))


def test_a_wrong_schema_refuses(tmp_path):
    def mutate(document):
        document["schema"] = "saea-diarization-v2"

    with pytest.raises(DiarizationError, match="schema mismatch"):
        load_diarization(_tamper(tmp_path, mutate))


def test_a_repeated_call_refuses(tmp_path):
    def mutate(document):
        document["calls"].append(dict(document["calls"][0]))

    with pytest.raises(DiarizationError, match="repeats call"):
        load_diarization(_tamper(tmp_path, mutate))


# ---------------------------------------------------------------------------
# Naming speakers is the caller's job, under its own row.
# ---------------------------------------------------------------------------


def test_a_roster_mapping_only_names_ids_the_artifact_has(tmp_path):
    path, _document = _artifact(tmp_path)
    artifact = load_diarization(path)
    mapping = speaker_roster_mapping(
        artifact, "4320211", {"speaker_0": "Jane Doe", "speaker_1": "John Roe"}
    )
    assert mapping == {"speaker_0": "Jane Doe", "speaker_1": "John Roe"}
    # speaker_2 was given no candidate and stays anonymous rather than guessed
    assert "speaker_2" not in mapping


def test_naming_an_absent_speaker_refuses(tmp_path):
    path, _document = _artifact(tmp_path)
    artifact = load_diarization(path)
    with pytest.raises(DiarizationError, match="has no speaker"):
        speaker_roster_mapping(artifact, "4320211", {"speaker_9": "Nobody"})


def test_two_ids_cannot_claim_one_roster_name(tmp_path):
    path, _document = _artifact(tmp_path)
    artifact = load_diarization(path)
    with pytest.raises(DiarizationError, match="two speaker ids to one roster name"):
        speaker_roster_mapping(
            artifact, "4320211", {"speaker_0": "Jane Doe", "speaker_1": "Jane Doe"}
        )
