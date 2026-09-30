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


# ---------------------------------------------------------------------------- --ranker study (synthetic fixture)


def test_ranker_flag_parses_and_routes_outputs():
    a = M.parse_args(["--data-root", "/d"])
    assert a.ranker == "trigram-lexicon" and M.output_dir(a) == Path("/d") / M.ANALYSIS_DIR
    r = M.parse_args(["--data-root", "/d", "--reference-source", "reference"])
    assert M.output_dir(r) == Path("/d") / M.ANALYSIS_DIR / M.REFERENCE_SUBDIR
    s = M.parse_args(["--data-root", "/d", "--ranker", "study", "--check"])
    assert s.ranker == "study" and s.check and M.output_dir(s) == Path("/d") / M.STUDY_DIR
    assert M.STUDY_DIR.endswith("SAEA-SLURP-S2A-RANKER-STUDY-V1")
    with pytest.raises(SystemExit):
        M.parse_args(["--ranker", "study", "--reference-source", "reference"])
    with pytest.raises(SystemExit):
        M.parse_args(["--ranker", "bogus"])
    assert M.GATE_T == pytest.approx(0.7383, abs=1e-4) and round(M.GATE_T * 70 + 0.4999) == 52


def test_span_features_modes_and_windows():
    canon = ["fly", "to", "paris", "now"]
    ctx = M.span_features(canon, 2, 1, "context")
    assert "L1=to" in ctx and "R1=now" in ctx and "R1R2=now_</s>" in ctx
    assert not any(f.startswith(("S=", "w=", "c3=")) for f in ctx)          # context never sees the span
    sp = M.span_features(canon, 2, 1, "span")
    assert "S=paris" in sp and not any(f.startswith("L1=") for f in sp)
    both = M.span_features(canon, 0, 2, "span+context")
    assert "L1=<s>" in both and "L1F=<s>_fly" in both and "ER1=to_paris" in both
    with pytest.raises(M.ReadError):
        M.span_features(canon, 0, 1, "nope")
    assert (1, 1) not in M.free_windows(canon, {1}) and (2, 2) in M.free_windows(canon, {1})
    wins, placed, unplaced = M.training_windows(canon, [("place_name", ("paris",)), ("date", ("monday",))])
    lab = {(i, n): l for i, n, l in wins}
    assert lab[(2, 1)] == "place_name" and lab[(1, 2)] == M.NONE_LABEL and (placed, unplaced) == (1, 1)


def test_aggregate_rank_outcome_and_budget():
    import numpy as np

    canon = ["a", "b", "a", "c"]
    wins = [(0, 1), (1, 1), (2, 1), (3, 1)]
    wmat = np.array([[0.1, 0.0], [0.5, 0.2], [0.9, 0.0], [0.5, 0.4]])
    tab = M.aggregate_windows(canon, wins, wmat)
    ai = tab["index"][("a",)]
    assert tab["starts"][ai] == 0 and tab["mat"][ai, 0] == 0.9     # max over occurrences, earliest start
    assert M.gold_rank(tab, ai, 0) == 1
    assert M.gold_rank(tab, tab["index"][("c",)], 0) == 3         # tie with "b" at 0.5 -> later start ranks after
    out = M.study_outcome(("c",), canon, set(), tab, 0, theta=0.0, k=2)
    assert out == {"outcome": "not_ranked_top_k", "rank": 3}
    assert M.study_outcome(("b",), canon, set(), tab, 0, 0.0, 3)["outcome"] == "hit"
    assert M.study_outcome(("b",), canon, set(), tab, 0, 0.6, 3)["outcome"] == "below_threshold"
    assert M.study_outcome(("a",), canon, set(), tab, 1, 0.0, 3)["outcome"] == "below_threshold"   # score 0
    assert M.study_outcome(("z",), canon, set(), tab, 0, 0.0, 3)["outcome"] == "not_in_transcript"
    assert M.study_outcome(("b",), canon, {1}, tab, 0, 0.0, 3)["outcome"] == "overlaps_draft"
    vals = np.array([0.9, 0.8, 0.8, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    th = M.theta_for_budget(vals, 0.10)
    assert 0.8 < th <= 0.9 and ((vals >= th) & (vals > 0)).mean() == 0.10      # exactly the one call at 0.9
    th2 = M.theta_for_budget(vals, 0.2)                          # a tie at 0.8 cannot be split: both excluded
    assert ((vals >= th2) & (vals > 0)).mean() <= 0.2 and th2 > 0.8
    assert M.theta_for_budget(vals, 0.5) == 0.0                  # the budget admits every positive call
    rows = {"r": {"canon": canon, "covered": set()}}
    pt = M.read_point({"r": tab}, rows, [("r", ("b",), "t0")], ["r"], {"t0": 0, "t1": 1}, 0.45, 3)
    assert pt["hits"] == 1 and pt["false_candidate_calls"] == 2 and pt["false_candidate_nonempty"] == 1
    assert pt["mean_candidates_per_call"] == pytest.approx(3 / 2)
    fused = M.fuse_tables(tab, tab, 1.0)
    assert fused["mat"][ai, 0] == pytest.approx(0.81)


def test_span_type_model_uses_context_on_unseen_values():
    cities = ["paris", "rome", "oslo", "lima", "kyiv", "doha", "baku", "riga"]
    docs = []
    for c in cities:
        canon = ["weather", "in", c, "today"]
        docs.append((canon, M.training_windows(canon, [("place_name", (c,)), ("date", ("today",))])[0]))
    model = M.SpanTypeModel("lr", "context", ["date", "place_name"], C=10.0).fit(docs)
    test = ["weather", "in", "zzyzx", "today"]          # a value no TRAIN lexicon holds
    wins = M.free_windows(test, set())
    tab = M.aggregate_windows(test, wins, model.score_windows([(test, i, n) for i, n in wins]))
    gi = tab["index"][("zzyzx",)]
    assert M.gold_rank(tab, gi, 1) == 1
    assert model.fit_facts["classes"] == 3 and model.score_windows([]).shape == (0, 2)
    nb = M.SpanTypeModel("nb", "span", ["date", "place_name", "absent_type"]).fit(docs)
    assert nb.columns[2] is None and nb.score_windows([(test, 3, 1)])[0, 1] > 0
    with pytest.raises(M.ReadError):
        M.SpanTypeModel("svm", "span", ["date"])


def test_theta_for_hits_diagnostic():
    import numpy as np

    canon = ["x", "y", "z"]
    wins = M.free_windows(canon, set(), 1)
    tab = M.aggregate_windows(canon, wins, np.array([[0.9], [0.4], [0.2]]))
    rows = {"r": {"canon": canon, "covered": set()}}
    targets = [("r", ("x",), "t"), ("r", ("y",), "t"), ("r", ("q",), "t")]
    assert M.theta_for_hits({"r": tab}, rows, targets, {"t": 0}, 3, 2) == pytest.approx(0.4)
    assert M.theta_for_hits({"r": tab}, rows, targets, {"t": 0}, 3, 3) is None      # "q" is not in the transcript
    assert M.theta_for_hits({"r": tab}, rows, targets, {"t": 0}, 1, 2) is None      # "y" ranks 2nd
