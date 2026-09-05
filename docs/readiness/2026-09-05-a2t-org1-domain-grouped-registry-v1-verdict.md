# A2T-ORG-1: the domain-grouped tool registry, v1 — verdict

One run flown 2026-09-05 on study commit `227c0ef2`, profile `baseline-reproduction`, one cell.

| Run id | Cell | Attempt | Rows | Manifest SHA-256 |
|---|---|---|---:|---|
| `SAEA-A2T-ORG1-DOMAIN-GROUPED-V1` | `ORG1-grouped-raw` | `attempt-20260905T171519Z-org1groupedraw` | 4,000 | `55a6c23a03a2c882d5a7f8c25dddf7f21801e8d0192adfe53549ec6c7cf52087` |

Preregistration: `docs/readiness/2026-09-05-a2t-org1-domain-grouped-registry-v1-preregistration.md`
(owner GO recorded verbatim in its section 8.1).
Full numbers:
`docs/checks/speech-aware-evidence-acquisition/2026-09-05-a2t-org1-domain-grouped-4000-v1/result-summary.json`
(SHA-256 `cacb2cc26071f83509707a50f521b897486946577d8b0ffc3d2c7b9b4d2edea1`).
Paper-facing scorer: `a2t-toolcall-official` — the pinned release's own `metrics.py`, git blob
`d98277bcf69795c9a0ae54e538c170abfd8c51ca`, commit `b9d5383ca30945fbafb965a04bea40117e1e8a82`.

## Verdict: HARMFUL. The domain cue does exactly what H1 said it would, and it still costs 3.23 points.

Pooled official tool accuracy over the 4,000 rows, paired against each row's own sealed
official-protocol output, tier-stratified bootstrap, 10,000 replicates, seed 20260903:

| quantity | value |
|---|---|
| baseline (compact registry) | **61.40 %** |
| ORG-1 (domain-grouped registry) | **58.17 %** |
| delta | **−3.23 pp** |
| CI90 | **[−4.15, −2.33]** |
| saves / harms / ties | **194 / 323 / 3,483** |
| exact sign test | **p < 0.0001** |

The CI90 upper bound is below zero, so the preregistered rule reads **HARMFUL**: ORG-1 is dropped
and the reason is recorded here before A2T-ORG-2 is registered. Under equal-domain weighting the
answer is the same, 68.11 → 65.04, **−3.07 pp, CI90 [−4.12, −2.01]**.

That is the letter of it. The substance is more interesting than the sign, in three ways:

1. **The mechanism fires.** Cross-domain twin misses fall from 621 to 521 (−16 %), and the named
   cross-domain pairs collapse: `setColorTemperature → setAmbientLighting` 35 → 9,
   `setColor → setAmbientLighting` 25 → 5, `setLighting → setAmbientLighting` 28 → 11. Summed over
   the named cross-domain twins the count goes **183 → 113, −38 %**. Telling the model which domain
   a tool belongs to genuinely stops it reaching into another domain.
2. **The misses do not become correct answers; they become same-domain misses.** Same-domain twin
   misses rise from 898 to 1,118 (+24 %), and the named same-domain twins go **236 → 321**:
   `rebootDevice → restartDevice` 41 → 74, `getAirQuality → getAirQuality_diag` 11 → 36,
   `setColor → setLighting` 15 → 32, `activateScene → activateRoutine` 12 → 24. The domain header
   moves the error one step closer to the right answer and no further.
3. **The loss is not confined to the stratum the cue was aimed at.** Every domain loses —
   `smart_home` −3.26, `wearables` −3.38, `smart_car` −2.56 — and `wearables` has 13 tools and the
   fewest confusable neighbours of any domain in the registry. A cue that only supplied domain
   knowledge could not cost 3.4 points there. Something about the prompt's FORM, not its content,
   is doing part of this.

## 1. Per tier, with the published column beside every tier

Official tool accuracy (%), n = 500 per tier, paired.

