"""Synthetic tests for the S2a.1 recall-ceiling driver (pure parts only; no data, no gold, no model)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_PATH = REPO_ROOT / "scripts" / "analysis" / "slurp_s2a1_recall_ceiling.py"


def _load():
    name = "slurp_s2a1_recall_ceiling_under_test"
    spec = importlib.util.spec_from_file_location(name, _PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = _load()


def lexicon():
    return M.Lexicon({"place_name": ["paris", "london", "new york"], "date": ["monday", "tomorrow"],
                      "empty_type": [""]})


def test_utterance_identity_spans_recordings():
    a = "slurp:train:000123:audio-1490-headset"
    b = "slurp:train:000123:audio-1490-farfield"
    assert M.utterance_of(a) == M.utterance_of(b) == "train:000123"
    assert M.split_of(a) == "train"
    with pytest.raises(M.ReadError):
        M.utterance_of("not-a-slurp-id")


def test_jaccard_and_exact_value_scores_one():
    lex = lexicon()
    assert lex.score("place_name", "paris") == 1.0
    assert 0.0 < lex.score("place_name", "pariss") < 1.0
    assert lex.score("unknown_type", "paris") == 0.0
    assert M.jaccard(frozenset(), frozenset({"a"})) == 0.0


def test_prime_matches_pure_score():
    pure, primed = lexicon(), lexicon()
    spans = ["paris", "to paris", "new", "new york city", "monday", "zzz"]
    primed.prime(spans)
    for t in ("place_name", "date", "empty_type"):
        for s in spans:
            assert primed.score(t, s) == pytest.approx(pure.score(t, s), abs=1e-12)


def test_covered_positions_and_candidate_spans():
    canon = ["book", "a", "table", "in", "paris", "on", "monday"]
    covered = M.covered_positions(canon, [["monday"], ["not", "there"]])
    assert covered == {6}
    spans = M.candidate_spans(canon, covered, max_tokens=2)
    assert all(6 not in range(i, i + len(s)) for i, s in spans)
    assert (4, ("paris",)) in spans and (3, ("in", "paris")) in spans
    assert all(len(s) <= 2 for _i, s in spans)
    # identical span strings are kept once, at their earliest start
    spans2 = M.candidate_spans(["a", "b", "a"], set(), 1)
    assert spans2 == [(0, ("a",)), (1, ("b",))]


def test_propose_caps_ranks_and_abstains():
    lex = lexicon()
    canon = ["fly", "from", "london", "to", "paris", "monday"]
    res = M.propose(canon, set(), lex, "place_name", theta=0.0, k=3)
    assert len(res) <= 3 and res[0] in {("london",), ("paris",)}
    assert res[:2] == [("london",), ("paris",)]          # tie at 1.0 -> earlier start first
    assert M.propose(canon, set(), lex, "place_name", theta=1.01) == []   # abstain: nothing padded
    covered = M.covered_positions(canon, [["london"]])
    assert ("london",) not in M.propose(canon, covered, lex, "place_name", theta=0.0)


def test_classify_every_outcome():
    lex = lexicon()
    canon = ["fly", "to", "paris", "on", "monday", "a", "b", "c", "d", "e", "f"]
    assert M.classify(("paris",), canon, set(), lex, "place_name", 0.0)["outcome"] == "hit"
    assert M.classify(("rome",), canon, set(), lex, "place_name", 0.0)["outcome"] == "not_in_transcript"
    assert M.classify((), canon, set(), lex, "place_name", 0.0)["outcome"] == "not_in_transcript"
    long_gold = ("a", "b", "c", "d", "e", "f")
    assert M.classify(long_gold, canon, set(), lex, "place_name", 0.0)["outcome"] == "too_long"
    assert M.classify(("paris",), canon, {2}, lex, "place_name", 0.0)["outcome"] == "overlaps_draft"
    assert M.classify(("paris",), canon, set(), lex, "place_name", 1.01)["outcome"] == "below_threshold"
    # a low-scoring gold behind three better spans is not ranked into the top 3
    canon2 = ["london", "paris", "new", "york", "qqq"]
    lex2 = M.Lexicon({"place_name": ["london", "paris", "new york", "york", "new"]})
    out = M.classify(("qqq",), canon2, set(), M.Lexicon({"place_name": ["london", "paris", "new york", "qqqx"]}),
                     "place_name", 0.0)
    assert out["outcome"] == "not_ranked_top_k" and out["rank"] > 3
    assert M.classify(("paris",), canon2, set(), lex2, "place_name", 0.0, k=1)["outcome"] == "not_ranked_top_k"


def test_pick_theta_ties_go_low_and_wilson():
    grid = [{"theta": 0.0, "youden_j": 0.2}, {"theta": 0.05, "youden_j": 0.3}, {"theta": 0.1, "youden_j": 0.3}]
    assert M.pick_theta(grid)["theta"] == 0.05
    lo, hi = M.wilson(27, 80)
    assert lo == pytest.approx(0.244, abs=0.002) and hi == pytest.approx(0.446, abs=0.002)
    assert M.wilson(0, 0) == [None, None]


def test_verdict_arithmetic():
    v = M.verdict(0.5, [0.4, 0.6])
    assert v["c_ceiling_at_conv_uptake"] == pytest.approx(0.5 * 32 / 70, abs=1e-4)
    assert v["reading_a_reachable_at_conv_uptake"] is False
    assert v["reading_a_reachable_at_perfect_uptake"] is True
    assert v["T_needed_at_conv_uptake_for_0_33"] == pytest.approx(0.33 / (32 / 70), abs=1e-4)
    assert M.verdict(0.8, [0.7, 0.9])["reading_a_reachable_at_conv_uptake"] is True


def test_perfect_asr_source_split_and_reference_rows():
    whisper = ["fly", "to", "pari", "on", "monday"]
    ref = ["fly", "to", "paris", "on", "monday", "at", "a", "b", "c", "d", "e", "f"]
    entries = [("date", ("monday",), whisper, ref),                         # in both -> in_whisper
               ("place_name", ("paris",), whisper, ref),                    # (i) ASR miss
               ("place_name", ("a", "b", "c", "d", "e", "f"), whisper, ref),   # reference only, > 5 tokens
               ("place_name", ("rome",), whisper, ref),                     # (ii) never spoken verbatim
               ("date", (), whisper, ref),                                  # empty gold -> neither
               ("date", ("mon", "day"), whisper, ref)]                      # (ii), but a spacing difference
    out = M.source_split(entries)
    assert out["counts"] == {"in_whisper": 1, "in_reference": 1, "in_reference_too_long": 1, "in_neither": 3}
    assert out["in_neither_contained_ignoring_spaces"] == 1
    assert out["reference_contained_within_max_tokens"] == 2
    by = {t["type"]: t for t in out["by_type"]}
    assert by["place_name"]["items"] == 3 and by["place_name"]["in_reference"] == 1
    assert by["date"]["in_whisper"] == 1 and by["date"]["in_neither"] == 2
    rows = M.reference_transcripts({"s1": "Fly to Paris"}, ["s1"], lambda x: x.lower().split())
    assert rows["s1"]["status"] == "ok" and rows["s1"]["canon"] == ["fly", "to", "paris"]
    with pytest.raises(M.ReadError):
        M.reference_transcripts({}, ["s1"], str.split)
    b = M.items_of_80(0.95)
    assert b["items_of_80"] == pytest.approx(80 * 0.95 * 32 / 70, abs=0.01)
    assert b["reaches_27_of_80"] is True and b["T_bar_0_738"] is True
    assert M.items_of_80(0.4714)["at_or_below_18_of_80"] is True


def test_verdict_perfect_ranker_bound():
    v = M.verdict(0.1, [0.05, 0.2], 0.47)
    assert v["c_ceiling_perfect_ranker_at_conv_uptake"] == pytest.approx(0.47 * 32 / 70, abs=1e-4)
    assert v["reading_a_reachable_perfect_ranker_at_conv_uptake"] is False
    assert "T_perfect_ranker" not in M.verdict(0.1, [0.05, 0.2])
