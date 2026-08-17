"""N1 re-run stage 3: routing recall/precision + the counterfactual ladder.

OFFLINE, MODEL-FREE (owner ruling D5 archival replay). Reads only already-consumed
run artifacts and gold layers; opens no model session, writes nothing outside its
own outputs.

WHAT A FLAG IS (frozen, committed): `core.flag_sources.roster_band_flags` --
a weighted grapheme edit distance between each pass-1 draft word (and adjacent
2-word window) and the call's candidate roster terms, kept when the distance
lands in the band [0.05, 0.45], scored `band_centrality(distance) * rarity`,
floored at `replay_flag_min_score` and truncated to `replay_max_spans_per_slice`
per slice. No logprob or confidence is consulted (`replay_loop` requests logprobs
only for request-shape stability across arms; r1verify ran flag_source
"roster-band").

WHAT A RE-LISTEN WINDOW IS: the flagged word run's forced-aligned timing plus
`replay_context_s` (5.0 s) either side plus `replay_span_pad_s` (0.3 s), clamped
to the 90 s slice -- persisted per window as absolute whole-call
`replay_window_start_seconds`/`_end_seconds`.

REACHED: a gold entity mention is reached iff any of its reference tokens' time
interval overlaps any flagged window. Reference-token times come from
`n1_timemap.py`.

THE LADDER
  rung 0  as-shipped        the 56 windows the consumed run actually cut.
  rung 1  roster ceiling    no floor, no budget, SAME participant roster: a
                            mention is reachable only if its own gold surface
                            form lands in-band against some roster term. This
                            bounds every floor/budget relaxation from above.
  rung 2  gold-roster perfect flag @ MATCHED budget: an oracle that knows where
                            the true-wrong mentions are, spending the same NUMBER
                            of windows of the same mean duration, placed by greedy
                            maximum coverage. Isolates "bad flag" from "small budget".
  rung 3  no-budget physical ceiling: unlimited windows. Recall reaches 1.0 by
                            construction, so the informative quantity is the COST --
                            windows and audio fraction needed for 50/90/100%.

PROVENANCE: the original N1 measurement is not committed anywhere -- no code, no
artifact (verified by repo-wide search and `git log --all`). Its only committed
ancestor is the guard-forensics statement "only 55 windows / 23 reachable entity
mentions were ever surfaced" (r0bias). The flag decisions used here are therefore
NOT a re-derivation of a lost computation but the CONSUMED decisions themselves,
read from each arm's `replay-derivation.<call>.json` sidecars -- a stronger
provenance than the original had.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

TNDL = Path(os.environ["TNDL"])
sys.path.insert(0, str(TNDL))

from speech_aware_evidence_acquisition.core.flag_sources import (  # noqa: E402
    BAND_HIGH, BAND_LOW, _decompose_candidate_words, weighted_grapheme_distance,
)
from speech_aware_evidence_acquisition.core.retrieval import normalize_term  # noqa: E402

CALLS = ["4330115", "4365024", "4365948", "4366429", "4366522",
         "4384964", "4385072", "4387383", "4389907", "4397829"]


# ---------------------------------------------------------------- reachability

def load_windows(data, arm, attempt):
    """Consumed re-listen windows per call, as absolute (start, end) seconds.

    A window whose timing is null was cut with no usable forced-aligned span (the
    LOCALIZE alignment-failure channel the guard forensics names as its largest
    loss). It occupied a budget slot but covers no locatable audio, so it cannot
    reach any mention; it is dropped from the reachability geometry and counted
    separately so the budget arithmetic still adds up.
    """
    base = Path(data) / "runs" / arm / attempt
    per_call, untimed = {}, 0
    for call in CALLS:
        path = base / f"{arm}.replay-derivation.{call}.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        kept = []
        for w in doc["replay_windows"]:
            ws, we = w["replay_window_start_seconds"], w["replay_window_end_seconds"]
            if ws is None or we is None:
                untimed += 1
                continue
            kept.append((ws, we))
        per_call[call] = kept
    return per_call, untimed


def mention_interval(times, token_indices):
    spans = [times[i] for i in token_indices if i < len(times)]
    if not spans:
        return None
    return min(s for s, _e in spans), max(e for _s, e in spans)


def reached(interval, windows):
    if interval is None:
        return False
    lo, hi = interval
    return any(lo < we and ws < hi for ws, we in windows)


# ---------------------------------------------------------------- rung 1

def roster_reachable(gold_text, roster_terms):
    """Could ANY roster-band flag ever fire for this mention's gold form?

    Uses the frozen distance and band from `core.flag_sources`: a draft word can
    only be flagged toward a candidate when their weighted grapheme distance lands
    inside [0.05, 0.45]. If the mention's own correct surface form is not in-band
    against any roster term, no floor change and no budget change can surface it.
    """
    forms = [normalize_term(w) for w in gold_text.split()]
    forms = [f for f in forms if f]
    if not forms:
        return False
    bigrams = [f"{a} {b}" for a, b in zip(forms, forms[1:])]
    targets = set()
    for term in roster_terms:
        words = _decompose_candidate_words(term)
        targets.update(words)
        targets.update(f"{a} {b}" for a, b in zip(words, words[1:]))
    for probe in forms + bigrams:
        for target in targets:
            distance = weighted_grapheme_distance(probe, target)
            if BAND_LOW <= distance <= BAND_HIGH:
                return True
    return False


# ---------------------------------------------------------------- rungs 2/3

def greedy_cover(intervals, duration, budget=None):
    """Greedy maximum coverage: place windows of length ``duration`` to reach as
    many mention intervals as possible. Returns the reach curve (cumulative
    mentions reached after each window)."""
    remaining = list(range(len(intervals)))
    anchors = sorted({round(lo, 2) for lo, _hi in intervals if lo is not None})
    curve = []
    covered = set()
    while remaining and (budget is None or len(curve) < budget):
        best, best_hits = None, set()
        for anchor in anchors:
            start = max(0.0, anchor - 0.5)
            end = start + duration
            hits = {i for i in remaining
                    if intervals[i] is not None
                    and intervals[i][0] < end and start < intervals[i][1]}
            if len(hits) > len(best_hits):
                best, best_hits = (start, end), hits
        if best is None or not best_hits:
            break
        covered |= best_hits
        remaining = [i for i in remaining if i not in best_hits]
        curve.append(len(covered))
    return curve


# ---------------------------------------------------------------- metrics

CONTEXT_S = 5.3  # replay_context_s 5.0 + replay_span_pad_s 0.3


def core_of(ws, we):
    """The flagged span inside a window.

    A window is the flagged run's own timing padded by ``replay_context_s`` +
    ``replay_span_pad_s`` on each side, so stripping that padding recovers the
    flagged run. Most windows are clamped to the slice and shorter than twice the
    padding, in which case the flagged run is taken as the window midpoint.
    Reported alongside whole-window reach because the two answer different
    questions: whole-window = did the re-listen AUDIO contain the mention
    (routing); core = was the mention the thing actually flagged (targeting).
    """
    lo, hi = ws + CONTEXT_S, we - CONTEXT_S
    if hi <= lo:
        mid = (ws + we) / 2.0
        return mid - 0.5, mid + 0.5
    return lo, hi


def evaluate(rows, times_by_call, windows_by_call, label):
    reach = 0
    core_reach = 0
    per_window_hits = Counter()
    for row in rows:
        call = row["sample_id"]
        interval = mention_interval(times_by_call[call], row["token_indices"])
        wins = windows_by_call[call]
        hit = False
        core_hit = False
        for index, (ws, we) in enumerate(wins):
            if interval and interval[0] < we and ws < interval[1]:
                per_window_hits[(call, index)] += 1
                hit = True
                clo, chi = core_of(ws, we)
                if interval[0] < chi and clo < interval[1]:
                    core_hit = True
        reach += int(hit)
        core_reach += int(core_hit)
    total_windows = sum(len(w) for w in windows_by_call.values())
    productive = len(per_window_hits)
    return {
        "denominator": label,
        "mentions": len(rows),
        "reached": reach,
        "recall": reach / len(rows) if rows else 0.0,
        "core_reached": core_reach,
        "core_recall": core_reach / len(rows) if rows else 0.0,
        "windows": total_windows,
        "productive_windows": productive,
        "window_precision": productive / total_windows if total_windows else 0.0,
        "mentions_per_window": reach / total_windows if total_windows else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--truewrong", required=True, type=Path)
    parser.add_argument("--allwrong", required=True, type=Path,
                        help="the full wrong-mention inventory (legacy denominator)")
    parser.add_argument("--timemap", required=True, type=Path)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    data = os.environ["SPEECHRL_DATA_DIR"]
    times = {k: [tuple(t) for t in v]
             for k, v in json.loads(args.timemap.read_text(encoding="utf-8")).items()}
    windows, untimed = load_windows(data, args.arm, args.attempt)
    truewrong = [json.loads(l) for l in
                 args.truewrong.read_text(encoding="utf-8").splitlines() if l.strip()]
    allwrong = [json.loads(l) for l in
                args.allwrong.read_text(encoding="utf-8").splitlines() if l.strip()]

    total_windows = sum(len(w) for w in windows.values())
    durations = [we - ws for w in windows.values() for ws, we in w]
    mean_duration = sum(durations) / len(durations)
    print(f"=== {args.arm}: {total_windows} timed re-listen windows "
          f"(+{untimed} untimed, LOCALIZE alignment failure), mean {mean_duration:.2f}s, over "
          f"{sum(1 for w in windows.values() if w)} of {len(CALLS)} calls")

    views = [
        ("(legacy) all wrong mentions", allwrong),
        ("true-wrong (FORMAT removed)", truewrong),
        ("true-wrong NAME only", [r for r in truewrong if r["group"] == "NAME"]),
        ("true-wrong NAME + 5+ char key",
         [r for r in truewrong if r["group"] == "NAME" and r["key_len_bucket"] == "len5plus"]),
    ]

    report = {"arm": args.arm, "schema": "saea-n1-rerun-v1",
              "windows": total_windows, "untimed_windows": untimed, "mean_window_seconds": mean_duration,
              "calls_with_windows": sum(1 for w in windows.values() if w),
              "rung0_as_shipped": [], "rung1_roster_ceiling": {},
              "rung2_matched_budget_oracle": {}, "rung3_no_budget": {}}

    print(f"\n--- RUNG 0: as-shipped flag ({total_windows} windows) ---")
    print(f"{'denominator':34}{'n':>6}{'reached':>9}{'recall':>9}"
          f"{'coreR':>8}{'prodW':>7}{'winPrec':>9}")
    for label, rows in views:
        m = evaluate(rows, times, windows, label)
        report["rung0_as_shipped"].append(m)
        print(f"{label:34}{m['mentions']:6d}{m['reached']:9d}"
              f"{100*m['recall']:8.2f}%{100*m['core_recall']:7.2f}%"
              f"{m['productive_windows']:7d}{100*m['window_precision']:8.1f}%")

    # ---- rung 1: roster ceiling
    pack_dir = Path(data) / "derived/evidence-candidates/p1-metadata-v2"
    rosters = {c: [t for t in (pack_dir / f"{c}.candidates.txt").read_text(encoding="utf-8").splitlines() if t.strip()]
               for c in CALLS if (pack_dir / f"{c}.candidates.txt").exists()}
    gold = {}
    for line in args.allwrong.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            gold[(r["sample_id"], r["entity_id"])] = r["ref_text"]
    print(f"\n--- RUNG 1: roster ceiling (no floor, no budget, "
          f"shipped participant roster: {sum(len(v) for v in rosters.values())} terms) ---")
    for label, rows in views[1:]:
        n = sum(1 for r in rows
                if roster_reachable(gold.get((r["sample_id"], r["entity_id"]), ""),
                                    rosters.get(r["sample_id"], [])))
        report["rung1_roster_ceiling"][label] = {"mentions": len(rows), "reachable": n,
                                                 "recall": n / len(rows) if rows else 0.0}
        print(f"{label:34}{len(rows):6d}{n:9d}{100*n/max(1,len(rows)):8.2f}%")

    # ---- rungs 2 and 3
    print(f"\n--- RUNG 2/3: oracle window placement (window = {mean_duration:.1f}s) ---")
    for label, rows in views[1:]:
        by_call = defaultdict(list)
        for r in rows:
            by_call[r["sample_id"]].append(
                mention_interval(times[r["sample_id"]], r["token_indices"]))
        # rung 3 first: unlimited budget per call
        curves = {c: greedy_cover(v, mean_duration) for c, v in by_call.items()}
        full_cost = sum(len(c) for c in curves.values())
        # rung 2: matched global budget, allocated proportionally to mention mass
        total = len(rows)
        budget_curve = []
        for c, curve in curves.items():
            share = max(1, round(total_windows * len(by_call[c]) / total)) if total else 0
            budget_curve.append(curve[min(share, len(curve)) - 1] if curve and share else 0)
        matched = sum(budget_curve)
        report["rung2_matched_budget_oracle"][label] = {
            "mentions": total, "reached": matched,
            "recall": matched / total if total else 0.0, "windows": total_windows}
        # cost curve for rung 3
        def windows_for(frac):
            need = 0
            for c, curve in curves.items():
                target = frac * len(by_call[c])
                k = next((i + 1 for i, v in enumerate(curve) if v >= target), len(curve))
                need += k
            return need
        report["rung3_no_budget"][label] = {
            "mentions": total, "windows_for_50pct": windows_for(0.5),
            "windows_for_90pct": windows_for(0.9), "windows_for_100pct": full_cost,
            "audio_fraction_at_100pct": full_cost * mean_duration / sum(
                (times[c][-1][1] if times[c] else 0) for c in by_call)}
        print(f"{label:34} matched-budget oracle recall="
              f"{100*matched/max(1,total):6.2f}% ({matched}/{total}); "
              f"windows for 50%/90%/100% = {windows_for(0.5)}/{windows_for(0.9)}/{full_cost}")

    args.out.write_text(json.dumps(report, indent=1, sort_keys=True), encoding="utf-8")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
