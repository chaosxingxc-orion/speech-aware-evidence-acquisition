# N1 re-run: routing metrics on the genuinely-wrong mass

**Date:** 2026-08-17 · **Headline arm:** `SAEA-P2-r1verify` · **Control:** `SAEA-P2-r0bias` · 10 earnings21 calls
**Bundle:** `docs/checks/speech-aware-evidence-acquisition/2026-08-17-n1-rerun-truewrong/` (commits `e045b98`, `0514025`)

## Provenance

Offline archival replay under owner ruling D5. Zero model contact, no attempt directory modified, CPU only, no exposure row required. Reproduce with `run_n1.sh`; full transcript in `n1_run.log`.

**The original N1 measurement is not committed anywhere** — no code, no artifact (verified by repo-wide search and `git log --all`). Its only committed ancestor is the guard-forensics line *"only 55 windows / 23 reachable entity mentions were ever surfaced."* So this is **not** a re-derivation of a lost computation: it reads the **consumed flag decisions themselves** from each arm's `replay-derivation.<call>.json` sidecars — stronger provenance than the original had.

## Two reach notions (and how they reconcile the 0.94%)

A re-listen window is the flagged word run's forced-aligned timing **plus `replay_context_s` 5.0 s + `replay_span_pad_s` 0.3 s each side**, clamped to the 90 s slice. That padding means "the audio contained the mention" and "the mention was what got flagged" are different questions:

- **routing recall** — a gold mention's tokens overlap a window in time. *Did the re-listen audio reach it?*
- **targeting recall** — overlap with the window **core** (window minus the ±5.3 s padding). *Was it the thing actually flagged?*

Targeting recall on the legacy all-wrong denominator is **0.84%** (r1verify) / **0.82%** (r0bias) — i.e. the reported ~0.94%. The original figure measured **targeting**, on the inflated denominator.

Reference-token→time mapping: the scored `earnings21-original` reference declares `ts`/`endTs` but leaves them **empty on all ten calls**, and ConEC's timestamped copy is not index-aligned (6,612 vs 6,602 rows). The two token sequences are therefore aligned with the same frozen-mirror aligner used in T-NDL and timestamps transferred across matched pairs (99.4–99.7% matched; 57–76% directly timed, remainder interpolated between timed neighbours).

## Denominators

| Denominator | r1verify | r0bias |
|---|--:|--:|
| all wrong mentions (legacy) | 2,873 | 2,822 |
| **true-wrong** (FORMAT removed) | **952** | **970** |
| — NUMERIC / CONVENTION / NAME | 282 / 294 / 376 | 286 / 308 / 376 |
| **true-wrong NAME only** | **376** | 376 |
| **true-wrong NAME + 5+ char key** | **236** | 236 |

Note the coordinator's "NAME subgroup (444)" is the *pre-filter* NAME total; within the true-wrong mass NAME is **376** (444 − 68 FORMAT).

## Rung 0 — as-shipped flag

54 timed windows (+2 untimed, LOCALIZE alignment failure), mean 10.41 s, over **6 of 10 calls**.

| denominator | n | routing | targeting | window precision |
|---|--:|--:|--:|--:|
| all wrong (legacy) | 2,873 | 2.44% | **0.84%** | 66.7% |
| true-wrong | 952 | 4.41% | 2.31% | 53.7% |
| true-wrong NAME | 376 | 8.51% | 5.85% | 48.1% |
| true-wrong NAME + 5+ char | 236 | **13.14%** | **9.32%** | 48.1% |

r0bias is identical on the NAME views (8.51% / 13.14%) and within 0.02 pt elsewhere.

Restating the denominator moves the headline from **0.84% → 9.32%** targeting (11×) and **2.44% → 13.14%** routing (5.4×). Window precision roughly halves as the denominator narrows — about half the windows land on something that is not a true-wrong name.

## The counterfactual ladder

