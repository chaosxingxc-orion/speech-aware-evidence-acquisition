# Audio2Tool tiers-3/4/6/7 official population, v1 — verdict

One run flown 2026-09-04 on study commit `6c13fb6d`, profile `baseline-reproduction`, one cell.

| Run id | Cell | Attempt | Rows | Manifest SHA-256 |
|---|---|---|---:|---|
| `SAEA-A2T-TIER3467-OFFICIAL-POPULATION-V1` | `T3467-official-pop-2000` | `attempt-20260904T211040Z-t3467officialpop2000` | 2,000 | `1f43aab3520a0e4df0aa0b11693f518fda81b52e936e510f51c00713af016d58` |

Preregistration: `docs/readiness/2026-09-04-a2t-tier3467-official-population-v1-preregistration.md`.
Full numbers:
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-tier3467-official-population-v1/result-summary.json`
(SHA-256 `b2f5dd5916206823e189baacd69706444593ceb3e96eb4e8278de7bc94b9807e`).
Paper-facing scorer: `a2t-toolcall-official` — the pinned release's own `metrics.py`, git blob
`d98277bcf69795c9a0ae54e538c170abfd8c51ca`, commit `b9d5383ca30945fbafb965a04bea40117e1e8a82`.

## Verdict: all four tiers FAIL on the natural mixture, and all four would be ALIGNED on an equal-domain one.

| tier | ours | CI90 | paper | delta | ALIGNED needs | outcome |
|---|---:|---|---:|---:|---:|---|
| tier3_multi_intent | **65.00** | [61.42, 68.42] | 74.7 | −9.70 | ≥ 71.7 | **FAIL** |
| tier4_implicit | **28.20** | [25.01, 31.62] | 33.4 | −5.20 | ≥ 30.4 | **FAIL** |
| tier6_correction | **75.80** | [72.52, 78.81] | 81.5 | −5.70 | ≥ 78.5 | **FAIL** |
| tier7_multiturn | **49.40** | [45.74, 53.07] | 54.6 | −5.20 | ≥ 51.6 | **FAIL** |

n = 500 per tier, official scorer, one contact per row, 1,992 of 2,000 rows parsed (99.60 %).
**Not one of the four is CONSISTENT-WITHIN-NOISE:** the published value sits outside every CI90,
including tier 7's, where 54.6 misses the interval's upper edge of 53.07 by 1.5 points. That is
exactly what n = 500 was bought for — at n = 50 all four of these tiers sat *inside* the owner's
3-point band and none of them could be believed.

**The eight-tier table is now complete at one resolution**, and it reads: one tier ALIGNED
(tier 8, 46.80 against 41.7) and seven FAIL.

### The floor rule

| tier | ours | Qwen-2.5-Omni-7B | delta | weakest published SpeechLM | delta |
|---|---:|---:|---:|---:|---:|
| tier3_multi_intent | 65.00 | 50.2 | +14.80 | 40.6 | +24.40 |
| tier4_implicit | 28.20 | 22.4 | +5.80 | 7.9 | +20.30 |
| tier6_correction | 75.80 | 68.3 | +7.50 | 44.6 | +31.20 |
| tier7_multiturn | 49.40 | 48.2 | **+1.20** | 34.5 | +14.90 |

**No tier is below a degraded model's published number.** Tier 7 clears Qwen-2.5-Omni-7B by only
1.20 pp, which is inside its own sampling error, so it is the row to watch; the other three clear
by 5.8–14.8.

## 1. Exact match and parameter F1, beside the paper's own columns

| tier | our EM | CI90 | paper EM | delta | our param F1 macro | micro | v2 slot F1 | paper Slot F1 |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| tier3_multi_intent | 19.40 | [16.66, 22.47] | 28.6 | −9.20 | 33.85 | 27.27 | 18.24 | 35.0 |
| tier4_implicit | 6.40 | [4.82, 8.45] | 11.3 | −4.90 | 14.69 | 6.55 | 5.39 | 23.4 |
| tier6_correction | **24.00** | [21.00, 27.28] | 24.8 | **−0.80** | 38.41 | 31.58 | 27.92 | 32.4 |
| tier7_multiturn | 10.40 | [8.36, 12.86] | 16.3 | −5.90 | 17.83 | 9.80 | 8.60 | 26.8 |

Unlike tiers 2 and 8, where our exact match beat the published one by 15.6 and 10.0 points, all
four tiers here are short — but tier 6 is short by **0.80 points**, which is well inside noise, and
its parameter F1 (38.41 macro) is 6.0 points *above* the published Slot F1. The published EM
columns are reachable on this runtime; they are not on tier 1, where the gap was 82 points.

The official parameter F1 is a macro average of per-sample key precision/recall/F1 while the paper's
"Slot F1" column is defined in neither the paper nor the released code, so the two are tabled side
by side rather than differenced; the same caution the earlier verdicts recorded applies. The exact
match comparison has no such ambiguity — it is the released `metrics.py` computing the same quantity
on both sides.

## 2. By domain — and this decides all four failures

| tier | domain | n | tool accuracy | CI90 | exact match |
|---|---|---:|---:|---|---:|
| tier3_multi_intent | `smart_car` | 41 | **82.93** | [71.31, 90.47] | 60.98 |
| | `wearables` | 91 | **79.12** | [71.32, 85.24] | 39.56 |
| | `smart_home` | 368 | **59.51** | [55.25, 63.64] | 9.78 |
| | natural mixture | 500 | 65.00 | [61.42, 68.42] | 19.40 |
| | **equal-domain** | 500 | **73.85** | — | — |
| tier4_implicit | `wearables` | 90 | **55.56** | [46.90, 63.88] | 18.89 |
| | `smart_car` | 35 | **28.57** | [17.91, 42.31] | 11.43 |
| | `smart_home` | 375 | **21.60** | [18.31, 25.29] | 2.93 |
| | natural mixture | 500 | 28.20 | [25.01, 31.62] | 6.40 |
| | **equal-domain** | 500 | **35.24** | — | — |
| tier6_correction | `wearables` | 91 | **93.41** | [87.75, 96.55] | 42.86 |
| | `smart_car` | 41 | **87.80** | [76.99, 93.94] | 63.41 |
| | `smart_home` | 368 | **70.11** | [66.05, 73.88] | 14.95 |
| | natural mixture | 500 | 75.80 | [72.52, 78.81] | 24.00 |
| | **equal-domain** | 500 | **83.77** | — | — |
| tier7_multiturn | `wearables` | 84 | **77.38** | [69.09, 83.97] | 34.52 |
| | `smart_car` | 36 | **55.56** | [42.02, 68.31] | 30.56 |
| | `smart_home` | 380 | **42.63** | [38.53, 46.84] | 3.16 |
| | natural mixture | 500 | 49.40 | [45.74, 53.07] | 10.40 |
| | **equal-domain** | 500 | **58.52** | — | — |

**Every one of the four failures is a `smart_home` failure, and the equal-domain column says so
without ambiguity:**

| tier | equal-domain | paper | delta | would be |
|---|---:|---:|---:|---|
| tier3_multi_intent | 73.85 | 74.7 | −0.85 | ALIGNED |
| tier4_implicit | 35.24 | 33.4 | **+1.84** | ALIGNED (above the paper) |
| tier6_correction | 83.77 | 81.5 | **+2.27** | ALIGNED (above the paper) |
| tier7_multiturn | 58.52 | 54.6 | **+3.92** | ALIGNED (above the paper) |

`smart_home` is 73.6–76.0 % of every one of these draws (73.9–74.4 % of the populations they came
from) and scores 21.6–70.1 there, while
`wearables` and `smart_car` score 28.6–93.4. On tier 4 the spread is a factor of 2.6 —
`wearables` 55.56 against `smart_home` 21.60 — the widest relative gap this repository has measured
on any tier.

### The eight-tier picture, under both weightings

| tier | natural mixture | paper | outcome | equal-domain | delta vs paper |
|---|---:|---:|---|---:|---:|
| tier1_direct | 65.60 | 92.4 | FAIL | 80.60 | −11.80 |
| tier2_parametric | 79.60 | 84.6 | FAIL | 85.44 | +0.84 |
| tier3_multi_intent | 65.00 | 74.7 | FAIL | 73.85 | −0.85 |
| tier4_implicit | 28.20 | 33.4 | FAIL | 35.24 | +1.84 |
| tier5_needle | 80.80 | 90.6 | FAIL | 89.75 | −0.85 |
| tier6_correction | 75.80 | 81.5 | FAIL | 83.77 | +2.27 |
| tier7_multiturn | 49.40 | 54.6 | FAIL | 58.52 | +3.92 |
| tier8_intent_blending | 46.80 | 41.7 | **ALIGNED** | 47.94 | +6.24 |

**Seven of the eight tiers are inside the owner's 3-point band under equal-domain weighting, and
tier 1 is the only one that is not.** On the natural mixture only tier 8 is. Whatever separates this
runtime from the published row on tiers 2–8 is concentrated almost entirely in one stratum, and
tier 1 is a different problem, as its own verdict already said.

## 3. Where the misses go — the same named component, on four more tiers

Diagnostic only; no number here enters a decision.

| tier | misses | predicted name is a real registry tool | invents a name | same domain | other domain |
|---|---:|---:|---:|---:|---:|
| tier3_multi_intent | 175 | 174 | 1 | 122 | 52 |
| tier4_implicit | 359 | 349 | 10 | 137 | 212 |
| tier6_correction | 121 | 117 | 4 | 80 | 37 |
| tier7_multiturn | 253 | 249 | 4 | 127 | 122 |

**889 of 908 misses name another real tool of the 152-row registry; nineteen invent a name.** The
top confusions repeat the earlier verdicts' almost exactly:

| tier | rows | gold | predicted |
|---|---:|---|---|
| tier3 | 7 | `setSecurityMode` | `armSecuritySystem` (smart_home/security) |
| tier3 | 5 | `setColor` | `setLighting` (smart_home/core_control) |
| tier3 | 5 | `setGarageDoor` | `setGarageOpener` (smart_car/body_control) |
| tier3 | 5 | `rebootDevice` | `restartDevice` (smart_home/automation) |
| tier4 | 10 | `setLighting` | `setAmbientLighting` (smart_car/media_cabin) |
| tier4 | 7 | `findMyDevice` | `findPairedPhone` (wearables/device_state) |
| tier4 | 6 | `setVolume` | `adjustVolume` (smart_car/media_cabin) |
| tier6 | 11 | `setSecurityMode` | `armSecuritySystem` (smart_home/security) |
| tier6 | 8 | `setLighting` | `setLightState` (smart_home/lighting) |
| tier6 | 7 | `rebootDevice` | `restartDevice` (smart_home/automation) |
| tier7 | 13 | `setSecurityMode` | `armSecuritySystem` (smart_home/security) |
| tier7 | 8 | `setLighting` | `setAmbientLighting` (smart_car/media_cabin) |
| tier7 | 8 | `getNetworkHealth` | `runNetworkSpeedTest` (smart_home/maintenance) |

`setSecurityMode → armSecuritySystem`, `rebootDevice → restartDevice` and
`setColorTemperature → setAmbientLighting` are the same pairs tiers 1, 2, 5 and 8 produced. The
component is **near-synonym selection inside a registry that contains near-synonyms**, and it is now
measured on 3,900 rows across all eight tiers.

**Tier 4 is the exception worth naming:** 212 of its 349 registry-valid misses reach into *another*
domain, against 137 inside the gold tool's own. On every other tier measured so far the same-domain
share is the majority. On the tier where the intent is implicit, the model does not merely pick the
wrong synonym — it picks the wrong domain.

## 4. Tier 3 under both rules — the divergence is 40 points and it is structural

| tier | official TA (first call) | v2 TA (ordered) | delta | official EM | v2 EM | delta | rows naming > 1 call | gold rows with additional calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| tier3_multi_intent | 65.00 | **24.80** | **−40.20** | 19.40 | 2.00 | −17.40 | **263** | **500** |
| tier4_implicit | 28.20 | 28.20 | **+0.00** | 6.40 | 6.40 | +0.00 | 0 | 0 |
| tier6_correction | 75.80 | 75.40 | −0.40 | 24.00 | 23.60 | −0.40 | 8 | 0 |
| tier7_multiturn | 49.40 | 49.40 | **+0.00** | 10.40 | 10.40 | +0.00 | 0 | 0 |

**Every one of tier 3's 500 gold rows carries additional expected calls** — it is the multi-intent
tier by construction — and **263 of 500 responses named more than one call**. The official HF path
never populates `all_tool_calls`, so `a2t-toolcall-official` reads only the **first** parsed call
against the **primary** gold tool, while `a2t-toolcall-v2` compares the whole ordered predicted
sequence against the whole expected sequence and is scoring a strictly harder task. The named rules
are `first_call_only_vs_ordered_sequence`, `primary_gold_tool_vs_full_expected_sequence` and (for
the exact-match column) `default_argument_credit`.

At 40.20 pp this is the largest official/v2 divergence measured on any tier — larger than tier 8's
31 pp, because tier 8's gold carries additional calls on 496 of 500 rows while tier 3's carries them
on all 500.

**On the three single-call tiers the two scorers agree to 0.00, 0.40 and 0.00 pp.** That is the
fourth independent confirmation that the official scorer and `a2t-toolcall-v2` are the same
measurement wherever gold asks for one call. Tier 6's 0.40 pp comes from the eight rows that named a
second call anyway.

**Which number is the paper's is not ambiguous.** The paper reports 74.7 for tier 3, the released
evaluator is the first-call one, and the FAIL verdict above is stated against the official scorer,
as preregistered. The v2 column is reported beside it, not instead of it.

## 5. Tier 7 — which turn the released evaluator actually hears

This is the tier-specific finding of the flight, and it changes how its number should be read.

`Tier7Dataset._get_audio_paths` returns `sorted(query_dir.glob("turn_*_user_*.wav"))` and
`BenchmarkEvaluator` evaluates `audio_paths[0]`, so the request carries **the first user turn only**
— no chat history, no agent audio, no later user turn — while the gold call is what the whole
conversation resolves to.

| fact | value |
|---|---|
| turn index flown, all 500 rows | `turn_00`, 500 of 500 |
| user turns per drawn query | 2 on 345, 3 on 153, 4 on 2 |
| queries whose first user turn is their **only** user turn | **0 of 2,146** |
| queries with later user turns | **2,146 of 2,146** |
| last user turn of the population | `turn_02` on 1,445, `turn_04` on 677, `turn_03` on 18, `turn_06` on 6 |
| how the frozen 400 bound the tier | `chat_history[-1]`, the **final** user turn (`turn_02` on 35, `turn_04` on 14, `turn_03` on 1) |
| shared sample ids between the two rosters | **0** |

So the released protocol asks the model to produce the conversation's resolved tool call from its
opening utterance, on every single query. Our 49.40 on `turn_00` sits 8.60 points under the frozen
400's 58.00 on the final user turn — and that 8.60 is a *protocol* difference at least as much as a
population one, because the two rosters share no query and bind different audio for the same tier.
The population-effect row for tier 7 in section 6 must be read with that in mind.

Whether the authors' own Table-3 number came from this first-turn binding is unknowable from the
release: the loader says first turn, and nothing else in the released code or the paper says
otherwise.

## 6. The population effect, measured

| tier | frozen 400 (n = 50) | official population (n = 500) | effect |
|---|---:|---:|---:|
| tier3_multi_intent | 72.00 | 65.00 | −7.00 pp |
| tier4_implicit | 28.00 | 28.20 | **+0.20 pp** |
| tier6_correction | 84.00 | 75.80 | −8.20 pp |
| tier7_multiturn | 58.00 | 49.40 | −8.60 pp (also a binding change, section 5) |

Not a paired contrast — the populations differ (10 / 13 / 12 / 0 shared queries out of 50). On
tiers 1, 2, 5 and 8 the move to the official population was **positive** (+5.6, +5.6, +2.8, +12.8);
here three of the four move negative. The frozen 400's 50-row tiers were simply noisy in both
directions, which is the whole reason these flights were flown.

## 7. Deviations still in force

1. **Quantization.** Q4_K_M against the release's bf16. Untouched here; still the last of the three
   ranked Tier-1 suspects standing, and it now has the full eight-tier table to explain or not.
2. **Tier 7 hears one turn**, and every tier-7 query has later user turns (section 5). This is the
   release's own protocol, flown unchanged, and it is the single largest interpretive fact about the
   tier-7 number.
3. **Tier 7's population is narrowed by 54 of 2,146 (2.5 %)** — 50 ids the immutable D1 artifact
   already binds to the final user turn, and 4 whose `chat_history` ends on an agent turn and which
   `data.audio2tool._entry_media` refuses. Both exclusions are this repository's identity
   constraints, not the release's, and both are named id by id in the roster receipt.
4. **Tier 4 ships irregularly.** Seven of its 2,132 query directories ship three or four recordings
   instead of two, and two of those duplicate a manifest row (`query_00232` ids 468/469,
   `query_00763` ids 1534/1535). On all seven the released loader's first resolvable CSV row is
   still the manifest's lowest-id row, verified directory by directory, so the pick is unaffected.
5. **Population reconstruction generally.** Verified on 2,146 + 2,132 + 2,146 + 2,146 directories
   with zero disagreements and zero unresolved. If the authors evaluated their internal corpus (up
   to 25 speakers per query) rather than the two the public release ships, "first successful
   speaker" resolves to a different wav for most queries. Unknowable from the release.
6. **The 654-second rows are not speech.** All three (`tier3_multi_intent:003555`,
   `tier6_correction:003151`, `tier7_multiturn:001033`) are the release's synthesis defect; the
   tier-6 and tier-7 ones returned prose refusals describing a dog and are two of the flight's eight
   parse failures, and the tier-3 one parsed to `activateRoutine` against a gold of `installApp`.
   All three are misses. They are 3 of 2,000 rows and cannot move any tier by more than 0.2 pp.
7. **Sample rate, serving geometry, seed and temperature.** 24 kHz material (not the README's
   16 kHz); `-c 49152 -np 2`, the tier-1 official-population geometry, forced by those same three
   654-second rows; seed 20260803 and temperature 0, both inert under greedy decoding.

## 8. Throughput

| quantity | T3467-official-pop-2000 |
|---|---:|
| contacts | 2,000 of 2,080 registered (2,008 planned) |
| speech audio | 11,964.831167 of 12,100 s |
| serving geometry | `-c 49152 -np 2`, 24,576/slot |
| model load | 10.035 s |
| generation wall | 1,344 s |
| end-to-end wall (preflight to server stop) | 1,383 s |
| summed per-call latency | 1,083.44 s |
| mean per-call latency | 0.542 s |
| prompt tokens per call | 3,667.4 |
| completion tokens per call | 16.3 |
| parse failures | 8 of 2,000 (tier 4 3, tier 7 3, tier 6 2, tier 3 0) |
| GPU `enforced.power.limit` before / after | 100.00 W / 100.00 W |

One attempt, COMPLETED and FINALIZED, zero aborted, zero orphans, no recovery re-registration used,
`study_repo_dirt` empty.

## 9. What this authorizes

Nothing new. The population is discovery data, no knob was tuned on it, and this is not a
superiority, generality or Stage-3 claim. Mechanism work stays stopped. No tier is re-flown and no
roster is extended.

What it changes is that the question is now fully specified:

- **The eight-tier table is complete at n = 500 per tier.** One tier ALIGNED, seven FAIL on the
  natural mixture.
- **Seven of eight would be ALIGNED under equal-domain weighting**, tier 1 excepted (80.60 against
  92.4). The residual gap on tiers 2–8 is a `smart_home` effect, measured now on 3,900 rows, and
  tier 1 is a separate problem its own verdict already characterized.
- **Tier 4 misses across domains, not within them** — 212 of 349 registry-valid misses land in
  another domain, the reverse of every other tier. The implicit tier is where domain selection
  itself breaks.
- **Tier 3's official/v2 divergence is 40.2 points**, the largest measured, and entirely explained
  by first-call-only scoring against gold that always asks for more than one call.
- **Tier 7's released protocol sends the conversation's opening turn**, never the turn that states
  the request, on all 2,146 of its queries. Any tier-7 comparison that does not say which turn was
  bound is not comparing the same thing.
- **The named component still holds:** 889 of 908 misses name another real registry tool. A
  candidate set narrower than all 152 would act on every tier measured.

Whether the next flight spends itself on quantization (the registered probe), on a narrowed
candidate set, on the `smart_home` stratum specifically, or on asking the authors which corpus and
which tier-7 turn produced Table 3, is an owner decision.
