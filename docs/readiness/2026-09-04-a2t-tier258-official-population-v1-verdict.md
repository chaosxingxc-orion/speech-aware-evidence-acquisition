# Audio2Tool tiers-2/5/8 official population, v1 — verdict

One run flown 2026-09-04 on study commit `b52c22b0`, profile `baseline-reproduction`, one cell.

| Run id | Cell | Attempt | Rows | Manifest SHA-256 |
|---|---|---|---:|---|
| `SAEA-A2T-TIER258-OFFICIAL-POPULATION-V1` | `T258-official-pop-1500` | `attempt-20260904T193726Z-t258officialpop1500` | 1,500 | `7de7429110e978784fc8303e632c54360d9cdbb70aa61e9d084b957f68db847f` |

Preregistration: `docs/readiness/2026-09-04-a2t-tier258-official-population-v1-preregistration.md`.
Full numbers:
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-tier258-official-population-v1/result-summary.json`
(SHA-256 `42a88f0d2ae81a168115c729725b99be8749559cf28047fe3b8e76bf4065956f`).
Paper-facing scorer: `a2t-toolcall-official` — the pinned release's own `metrics.py`, git blob
`d98277bcf69795c9a0ae54e538c170abfd8c51ca`, commit `b9d5383ca30945fbafb965a04bea40117e1e8a82`.

## Verdict: tier 8 ALIGNED, tiers 2 and 5 FAIL — and on both failing tiers the shortfall is one stratum, not the tier.

| tier | ours | CI90 | paper | delta | ALIGNED needs | outcome |
|---|---:|---|---:|---:|---:|---|
| tier2_parametric | **79.60** | [76.48, 82.40] | 84.6 | −5.00 | ≥ 81.6 | **FAIL** |
| tier5_needle | **80.80** | [77.74, 83.53] | 90.6 | −9.80 | ≥ 87.6 | **FAIL** |
| tier8_intent_blending | **46.80** | [43.16, 50.48] | 41.7 | **+5.10** | ≥ 38.7 | **ALIGNED** |

n = 500 per tier, official scorer, one contact per row, 1,499 of 1,500 rows parsed (99.93 %).
Neither failing tier is CONSISTENT-WITHIN-NOISE: 84.6 and 90.6 both sit outside their Wilson CI90,
which is the whole point of moving from n = 50 to n = 500. The three tiers the frozen 400 could not
decide are now decided.

**Tier 8 clears the band by 5.1 points**, the first Audio2Tool tier this repository has ever landed
ALIGNED under the owner's rule.

### The floor rule

| tier | ours | Qwen-2.5-Omni-7B | delta | weakest published SpeechLM | delta |
|---|---:|---:|---:|---:|---:|
| tier2_parametric | 79.60 | 80.6 | **−1.00 (BELOW)** | 75.3 | +4.30 |
| tier5_needle | 80.80 | 74.1 | +6.70 | 58.9 | +21.90 |
| tier8_intent_blending | 46.80 | 36.5 | +10.30 | 30.4 | +16.40 |

**One tier is below a degraded model's published number, and it is called out here as the rule
requires: tier 2 sits 1.00 pp under Qwen-2.5-Omni-7B's 80.6.** Its CI90 [76.48, 82.40] contains
80.6, so the gap is not itself separable from noise at n = 500 — but the rule is a floor, not a
significance test, and the observation is below it. No tier is below the weakest published SpeechLM
row.

## 1. Exact match and parameter F1, beside the paper's own columns

| tier | our EM | CI90 | paper EM | delta | our param F1 macro | micro | v2 slot F1 | paper Slot F1 |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| tier2_parametric | **31.20** | [27.90, 34.70] | 15.6 | **+15.60** | 48.21 | 45.25 | 39.94 | 21.7 |
| tier5_needle | **22.80** | [19.87, 26.03] | 36.0 | −13.20 | 35.87 | 34.75 | 29.37 | 41.6 |
| tier8_intent_blending | **22.40** | [19.49, 25.61] | 12.4 | **+10.00** | 30.99 | 23.87 | 20.46 | 19.9 |

This is the sharpest surprise in the flight and it runs the opposite way to tier 1. On tier 1 the
published exact match was 92.4 against our 10.20 — an 82-point hole. Here **we beat the published
exact match on two of the three tiers**, by 15.6 and 10.0 points, and our parameter F1 beats the
published Slot F1 on tier 2 by 26.5 points and on tier 8 by 11.1. Only tier 5 is short on both.

The official parameter F1 is a macro average of per-sample key precision/recall/F1 while the paper's
"Slot F1" column is defined in neither the paper nor the released code, so the two are tabled side
by side rather than differenced; the same caution the tier-1 verdict recorded applies. The exact
match comparison has no such ambiguity — it is the released `metrics.py` computing the same quantity
on both sides.

## 2. By domain, and this is where both failures live

| tier | domain | n | tool accuracy | CI90 | exact match |
|---|---|---:|---:|---|---:|
| tier2_parametric | `wearables` | 108 | **95.37** | [90.79, 97.73] | 51.85 |
| | `smart_car` | 22 | **86.36** | [70.35, 94.42] | 54.55 |
| | `smart_home` | 370 | **74.59** | [70.70, 78.13] | 23.78 |
| | natural mixture | 500 | 79.60 | [76.48, 82.40] | 31.20 |
| | **equal-domain** | 500 | **85.44** | — | — |
| tier5_needle | `smart_car` | 41 | **97.56** | [89.78, 99.45] | 53.66 |
| | `wearables` | 91 | **96.70** | [92.03, 98.67] | 46.15 |
| | `smart_home` | 368 | **75.00** | [71.11, 78.52] | 13.59 |
| | natural mixture | 500 | 80.80 | [77.74, 83.53] | 22.80 |
| | **equal-domain** | 500 | **89.75** | — | — |
| tier8_intent_blending | `wearables` | 211 | **58.77** | [53.12, 64.20] | 31.28 |
| | `smart_car` | 94 | **55.32** | [46.85, 63.49] | 35.11 |
| | `smart_home` | 195 | **29.74** | [24.67, 35.38] | 6.67 |
| | natural mixture | 500 | 46.80 | [43.16, 50.48] | 22.40 |
| | **equal-domain** | 500 | **47.94** | — | — |

**The tier-1 finding replicates on all three tiers, and it decides both failures.** Under
equal-domain weighting tier 2 scores **85.44 against a published 84.6 — above the paper** — and
tier 5 scores **89.75 against 90.6, inside the 3-point band**. Both tiers fail on the natural
mixture only because `smart_home` is 73.6–74.0 % of each population and scores 74.59 and 75.00
there, while `wearables` and `smart_car` score 86–98.

That is now four tiers in a row (1, 2, 5, 8) on which `smart_home` is 20–47 points below the other
two domains on this runtime. On tier 8 the pattern is present but weaker in relative terms — every
domain is hard there — and the tier still clears the band.

## 3. Where the misses go — the same named component, on three more tiers

Diagnostic only; no number here enters a decision.

| tier | misses | predicted name is a real registry tool | invents a name | same domain | other domain |
|---|---:|---:|---:|---:|---:|
| tier2_parametric | 102 | 100 | 2 | 64 | 36 |
| tier5_needle | 96 | **96** | **0** | 63 | 33 |
| tier8_intent_blending | 266 | 264 | 2 | 224 | 40 |

**460 of 464 misses name another real tool of the 152-row registry; four invent a name.** The top
confusions are near-synonyms, exactly as on tier 1:

| tier | rows | gold | predicted |
|---|---:|---|---|
| tier2 | 9 | `rebootDevice` (smart_home/maintenance) | `restartDevice` (smart_home/automation) |
| tier2 | 8 | `setSecurityMode` (smart_home/core_control) | `armSecuritySystem` (smart_home/security) |
| tier2 | 6 | `setGroupLightState` | `setLighting` (smart_home/core_control) |
| tier2 | 5 | `setColor` | `setAmbientLighting` (smart_car/media_cabin) |
| tier2 | 5 | `setGarageDoor` | `setGarageOpener` (smart_car/body_control) |
| tier5 | 13 | `setSecurityMode` | `armSecuritySystem` (smart_home/security) |
| tier5 | 11 | `setLighting` | `setLightState` (smart_home/lighting) |
| tier5 | 8 | `setFanMode` | `setFanSpeed` (smart_car/climate_environment) |
| tier5 | 6 | `setColorTemperature` | `setAmbientLighting` (smart_car/media_cabin) |
| tier5 | 6 | `getApplianceState` | `getApplianceStatus` (smart_home/appliances) |
| tier8 | 4 | `setColorTemperature` | `setAmbientLighting` (smart_car/media_cabin) |
| tier8 | 4 | `getBiometricData` | `startWorkout` (wearables/health_activity) |
| tier8 | 3 | `rebootDevice` | `restartDevice` (smart_home/automation) |
| tier8 | 3 | `setLockState` | `setLockState_home` (smart_home/security) |

`rebootDevice → restartDevice`, `setSecurityMode → armSecuritySystem` and
`setColorTemperature → setAmbientLighting` are the same three confusions the tier-1 verdict named.
The component is not tier-specific: it is **near-synonym selection inside a registry that contains
near-synonyms**, and it is now measured on 1,500 rows across three more tiers.

## 4. Tier 8 under both rules — the divergence is 31 points and it is structural

| tier | official TA (first call) | v2 TA (ordered) | delta | official EM | v2 EM | delta | rows naming > 1 call | gold rows with additional calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| tier2_parametric | 79.60 | 79.60 | **+0.00** | 31.20 | 31.40 | +0.20 | 0 | 0 |
| tier5_needle | 80.80 | 80.80 | **+0.00** | 22.80 | 24.60 | +1.80 | 0 | 0 |
| tier8_intent_blending | 46.80 | **15.80** | **−31.00** | 22.40 | 1.80 | −20.60 | **215** | **496** |

**The two scorers agree to the last row on both single-call tiers** — 0.00 pp on tool accuracy, and
zero rows named more than one call on either. That is the third independent confirmation of the
tier-1 finding that the official scorer and `a2t-toolcall-v2` are the same measurement wherever gold
asks for one call.

On tier 8 they diverge by 31 points, and the reason is written into the data rather than inferred:
**496 of the 500 tier-8 gold rows carry additional expected calls**, and **215 of 500 responses name
more than one call**. The official HF path never populates `all_tool_calls`, so
`a2t-toolcall-official` reads only the **first** parsed call against the **primary** gold tool;
`a2t-toolcall-v2` compares the whole ordered predicted sequence against the whole expected sequence
and is therefore scoring a strictly harder task. The named rules are
`first_call_only_vs_ordered_sequence`, `primary_gold_tool_vs_full_expected_sequence` and (for the
exact-match column) `default_argument_credit`.

**Which number is the paper's is not ambiguous.** The paper reports 41.7 for tier 8, the released
evaluator is the first-call one, and the ALIGNED verdict above is stated against the official
scorer, as preregistered. The v2 column is reported beside it, not instead of it: on the ordered
rule tier 8 would be 15.80, and nothing in the release computes that.

## 5. The population effect, measured

| tier | frozen 400 (n = 50) | official population (n = 500) | effect |
|---|---:|---:|---:|
| tier2_parametric | 74.00 | 79.60 | **+5.60 pp** |
| tier5_needle | 78.00 | 80.80 | **+2.80 pp** |
| tier8_intent_blending | 34.00 | 46.80 | **+12.80 pp** |

Not a paired contrast — the populations differ (12 / 13 / 32 shared queries out of 50). Two
independent estimates of the same tier under the same protocol. The tier-1 flight measured +5.60 pp
for the same change; tiers 2 and 5 land in the same place, tier 8 moves three times as far. Tier 8's
larger move is the one to treat with care: its population is only 821 queries, the draw covers 60.9 %
of it, and the frozen 400's 50 tier-8 rows are 32 of the 500 drawn here, so the two estimates are
not independent to the same degree as on tiers 2 and 5.

## 6. Deviations still in force

1. **Quantization.** Q4_K_M against the release's bf16. Untouched here; still the last of the three
   ranked Tier-1 suspects standing, and it now has three more tiers of evidence to explain or not.
2. **The released `tier5_dataset.py` cannot read the released tier-5 dataset.** Its
   `_get_audio_paths` appends only when `Path(audio_path).exists()` and has no `query_dir/<basename>`
   fallback; because `generation_results.csv` exists in every tier-5 query directory the `else`-branch
   glob never runs either, so a literal replay against the public release resolves **zero** audio
   paths and the loader yields an empty dataset. This flight applied the tier-1/tier-2 spelling of
   the same walk, which agrees with the manifest-first pick on all 2,146 directories. It is the
   largest residual uncertainty about the tier-5 cell.
3. **Population reconstruction generally.** Verified on 3,160 + 2,146 + 821 directories with zero
   disagreements and zero unresolved. If the authors evaluated their internal corpus (up to 25
   speakers per query on tiers 2 and 5) rather than the two the public release ships, "first
   successful speaker" resolves to a different wav for most queries. Unknowable from the release.
4. **Tier 8's file-order rule resolved trivially.** Each of the 821 query directories ships exactly
   one `mixed.wav`, there is no `generation_results.csv`, and every manifest row carries
   `speaker_idx` `null`. The released manifest and the released loader cannot disagree.
5. **Tier 8's gold is the foreground call**, as the released loader defines it; `background_*` is
   never read. Unchanged from the frozen 400.
6. **Sample rate, serving geometry, seed and temperature.** 24 kHz material (not the README's
   16 kHz); `-c 49152 -np 3`, the same geometry `R-official-raw` and `W-official-raw-yaml` flew, with
   the longest wav at 32.43375 s and a worst request of 4,268 tokens; seed 20260803 and temperature 0,
   both inert under greedy decoding.

## 7. Throughput

| quantity | T258-official-pop-1500 |
|---|---:|
| contacts | 1,500 of 1,560 registered (1,508 planned) |
| speech audio | 9,784.337875 of 9,900 s |
| serving geometry | `-c 49152 -np 3`, 16,384/slot |
| model load | 10.0 s |
| generation wall | 934 s |
| end-to-end wall (preflight to server stop) | 972 s |
| summed per-call latency | 1,249.76 s |
| mean per-call latency | 0.833 s |
| prompt tokens per call | 3,674.5 |
| completion tokens per call | 16.6 |
| parse failures | 1 of 1,500 (tier 8) |
| GPU `enforced.power.limit` before / after | 100.00 W / 100.00 W |

One attempt, COMPLETED and FINALIZED, zero aborted, zero orphans, no recovery re-registration used,
`study_repo_dirt` empty.

## 8. What this authorizes

Nothing new. The population is discovery data, no knob was tuned on it, and this is not a
superiority, generality or Stage-3 claim. Mechanism work stays stopped. Tiers 1, 3, 4, 6 and 7 are
not re-flown and the roster is not extended.

What it changes is the shape of the open question:

- **Tier 8 is aligned.** 46.80 against a published 41.7, clear of the band by 5.1 points and clear of
  both floors. There is no tier-8 gap on this runtime.
- **Tiers 2 and 5 fail on the natural mixture and would pass on an equal-domain one** (85.44 against
  84.6; 89.75 against 90.6). Whatever the residual gap is, it is concentrated in `smart_home`, which
  is also where tier 1 lost 36.7 points. Four tiers, one stratum.
- **Tier 2 is the one tier below a degraded model's published number** (−1.00 pp against
  Qwen-2.5-Omni-7B), with 80.6 inside its CI90. If any single number in this flight deserves a
  follow-up it is that one.
- **Our exact match beats the published exact match on tiers 2 and 8** by 15.6 and 10.0 points, which
  is the reverse of tier 1's 82-point hole and says the argument-extraction path is not the weak
  link on these tiers.
- **The named component holds:** 460 of 464 misses name another real registry tool, and the top
  confusions are the same near-synonym pairs tier 1 produced. A candidate tool set narrower than all
  152 would act here on every tier measured so far.

Whether the next flight spends itself on quantization (the registered probe), on a narrowed candidate
set, or on asking the authors which corpus produced Table 3, is an owner decision.