| rung | true-wrong (952) | NAME (376) | NAME + 5+ char (236) |
|---|--:|--:|--:|
| 0 · as-shipped | 4.41% | 8.51% | **13.14%** |
| 1 · roster ceiling — no floor, no budget, same 95-term roster | 11.55% | 19.41% | **28.81%** |
| 2 · gold-roster perfect flag @ **matched** 54-window budget | 22.37% | 30.85% | **40.25%** |
| 3 · no-budget — windows for 50% / 90% / 100% | 171 / 469 / 559 | 112 / 264 / 299 | **79 / 175 / 194** |

Rung 1 asks what *any* roster-band flag could reach with the shipped roster, floor and budget removed: a mention is reachable only if its own gold surface form lands in-band (weighted grapheme distance ∈ [0.05, 0.45]) against a roster term. Rung 2 gives an oracle perfect knowledge of where the true-wrong mentions are but the *same* number of windows of the same mean duration, placed by greedy maximum coverage.

**Failure decomposition on NAME + 5+ char (236):** shipped 13.14% → roster ceiling 28.81% (floor + budget cost **15.7 pts**) → perfect roster at same budget 40.25% (roster quality costs a further **11.4 pts**) → 100% needs 194 windows (**3.6× budget**). The shipped flag falls well short even of its own roster ceiling, so floor and budget — not only roster quality — are binding.

## Structural findings

1. **The roster is a participant-NAME roster** (6–15 proper names per call: "Boyd Chumbley", "Aldeyra Therapeutics Inc", "Rajesh Vashist"). The flag family **cannot target numeric mass by construction** — which is exactly why the blanket denominator was the wrong one, and independently corroborates T-NDL's recommendation to scope knowledge supply to names.
2. **4 of 10 calls produced zero windows.** Only 6 calls carried ORG/SUPPLY evidence (19–54 bytes each). Those 4 calls' true-wrong mass is structurally unreachable regardless of flag tuning.
3. **Monopolisation persists.** Windows concentrate on a few terms (`sitimes` 11, `ching` 9, `tribecca` 5), reproducing the forensics' "45% of budget to three terms".
4. **2 windows per arm have null timing** — the LOCALIZE alignment-failure channel. They consumed budget and can reach nothing.

## Verdict

**Does the N1 NO-GO on per-span routing survive?** **Yes, on the blanket view.** Over the full true-wrong mass, routing reaches 4.41% and targeting 2.31%, against a matched-budget oracle ceiling of 22.4%. Even a perfect flag spending the current budget leaves ~78% of genuinely-wrong mentions untouched, and 90% coverage costs 469 windows (8.7× budget). Per-span routing as a general mechanism remains NO-GO.

**Does name-scoped routing deserve a different verdict?** **Yes — it should not inherit the blanket NO-GO.** On NAME + 5-plus-char keys the picture is a bounded engineering gap, not a structural dead end:

- 40.25% is reachable **at the current 54-window budget** with a better flag — 3.1× today's 13.14%;
- 90% coverage costs 175 windows, 3.2× budget, ≈6% of call audio re-listened;
- the gap decomposes into two addressable causes (floor/budget 15.7 pts, roster quality 11.4 pts) rather than an unreachable target;
- and T-NDL independently showed this is the subgroup where knowledge supply has purchase (52.5% pre-published, 54.2% at 5+ char keys against a 0.0% decoy rate).

**Recommendation:** re-scope the N1 gate from "per-span routing" to "name-scoped per-span routing", and set its pass line against the matched-budget oracle (40.25%) rather than against 100%. Retire the 0.94% figure — it conflated targeting with routing on a denominator that was two-thirds writing convention. The MUST-NOT-FLY scale bar should stay bound until a flag demonstrably clears its own roster ceiling (28.81%), which the shipped flag does not.

**Caveats.** n = 10 calls, 54 windows, 6 calls with any window. Reachability is geometric (audio overlap), so it is an *upper bound* on what the guard chain could consume — the forensics' 23-mention figure is the routing∩consumability intersection and is correspondingly smaller. Timestamps are transferred across an alignment and 24–43% are interpolated; mention intervals are therefore approximate to roughly a word. Rung 2's oracle may route to all 10 calls while the shipped flag only reached 6.
