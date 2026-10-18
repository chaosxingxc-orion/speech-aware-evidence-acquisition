"""The statistics-only analyzer of the Solver reasoning diagnostic (owner ruling 330 A): a loop text, an enumeration text and a normal text, and the proof it prints no text."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("solver_reasoning_diag_read", REPO / "scripts" / "analysis" / "solver_reasoning_diag_read.py")
read = importlib.util.module_from_spec(SPEC)
sys.modules["solver_reasoning_diag_read"] = read
SPEC.loader.exec_module(read)

PREFIX = "intent-boundaries::intent-boundary:"
LABELS = ["alarm_set", "alarm_query", "weather_query", "iot_hue_lightup", "iot_hue_lightdim", "music_play", "news_query", "calendar_set"]
EVIDENCE = [PREFIX + label for label in LABELS] + ["slot-cards::slot:date", "slot-cards::slot:time"]


def normal_text() -> str:
    return (
        "The speaker asks about tomorrow. I should decide what the user wants. The request mentions rain and an umbrella, which points to a forecast question. "
        "No other card fits as well as the forecast one. The entities are a date word only. I will answer with the forecast scenario and leave the other slots empty."
    )


def loop_text() -> str:
    block = "Let me double check the forecast card against the request once more before I decide anything at all. "
    return "The speaker asks about tomorrow. " + block * 14 + "I will answer now."


TOPICS = ["clock times and wake ups", "rain, snow and temperature", "lights and dimming", "songs and playlists", "headlines and reporters",
          "meetings and reminders", "alarms that were already set", "questions about what is scheduled"]


def enumeration_text() -> str:
    lines = [f"Next I consider the intent {label}. Its boundary talks about {topic}, so I weigh that against the words I heard and move on."
             for label, topic in zip(LABELS, TOPICS)]
    newline = chr(10)
    return "I go through the supplied cards one at a time." + newline + newline.join(lines) + newline + "None of the others fit better than the weather one, so I conclude."


def test_a_normal_text_is_not_a_loop_and_not_an_enumeration():
    stats = read.analyze_text(normal_text(), evidence_ids=EVIDENCE)
    assert stats["pattern"] == "other"
    assert stats["repeat_count"] <= 1 and stats["repeated_sentence_share"] == 0.0
    assert stats["labels_supplied"] == len(LABELS) and stats["labels_mentioned"] <= 1


def test_a_loop_text_shows_a_repeated_block_an_early_first_repeat_and_a_low_compression_ratio():
    stats = read.analyze_text(loop_text(), evidence_ids=EVIDENCE)
    assert stats["pattern"] == "repetition-loop"
    assert stats["repeat_count"] >= 10 and stats["block_sentences"] == 1
    assert stats["repeated_chars_total"] >= read.LOOP_REPEATED_CHARS
    assert stats["repeated_sentence_share"] > 0.8
    assert stats["first_repeat_char_fraction"] < 0.2 and stats["first_repeat_sentence_index"] == 2
    assert stats["tail_repeated_sentence_share"] >= read.LOOP_TAIL_SHARE
    assert stats["zlib_ratio"] < read.analyze_text(normal_text())["zlib_ratio"]


def test_an_enumeration_text_covers_the_supplied_labels_once_each_in_supply_order():
    stats = read.analyze_text(enumeration_text(), evidence_ids=EVIDENCE)
    assert stats["pattern"] == "enumeration"
    assert stats["labels_mentioned"] == len(LABELS) and stats["label_coverage"] == 1.0
    assert stats["label_mentions_max_single"] == 1
    assert stats["first_mention_order_share"] == 1.0
    assert stats["repeat_count"] <= 1 and stats["repeated_sentence_share"] < 0.2


def test_label_matching_accepts_the_spaced_form_and_refuses_substrings():
    assert read.label_pattern("alarm_set").search("I think alarm set fits")
    assert read.label_pattern("alarm_set").search("ALARM_SET")
    assert not read.label_pattern("alarm_set").search("alarm_settings are different")
    assert not read.label_pattern("news_query").search("breaking_news_query_x")


def test_the_longest_repeated_block_reduces_to_its_primitive_period():
    units = ["a long enough sentence one", "a long enough sentence two"] * 4 + ["a closing sentence that is unique"]
    block = read.longest_repeated_block(units)
    assert block["block_sentences"] == 2 and block["repeat_count"] == 4
    assert block["repeated_chars_total"] == block["block_chars"] * 4
    assert read.longest_repeated_block(["a sentence only once here", "another sentence once here"])["repeat_count"] == 0


def test_short_units_never_count_as_repeats():
    assert read.repeat_flags(["wait.", "wait.", "wait.", "this one is long enough to count", "this one is long enough to count"]) == [False, False, False, False, True]


def test_the_restatement_signal_names_whether_the_answer_differs_from_the_last_restated_label():
    labels = ["weather_query", "alarm_set"]
    restated = ("The request is about weather_query because of the rain word in it. The request is about weather_query because of the rain word in it. "
                "The request is about weather_query because of the rain word in it.")
    changed = read.restatement_signal(restated, labels, "alarm_set")
    assert changed["answer_changed_after_last_restatement"] is True and changed["answer_equals_last_mentioned"] is False
    kept = read.restatement_signal(restated, labels, "weather_query")
    assert kept["answer_changed_after_last_restatement"] is False and kept["answer_equals_last_mentioned"] is True
    none = read.restatement_signal(normal_text(), labels, "weather_query")
    assert none["last_restated_label_exists"] is False and none["answer_changed_after_last_restatement"] is None
    assert read.answer_intent('{"scenario":"iot","action":"hue_lightup","entities":[]}') == "iot_hue_lightup"
    assert read.answer_intent("not json") is None and read.answer_intent(None) is None


def _roster(samples):
    rows = []
    for index, (sample, group) in enumerate(samples):
        rows.append({"sample_id": sample, "group": group, "stratum": {"supplied_bin": "lt40" if index % 2 else "ge40", "gold_empty": bool(index % 3 == 0)},
                     "supplied_evidence_ids": EVIDENCE})
    return {"rows": rows}


def test_the_group_read_summarises_every_group_and_counts_missing_rows(tmp_path):
    reasoning, answers = tmp_path / "reasoning", tmp_path / "answers"
    reasoning.mkdir()
    answers.mkdir()
    samples = [("slurp:train:000001:audio-1", "forced-both"), ("slurp:train:000002:audio-2", "forced-both"), ("slurp:train:000003:audio-3", "natural-both"),
               ("slurp:train:000004:audio-4", "forced-3072-only")]
    (reasoning / "slurp_train_000001_audio-1.txt").write_text(loop_text(), encoding="utf-8")
    (reasoning / "slurp_train_000002_audio-2.txt").write_text(enumeration_text(), encoding="utf-8")
    (reasoning / "slurp_train_000003_audio-3.txt").write_text(normal_text(), encoding="utf-8")
    (answers / "slurp_train_000002_audio-2.txt").write_text('{"scenario":"weather","action":"query","entities":[]}', encoding="utf-8")
    report = read.read_diagnostic(_roster(samples), reasoning, answers)
    assert report["rows_read"] == 3 and report["rows_missing"] == 1
    assert report["by_group"]["forced-both"]["rows"] == 2 and report["by_group"]["forced-both"]["patterns"] == {"repetition-loop": 1, "enumeration": 1}
    assert report["by_group"]["natural-both"]["patterns"] == {"other": 1}
    assert report["by_group"]["forced-6144-only"]["rows"] == 0 and report["by_group"]["forced-3072-only"]["rows"] == 0
    assert report["model_contacts"] == 0 and report["text_printed"] is False


def test_the_analyzer_prints_statistics_only(tmp_path, capsys):
    root = tmp_path / "data" / "diagnostics" / read.RUN_ID
    (root / "reasoning").mkdir(parents=True)
    (root / "answers").mkdir()
    secret = "ZEBRA-QUOKKA-UNIQUE-PHRASE-9931"
    text = f"{secret} is the private thought. " + loop_text()
    (root / "reasoning" / "slurp_train_000001_audio-1.txt").write_text(text, encoding="utf-8")
    roster = tmp_path / "roster.json"
    roster.write_text(json.dumps(_roster([("slurp:train:000001:audio-1", "forced-both")])), encoding="utf-8")
    out = tmp_path / "read.json"
    assert read.main(["--data-root", str(tmp_path / "data"), "--roster", str(roster), "--out", str(out)]) == 0
    printed = capsys.readouterr().out
    for blob in (printed, out.read_text(encoding="utf-8")):
        assert secret not in blob and "double check the forecast card" not in blob and "private thought" not in blob
        json.loads(blob)
    # Every value in a per-row record is a number, a boolean, null, or one of the fixed words.
    row = json.loads(printed)["rows"][0]
    for key, value in row.items():
        assert isinstance(value, (int, float, bool, type(None))) or key in {"sample_id", "group", "arm", "supplied_bin", "pattern", "tokens_approx_basis"}, key


# --------------------------------------------------------------------------------------------------------------------- the 3072 versus 6144 pair


def test_a_6144_text_that_continues_the_3072_text_shares_its_prefix_through_the_close():
    head = normal_text()
    closed = head + " " + read.FORCED_CLOSE_MESSAGE
    longer = head + " " + "Let me double check the forecast card against the request once more before I decide anything at all. " * 8
    pair = read.pair_comparison(closed, longer)
    assert pair["forced_close_3072"] is True and pair["identical_through_close"] is True
    assert pair["prefix_share_of_3072"] >= read.PREFIX_SHARE_IDENTICAL
    assert pair["chars_3072_without_close"] == len(head) and pair["text_beyond_3072_chars"] > 500
    assert pair["beyond_pattern"] == "repetition-loop" and pair["beyond_repeated_sentence_share"] > 0.8
    assert pair["repeat_onset_offset_3072"] is None and pair["repeat_onset_before_3072_close_in_6144"] is False
    assert pair["pattern_3072"] == "other" and pair["pattern_6144"] == "repetition-loop"


def test_a_diverging_pair_and_a_pair_whose_repeat_begins_before_the_3072_close():
    loop = loop_text()
    pair = read.pair_comparison(loop + " " + read.FORCED_CLOSE_MESSAGE, loop + " " + loop)
    assert pair["identical_through_close"] is True and pair["repeat_onset_same_in_both"] is True
    assert pair["repeat_onset_before_3072_close_in_6144"] is True
    other = read.pair_comparison(normal_text(), "A completely different opening, then " + normal_text())
    assert other["identical_through_close"] is False and other["forced_close_3072"] is False and other["prefix_share_of_3072"] < 0.2


def test_the_read_adds_the_forced_both_6144_group_and_the_pair_summary_without_printing_text(tmp_path):
    reasoning, answers = tmp_path / "reasoning", tmp_path / "answers"
    reasoning.mkdir()
    answers.mkdir()
    roster = _roster([("slurp:train:000001:audio-1", "forced-both"), ("slurp:train:000002:audio-2", "forced-both"), ("slurp:train:000003:audio-3", "natural-both")])
    roster["raised_arm_reissue"] = True
    for entry in roster["rows"][:2]:
        entry["raised_arm_request"] = {}
    (reasoning / "slurp_train_000001_audio-1.txt").write_text(normal_text() + " " + read.FORCED_CLOSE_MESSAGE, encoding="utf-8")
    (reasoning / "slurp_train_000001_audio-1.b6144.txt").write_text(normal_text() + " " + loop_text(), encoding="utf-8")
    (reasoning / "slurp_train_000002_audio-2.txt").write_text(enumeration_text(), encoding="utf-8")
    report = read.read_diagnostic(roster, reasoning, answers)
    assert report["by_group"]["forced-both@6144"]["rows"] == 1 and report["by_group"]["forced-both"]["rows"] == 2
    assert report["pair_summary"]["pairs"] == 1 and report["pair_summary"]["identical_through_close"] == {"True": 1}
    assert report["rows_missing"] == 2                         # the 6144 file of row 2 and the 3072 file of row 3; a natural row never has a raised file
    assert {r["arm"] for r in report["rows"]} == {"budget-3072", "solver-6144"}
    blob = json.dumps(report)
    assert "double check the forecast card" not in blob and "umbrella" not in blob