| tier | baseline | ORG-1 | delta | paper | ORG-1 vs paper | saves | harms |
|---|---:|---:|---:|---:|---:|---:|---:|
| tier1_direct | 65.60 | 63.60 | **−2.00** | 92.4 | −28.80 | 26 | 36 |
| tier2_parametric | 79.60 | 74.80 | **−4.80** | 84.6 | −9.80 | 17 | 41 |
| tier3_multi_intent | 65.00 | 63.20 | **−1.80** | 74.7 | −11.50 | 37 | 46 |
| tier4_implicit | 28.20 | 26.80 | **−1.40** | 33.4 | −6.60 | 25 | 32 |
| tier5_needle | 80.80 | 77.40 | **−3.40** | 90.6 | −13.20 | 21 | 38 |
| tier6_correction | 75.80 | 71.00 | **−4.80** | 81.5 | −10.50 | 20 | 44 |
| tier7_multiturn | 49.40 | 45.60 | **−3.80** | 54.6 | −9.00 | 30 | 49 |
| tier8_intent_blending | 46.80 | 43.00 | **−3.80** | 41.7 | **+1.30** | 18 | 37 |
| **pooled, n = 4,000** | **61.40** | **58.17** | **−3.23** | — | — | **194** | **323** |

The paper column is a ceiling reference and no gate is set relative to it. It does carry one fact
worth stating plainly: **tier 8 was the only Audio2Tool tier this repository had ever landed above
the published row, and ORG-1 spends most of that margin.** It was +5.10 pp over 41.7; it is now
+1.30.

Harms exceed saves on all eight tiers. There is no tier on which the domain cue is a net gain.

## 2. Per domain, and per tier × domain

| domain | n | baseline | ORG-1 | delta | saves | harms |
|---|---:|---:|---:|---:|---:|---:|
| `smart_home` | 2,792 | 54.98 | 51.72 | **−3.26** | 172 | 263 |
| `wearables` | 857 | 78.41 | 75.03 | **−3.38** | 12 | 41 |
| `smart_car` | 351 | 70.94 | 68.38 | **−2.56** | 10 | 19 |
| natural mixture | 4,000 | 61.40 | 58.17 | −3.23 | 194 | 323 |
| **equal-domain** | 4,000 | **68.11** | **65.04** | **−3.07** | — | — |

Per tier × domain (tool accuracy, baseline → ORG-1):

| tier | `smart_home` | `wearables` | `smart_car` |
|---|---|---|---|
| tier1_direct | 55.71 → 53.53 (−2.17) | 93.41 → 92.31 (−1.10) | 92.68 → 90.24 (−2.44) |
| tier2_parametric | 74.59 → 68.65 (**−5.95**) | 95.37 → 93.52 (−1.85) | 86.36 → 86.36 (0.00) |
| tier3_multi_intent | 59.51 → 57.61 (−1.90) | 79.12 → 76.92 (−2.20) | 82.93 → 82.93 (0.00) |
| tier4_implicit | 21.60 → 22.13 (**+0.53**) | 55.56 → 45.56 (**−10.00**) | 28.57 → 28.57 (0.00) |
| tier5_needle | 75.00 → 71.20 (−3.80) | 96.70 → 93.41 (−3.30) | 97.56 → 97.56 (0.00) |
| tier6_correction | 70.11 → 64.40 (−5.71) | 93.41 → 93.41 (0.00) | 87.80 → 80.49 (−7.32) |
| tier7_multiturn | 42.63 → 38.68 (−3.95) | 77.38 → 72.62 (−4.76) | 55.56 → 55.56 (0.00) |
| tier8_intent_blending | 29.74 → 26.67 (−3.08) | 58.77 → 54.98 (−3.79) | 55.32 → 50.00 (−5.32) |

**One cell of twenty-four is positive: tier 4 × `smart_home`, +0.53 pp on 375 rows.** That is exactly
where the tiers-3/4/6/7 verdict predicted a domain cue would act — tier 4 is the one tier whose
registry-valid misses cross domains more often than not (212 of 349), the tier where "the model does
not merely pick the wrong synonym, it picks the wrong domain". The cue helps there and only there,
and the effect is a third of a standard error.

The `smart_car` column is mostly flat because it is small (22–94 rows per tier) and already scores
high; the two places it moves are tier 6 (−7.32 on 41 rows) and tier 8 (−5.32 on 94).

## 3. Where the misses went — the whole finding in one table

Miss classes over all 4,000 rows, resolved from `tools_registry.csv` (the predicted tool's domain
against the gold tool's), never asserted:

| class | baseline | ORG-1 | delta |
|---|---:|---:|---:|
| correct | 2,456 | 2,327 | **−129** |
| **cross-domain twin** (predicted a real tool in ANOTHER domain) | **621** | **521** | **−100** |
| **same-domain twin** (predicted a real tool in the SAME domain) | **898** | **1,118** | **+220** |
| invented a name | 16 | 8 | −8 |
| produced no call at all | 9 | 26 | **+17** |

The named confusion pairs, before and after:

| gold | predicted | class | before | after | delta |
|---|---|---|---:|---:|---:|
| `setSecurityMode` | `armSecuritySystem` | same-domain | 64 | 72 | +8 |
| `rebootDevice` | `restartDevice` | same-domain | 41 | **74** | **+33** |
| `setColorTemperature` | `setAmbientLighting` | cross-domain | 35 | **9** | **−26** |
| `setLighting` | `setLightState` | same-domain | 33 | 22 | −11 |
| `setLighting` | `setAmbientLighting` | cross-domain | 28 | **11** | **−17** |
| `findMyDevice` | `findPairedPhone` | cross-domain | 25 | 17 | −8 |
| `getApplianceState` | `getApplianceStatus` | same-domain | 25 | 24 | −1 |
| `setColor` | `setAmbientLighting` | cross-domain | 25 | **5** | **−20** |
| `setGarageDoor` | `setGarageOpener` | cross-domain | 22 | 33 | +11 |
| `setFanMode` | `setFanSpeed` | cross-domain | 21 | 18 | −3 |
| `setVolume` | `adjustVolume` | cross-domain | 18 | 9 | −9 |
| `getNetworkHealth` | `runNetworkSpeedTest` | same-domain | 16 | 18 | +2 |
| `setColor` | `setLighting` | same-domain | 15 | **32** | **+17** |
| `setGroupLightState` | `setLighting` | same-domain | 15 | 14 | −1 |
| `activateScene` | `activateRoutine` | same-domain | 12 | **24** | **+12** |
| `getAirQuality` | `getAirQuality_diag` | same-domain | 11 | **36** | **+25** |
| `setLockState` | `setLockState_home` | cross-domain | 9 | 11 | +2 |
| `getBiometricData` | `startWorkout` | same-domain | 4 | 5 | +1 |
| **named cross-domain, summed** | | | **183** | **113** | **−70** |
| **named same-domain, summed** | | | **236** | **321** | **+85** |

`setColor → setAmbientLighting` (cross-domain, −20) and `setColor → setLighting` (same-domain, +17)
are the same rows moving: the header tells the model that `setAmbientLighting` is a smart_car tool,
it stops choosing it, and it chooses the wrong smart_home lighting tool instead.

### The cross-domain share of the gain

Preregistered as (baseline cross-domain-twin misses corrected) / (all misses corrected):

| quantity | value |
|---|---:|
| rows corrected (baseline wrong → ORG-1 right) | 194 |
| of which the baseline miss was a cross-domain twin | 92 |
| of which the baseline miss was a same-domain twin | 96 |
| of which the baseline invented a name | 6 |
| **cross-domain share of the gain** | **0.474** |
| rows broken (baseline right → ORG-1 wrong) | 323 |
| of which ORG-1's new miss is a same-domain twin | 203 |
| of which ORG-1's new miss is a cross-domain twin | 111 |
| of which ORG-1 produced no call at all | 6 |
| **net** | **−129** |

Under half the gain is cross-domain, so even the ADMITTED rule's second clause fails on its own
terms. And the decomposition of the 323 broken rows is the finding: **203 of them are new
same-domain confusions.** The mechanism trades 92 cross-domain corrections for 203 same-domain
regressions.

## 4. The secondary metrics, each as a paired delta

Same 4,000 rows, same pairing, same bootstrap.

| metric | baseline | ORG-1 | delta | CI90 | saves / harms | sign p |
|---|---:|---:|---:|---|---|---:|
| official exact match | 18.350 | 17.700 | −0.650 | [−1.200, −0.100] | 79 / 105 | 0.0650 |
| official parameter F1 (macro) | 29.280 | 28.505 | −0.775 | [−1.392, −0.173] | 195 / 242 | 0.0277 |
| parse rate | 99.775 | 99.350 | **−0.425** | [−0.625, −0.225] | 3 / 20 | 0.0005 |
| `a2t-toolcall-v2` ordered tool accuracy | 52.450 | 50.250 | −2.200 | [−3.150, −1.250] | 214 / 302 | 0.0001 |
| `a2t-toolcall-v2` exact match | 14.350 | 13.825 | −0.525 | [−1.050, +0.000] | 69 / 90 | 0.1124 |

Parameter F1 micro-pooled: 24.396 → 23.365. Rows naming more than one call: 486 → 505.

**Every secondary metric moves the same way as the primary**, and the parse-rate row is the sharpest
small signal in the flight: 9 unparseable responses become 26. Three rows recover and twenty break.
Whatever the grouped prompt does to the output contract, it is not neutral, and `a2t-toolcall-v2`'s
ordered rule sees the same −2.2 pp the official first-call rule sees at −3.2, so the loss is not a
scoring artefact of either rule.

## 5. Why HARMFUL rather than NULL — two separable channels

**Channel 1: substitution, worth roughly zero.** The domain header removes 100 cross-domain misses
and adds 220 same-domain ones. On the metric that is not a gain at all; a wrong tool is a wrong tool.
H1's premise — that the missing cue is the domain — is *confirmed as a description of the model's
behaviour* and *refuted as a lever on accuracy*, because the neighbourhood the model falls into once
the domain is fixed is exactly as confusable as the one it left. The tier-1 verdict named that
neighbourhood already: 50 distinct smart_home gold names competing with 53 same-domain entries.

**Channel 2: a prompt-form cost, worth about three points.** Substitution alone would leave the
pooled delta near zero. It is −3.23, and the loss appears where domain knowledge cannot be the
explanation: `wearables` −3.38 pp on 13 tools with almost nothing to confuse them with; tier 6
`smart_car` −7.32; the parse rate down 0.425 pp. The three candidate causes, in the order this
flight would rank them:

1. **Prompt length and shape.** The grouped block is 87 text tokens longer (3,668 against 3,581) and
   465 lines against 155, with the signature and its description on separate lines. Every tool's
   description is now a line of its own rather than the tail of a `- signature: description` pair,
   which is a weaker association between the two halves of what a tool IS.
2. **Header salience.** Three `## DOMAIN` headers are the most prominent tokens in a 16,490-character
   message. They make the domain decision easy and, plausibly, make the within-domain decision
   relatively harder to attend to — which is precisely the substitution channel above, seen from the
   prompt side.
3. **Ordering.** The compact form sorts all 152 tools by name globally; the grouped form sorts by
   name only within a domain. `setAmbientLighting`, `setColor`, `setColorTemperature` and
   `setLighting` used to be adjacent lines the model could compare directly; now they are in two
   different blocks hundreds of lines apart. The 26-row collapse of
   `setColorTemperature → setAmbientLighting` and the 17-row rise of `setColor → setLighting` are
   both consistent with that, and it is the one of the three that is cheapest to test.

None of the three is separated by this flight, and separating them is not registered.

## 6. Deviations in force

1. **Quantization and runtime.** Q4_K_M GGUF on llama.cpp build `04ccc72a` instead of the release's
   bf16 checkpoint. Unchanged, and identical on both sides of the pairing, so it cannot bias the
   delta.
2. **The baseline is sealed bytes, not a re-flight.** Greedy decoding is not bitwise reproducible
   across batch shapes on this runtime, so ORG-1 is paired against the 2026-09-04 outputs rather
   than against a fresh compact-registry pass. The three parents flew at `-np 2` (tier 1, tiers
   3/4/6/7) and `-np 3` (tiers 2/5/8) while ORG-1 flew entirely at `-np 2`; that difference is
   inside the pairing for 1,500 of the 4,000 rows and is the one place where a batch-shape effect
   could hide. It cannot explain the sign: the 2,500 rows whose baseline flew at the SAME `-np 2`
   geometry move **−2.76 pp** on their own (tier 1 −2.00, tiers 3/4/6/7 −1.80 / −1.40 / −4.80 /
   −3.80, 500 rows each), and the 1,500 rows whose baseline flew at `-np 3` move −4.00 pp
   (tiers 2/5/8 −4.80 / −3.40 / −3.80). Both halves are negative and neither is small.
3. **Population.** The union of the three released populations, first successful speaker per query
   (tier 7 = first user turn). Unchanged, and identical on both sides.
4. **The four 654-second rows** are the release's synthesis defect and are kept, because the sealed
   baseline outputs they are paired against were produced on exactly these rows. They are 4 of 4,000.
5. **Constraints withheld.** `include_constraints=False`. The release's renderer can also emit a
   per-tool `Constraints:` line; it is not flown and is not authorized here.
6. **Serving geometry, seed and temperature.** `-c 49152 -np 2`, 24,576 tokens per slot, re-derived
   by the section 8.1 rule from this cell's own measured envelope; seed 20260803 and temperature 0,
   both inert under greedy decoding.

## 7. Throughput

| quantity | value |
|---|---:|
| contacts | 4,000 of 4,200 registered (4,008 planned) |
| speech audio | 23,418.083083 of 24,600 registered s |
| serving geometry | `-c 49152 -np 2`, 24,576 tokens per slot, `max_tokens` 256 |
| model load | 10.030 s |
| generation wall | 2,586 s (17:16:52Z → 17:59:58Z) |
| end-to-end wall (preflight to server stop) | 2,634 s |
| summed per-call latency | 2,150.742 s |
| mean per-call latency | 0.538 s |
| prompt tokens per call | 3,752.7 (baseline cells: 3,633 / 3,674.5 / 3,667.4) |
| completion tokens per call | 16.4 |
| parse failures | 26 of 4,000 |
| GPU `enforced.power.limit` before / after | 100.00 W / 100.00 W |

One attempt, COMPLETED and FINALIZED, zero aborted, zero orphans, no recovery re-registration used,
`study_repo_dirt` empty. The +85 prompt tokens per call against the sealed cells is the +87 the
prompt fit predicted, to within the roster's own speech-token mixture.

## 8. What this authorizes

Nothing new. The population is discovery data already exposed on 2026-09-04, no knob was tuned on
it, and this is not a superiority, generality or Stage-3 claim.

What it settles:

- **ORG-1 is dropped.** The pooled CI90 is entirely below zero on 4,000 paired rows with 323 harms
  against 194 saves. It does not become a component of any later mechanism.
- **The direct baseline is unchanged**, as the preregistration required of every outcome: the
  official-protocol cell stays the comparator every mechanism is paired against.
- **A2T-ORG-2 is registered against the official-protocol baseline**, not against ORG-1, and the
  domain cue is folded into its notes rather than tested again. The preregistration's NULL branch
  said this; the HARMFUL branch reaches the same place with one extra instruction, which is that
  ORG-2's contrast notes must target the SAME-domain twins — `rebootDevice` / `restartDevice`,
  `setSecurityMode` / `armSecuritySystem`, `getAirQuality` / `getAirQuality_diag`,
  `activateScene` / `activateRoutine` — because that is where 1,118 of the 1,673 misses now live and
  where 898 of them lived before ORG-1 ever flew.
- **The registry's structure is not the missing knowledge.** The model can be told which domain a
  tool belongs to and it will use the information; it still cannot tell two tools apart when their
  descriptions are semantically equivalent. That is a distinguishability problem, not an
  organization problem, and it is what the next mechanism has to attack.
- **One methodological caution is now measured rather than assumed**: a prompt-form change that
  supplies real, correct, release-authored knowledge can cost three points on this carrier. Any
  later ORG or SUPPLY mechanism that changes the shape of the registry block owes a same-shape
  control, because the form is worth as much as the content here.
