# A2T KC-A1 contrast notes and KC-A1c, their form twin, v1 — verdict

Two runs flown 2026-09-06, profile `baseline-reproduction`, one cell each, sequentially, one experiment in
flight, under the 2026-09-06 owner ruling that made the form twin unconditional.

| Run id | Cell | Attempt | Study commit | Rows | Manifest SHA-256 |
|---|---|---|---|---:|---|
| `SAEA-A2T-KC-A1-CONTRAST-NOTES-V1` | `KC-A1-contrast-raw` | `attempt-20260906T150235Z-kca1contrastraw` | `99af3c74` | 4,000 | `6ee19b383f14557305a74a0c7f2e245ccc9fe9a64d54d38ad659b73dc349fd10` |
| `SAEA-A2T-KC-A1C-CATEGORY-ONLY-V1` | `KC-A1c-category-raw` | `attempt-20260906T164643Z-kca1ccategoryraw` | `9c803ef9` | 4,000 | `eb8660b15db5217dd5e72616d75a3920cf516837330fbae475e8fdf053684ada` |

Preregistration: `docs/readiness/2026-09-05-a2t-kc-a1-contrast-notes-v1-preregistration.md` (owner ruling
verbatim in its section 3.3, the three-way decomposition in its section 6).
Full numbers: `docs/checks/speech-aware-evidence-acquisition/2026-09-05-a2t-kc-a1-contrast-notes-4000-v1/result-summary.json`
(SHA-256 `ba43798bc74c3686f8c49fadbd92146fbe895660ddfabe084a7efecb4b319515`).
Wiring proofs: `.../wire-check/wire-check-kc-a1.json` (SHA-256 `67821be75d3a085426b1f1bc9f55baeec01628ce2aabf5518760e49ff7c84261`)
and `.../wire-check/wire-check-kc-a1c.json` (SHA-256 `9eaf4145491cbaf12b83bcf398477aa787566c3a622f694a98c711c4226687ef`),
4,000 contact-free requests each, zero model contacts, zero servers.
Paper-facing scorer: `a2t-toolcall-official` — the pinned release's own `metrics.py`, git blob
`d98277bcf69795c9a0ae54e538c170abfd8c51ca`, commit `b9d5383ca30945fbafb965a04bea40117e1e8a82`.

## Verdict: NULL, and the form twin is the reason the null is worth reading

Pooled official tool accuracy over the same 4,000 rows, each paired against its own sealed
official-protocol output, tier-stratified bootstrap, 10,000 replicates, seed 20260903:

| contrast | definition | delta | CI90 | saves / harms / ties | sign p |
|---|---|---:|---|---|---:|
| **total** | KC-A1 − sealed baseline | **+0.42 pp** | **[−0.12, +0.97]** | 101 / 84 / 3,815 | 0.2394 |
| **form** | KC-A1c − sealed baseline | **+0.25 pp** | **[−0.30, +0.80]** | 94 / 84 / 3,822 | 0.5001 |
| **content** | KC-A1 − KC-A1c, paired | **+0.17 pp** | **[−0.38, +0.70]** | 86 / 79 / 3,835 | 0.6406 |

Baseline 61.40 % → KC-A1 61.825 % → and KC-A1c 61.65 % sits between them. Under equal-domain weighting the
picture is unchanged and unchanged in sign: 68.11 → 68.40 (**+0.29 pp**, CI90 [−0.34, +0.93]) for KC-A1 and
68.11 → 68.26 (**+0.15 pp**, CI90 [−0.48, +0.77]) for KC-A1c.

The preregistered rule reads **NULL** for KC-A1: the pooled CI90 includes 0. It fails the second ADMITTED
clause independently — the target-pair share of the gain is **0.198** against a required 0.5, so four
corrected rows in five were not even confusions between two tools inside one MF-1 target. The content
contrast's CI90 lower bound is below 0, so **no part of the movement is credited as content**
(`content_effect_credited: false`).

Three things this pair establishes that ORG-1 could not, and they are worth more than the sign:

1. **The 3-point form cost of ORG-1 was structure, not text volume.** ORG-1 lost 3.23 pp and this verdict's
   predecessor named "prompt length and shape" as the leading suspect. KC-A1c is the controlled test of the
   volume half alone: 44 added text tokens in the same eight lines of the same 152-line block, carrying no
   contrast. It costs **+0.25 pp, not −3**. Whatever cost ORG-1 three points was its 465 lines against 155,
   its `## DOMAIN` headers and its re-ordering — not the extra tokens. A same-shape append is close to free
   on this carrier, which is a reusable fact about the next mechanism's budget.
2. **The contrast content does fire on exactly the confusions it was built for, and the firing does not
   reach the metric.** On the named cross-domain lighting pairs the treatment moves roughly twice as hard as
   its form twin (table in section 3), and it still buys +0.17 pp of nothing.
3. **The reason is ORG-1's reason, one layer down.** Cross-domain twin misses fall 621 → 535 under KC-A1
   (−86) while same-domain twin misses rise 898 → 967 (+69). The notes push the model out of the wrong
   domain and into the wrong neighbour inside the right one. That is the same substitution channel ORG-1
   found with a domain header, reproduced by eight inline contrast notes at a quarter of the prompt cost.

## 1. Per tier, with the published column beside every tier

Official tool accuracy (%), n = 500 per tier, paired. The paper column is a ceiling reference and no gate is
set relative to it.

| tier | baseline | KC-A1 | delta | KC-A1c | delta | paper | KC-A1 vs paper |
|---|---:|---:|---:|---:|---:|---:|---:|
| tier1_direct | 65.60 | 67.20 | **+1.60** | 67.00 | +1.40 | 92.4 | −25.20 |
| tier2_parametric | 79.60 | 79.60 | 0.00 | 78.20 | −1.40 | 84.6 | −5.00 |
| tier3_multi_intent | 65.00 | 65.60 | +0.60 | 65.20 | +0.20 | 74.7 | −9.10 |
| tier4_implicit | 28.20 | 28.00 | −0.20 | 28.00 | −0.20 | 33.4 | −5.40 |
| tier5_needle | 80.80 | 81.20 | +0.40 | 81.40 | +0.60 | 90.6 | −9.40 |
| tier6_correction | 75.80 | 77.20 | **+1.40** | 76.40 | +0.60 | 81.5 | −4.30 |
| tier7_multiturn | 49.40 | 48.60 | −0.80 | 48.80 | −0.60 | 54.6 | −6.00 |
| tier8_intent_blending | 46.80 | 47.20 | +0.40 | 48.20 | **+1.40** | 41.7 | **+5.50** |
| **pooled, n = 4,000** | **61.40** | **61.82** | **+0.42** | **61.65** | **+0.25** | — | — |

Saves and harms per tier for KC-A1: 16/8, 12/12, 17/14, 11/12, 7/5, 15/8, 10/14, 13/11.

**Read the tier-1 row against the tier-1 row of the twin, not against the baseline.** KC-A1 is +1.60 there and
KC-A1c is +1.40; the difference is 0.20 pp on 500 rows, which is nothing. Tier 1 is the tier the lighting
cluster is densest in and the tier a contrast note should help most, and almost all of what happens there
happens to the control too. The same is true in reverse on tier 8, where the *control* gains 1.40 and the
treatment 0.40. Neither is a content effect; both are the noise of moving 44 tokens through a frozen core.

Tier 8 remains the one Audio2Tool tier this repository has ever landed above the published row (+5.50 for
KC-A1, +6.50 for KC-A1c against 41.7), and unlike ORG-1 neither arm spends that margin.

## 2. Per domain, under both weightings

| domain | n | baseline | KC-A1 | delta | KC-A1c | delta |
|---|---:|---:|---:|---:|---:|---:|
| `smart_home` | 2,792 | 54.98 | 55.55 | **+0.57** | 55.37 | +0.39 |
| `wearables` | 857 | 78.41 | 78.41 | **0.00** | 78.18 | −0.23 |
| `smart_car` | 351 | 70.94 | 71.23 | +0.28 | 71.23 | +0.28 |
| natural mixture | 4,000 | 61.40 | 61.82 | +0.42 | 61.65 | +0.25 |
| **equal-domain** | 4,000 | **68.11** | **68.40** | **+0.29** | **68.26** | **+0.15** |

Saves/harms by domain for KC-A1: `smart_home` 85/69, `wearables` 10/10, `smart_car` 6/5.

The `wearables` row is the cleanest negative control in the run and it behaves. Seven of the eight
manipulated tools are `smart_home` and one is `smart_car`; no lighting note touches a wearables tool, and
`wearables` moves exactly 0.00 pp under the treatment with ten saves against ten harms. ORG-1, by contrast,
lost 3.38 pp on that same untouched domain — which is precisely the evidence that ORG-1's loss was a
whole-prompt effect and KC-A1's manipulation is local, as designed.

**Per tier × domain is not reported.** Preregistration section 6 lists it among the mandatory slices, and
the registered N-arm analysis (`scripts/a2t_org1_domain_grouped_analysis.py`, schema
`saea-a2t-paired-arms-result-summary-v2`) does not emit it; the single-arm ORG-1 schema did. Rather than
compute a headline slice outside the registered path, the gap is declared here. Nothing in the decision rule
depends on it, and the flight brief's own reporting list does not ask for it.

## 3. The lighting pairs, before and after — where the content is visible

Named confusion pairs over all 4,000 rows, resolved from `tools_registry.csv`. The lighting-cluster rows are
the ones KC-A1 manipulates; every other row is unmanipulated and is reported as the within-run control it is.

| gold | predicted | class | baseline | KC-A1 | delta | KC-A1c | delta |
|---|---|---|---:|---:|---:|---:|---:|
| `setColorTemperature` | `setAmbientLighting` | cross-domain | 35 | **14** | **−21** | 28 | −7 |
| `setColor` | `setAmbientLighting` | cross-domain | 25 | **10** | **−15** | 16 | −9 |
| `setLighting` | `setAmbientLighting` | cross-domain | 28 | **20** | **−8** | 23 | −5 |
| `setLighting` | `setLightState` | same-domain | 33 | 34 | +1 | 26 | −7 |
| `setColor` | `setLighting` | same-domain | 15 | **31** | **+16** | 21 | +6 |
| `setGroupLightState` | `setLighting` | same-domain | 15 | **23** | **+8** | 20 | +5 |
| `setSecurityMode` | `armSecuritySystem` | same-domain | 64 | 65 | +1 | 72 | +8 |
| `rebootDevice` | `restartDevice` | same-domain | 41 | 32 | −9 | 32 | −9 |
| `findMyDevice` | `findPairedPhone` | cross-domain | 25 | 24 | −1 | 23 | −2 |
| `getApplianceState` | `getApplianceStatus` | same-domain | 25 | 26 | +1 | 25 | 0 |
| `setGarageDoor` | `setGarageOpener` | cross-domain | 22 | 21 | −1 | 22 | 0 |
| `setFanMode` | `setFanSpeed` | cross-domain | 21 | 24 | +3 | 21 | 0 |
| `setVolume` | `adjustVolume` | cross-domain | 18 | 20 | +2 | 19 | +1 |
| `getNetworkHealth` | `runNetworkSpeedTest` | same-domain | 16 | 13 | −3 | 16 | 0 |
| `activateScene` | `activateRoutine` | same-domain | 12 | 15 | +3 | 16 | +4 |
| `getAirQuality` | `getAirQuality_diag` | same-domain | 11 | 12 | +1 | 9 | −2 |
| `setLockState` | `setLockState_home` | cross-domain | 9 | 8 | −1 | 8 | 0 |
| `getBiometricData` | `startWorkout` | same-domain | 4 | 4 | 0 | 4 | 0 |

**The three `→ setAmbientLighting` rows are the manipulation working.** Summed, they go 88 → 44 under KC-A1,
a 50 % collapse, against 88 → 67 under the form twin. `setAmbientLighting` is the one lighting tool in
`smart_car`, and its note says exactly that: `; smart_car cabin only`. Half of that collapse survives the
control, and half does not — the surviving half is the clearest content signal in the flight.

**And the two `→ setLighting` rows are where it goes.** `setColor → setLighting` 15 → 31 and
`setGroupLightState → setLighting` 15 → 23: +24 rows between them, against +11 for the control. The rows
rescued from the `smart_car` lighting tool land on the wrong `smart_home` lighting tool instead. The notes
that were supposed to separate them (`; smart_home hsb only`, `; a group, not one light`, `; one light, not
a group`) do not.

Net over the six lighting rows: −44 cross-domain, +25 same-domain for KC-A1. That is the whole cell in two
numbers.

## 4. Where the misses went, and the MF-1 target mass

Miss classes over all 4,000 rows:

| class | baseline | KC-A1 | delta | KC-A1c | delta |
|---|---:|---:|---:|---:|---:|
| correct | 2,456 | 2,473 | **+17** | 2,466 | +10 |
| cross-domain twin | 621 | **535** | **−86** | 607 | −14 |
| same-domain twin | 898 | **967** | **+69** | 903 | +5 |
| invented a name | 16 | 17 | +1 | 19 | +3 |
| produced no call at all | 9 | 8 | −1 | 5 | −4 |

The gain decomposition, preregistered:

| quantity | KC-A1 | KC-A1c |
|---|---:|---:|
| rows corrected | 101 | 94 |
| of which the baseline miss was a cross-domain twin | 37 | 31 |
| of which the baseline miss was a same-domain twin | 60 | 61 |
| rows broken | 84 | 84 |
| of which the new miss is a same-domain twin | 53 | 44 |
| of which the new miss is a cross-domain twin | 30 | 37 |
| net | **+17** | **+10** |
| cross-domain share of the gain | 0.366 | 0.330 |
| **MF-1 target-pair share of the gain** | **0.198** | 0.234 |

The five MF-1 targets' own miss mass, with the four unflown targets as the within-run negative control the
preregistration's section 3 promised:

| target | in the cell | baseline | KC-A1 | delta | KC-A1c | delta |
|---|---|---:|---:|---:|---:|---:|
| **lighting** | **yes** | **186** | **178** | **−8** | 175 | −11 |
| activateRoutine | no | 48 | 43 | −5 | 40 | −8 |
| calibrateCameras | no | 16 | 17 | +1 | 16 | 0 |
| getBiometricData | no | 23 | 22 | −1 | 22 | −1 |
| castContent | no | 5 | 5 | 0 | 5 | 0 |
| **all five** | | **278** | **265** | **−13** | 258 | −20 |

**This table is the honest centre of the verdict and it does not flatter the cell.** The manipulated cluster
loses 8 rows of miss mass under the treatment and **11 under the control that says nothing about lighting**.
The four unmanipulated targets move by −5 and −8 respectively, on notes that do not exist. At the level of
target mass, the contrast content is indistinguishable from 44 tokens of filler, and the movement in both
arms is the size of the movement in tools nobody touched. The named-pair table of section 3 shows the
content doing real, specific work on three confusions; this table shows that work not summing to anything a
mass count can see.

## 5. The secondary metrics, each as a paired delta

Same 4,000 rows, same pairing, same bootstrap.

| metric | baseline | KC-A1 | delta | CI90 | KC-A1c | delta | CI90 |
|---|---:|---:|---:|---|---:|---:|---|
| official exact match | 18.350 | 18.825 | **+0.475** | **[+0.100, +0.850]** | 18.400 | +0.050 | [−0.325, +0.425] |
| official parameter F1 (macro) | 29.280 | 30.144 | **+0.864** | **[+0.422, +1.298]** | 29.687 | +0.407 | [−0.013, +0.833] |
| parse rate | 99.775 | 99.800 | +0.025 | [−0.100, +0.150] | 99.875 | +0.100 | [+0.000, +0.200] |
| `a2t-toolcall-v2` ordered tool accuracy | 52.450 | 53.300 | **+0.850** | **[+0.250, +1.475]** | 52.550 | +0.100 | [−0.475, +0.675] |
| `a2t-toolcall-v2` exact match | 14.350 | 14.725 | +0.375 | [+0.000, +0.750] | 14.475 | +0.125 | [−0.225, +0.475] |

Parameter F1 micro-pooled: 24.396 → 24.961 (KC-A1) and → 24.643 (KC-A1c). Rows naming more than one call:
486 → 519 → 488.

**This is the one place the treatment separates from its twin.** Three of KC-A1's five secondary CI90s
exclude zero and none of KC-A1c's do. It is a real asymmetry and it is reported, not promoted: the
preregistration fixed the primary before takeoff as pooled official tool accuracy, these are secondary
metrics on the same rows and therefore not independent evidence, and no decision rule in this study is
stated on them. What they suggest — that the notes improve the *arguments* of a call more reliably than they
improve the *choice* of tool — is a hypothesis for a later cell, not a finding of this one.

There is no ORG-1-style parse damage in either arm: 9 unparsed baseline rows become 8 and 5. ORG-1 turned
them into 26.

## 6. Deviations in force

1. **Quantization and runtime.** Q4_K_M GGUF on llama.cpp build `04ccc72a` instead of the release's bf16
   checkpoint. Identical on both sides of every pairing, so it cannot bias a delta.
2. **The baseline is sealed bytes, not a re-flight.** Greedy decoding is not bitwise reproducible across
   batch shapes on this runtime, so both arms are paired against the 2026-09-04 outputs. 1,500 of the 4,000
   baseline rows flew at `-np 3` and the rest at `-np 2`; both arms here flew entirely at `-np 2`. The
   arm-versus-arm contrast — the content effect, the one this cell was designed to isolate — is free of that
   asymmetry entirely, because both its sides flew at the same geometry on the same day.
3. **The four 654-second rows** are the release's synthesis defect and are kept, because the sealed outputs
   they are paired against were produced on exactly those rows.
4. **No separate 4-row smoke was flown.** ORG-1 flew one (`SAEA-A2T-ORG1-DOMAIN-GROUPED-SMOKE-V1`); the
   flight brief's final sequence and preregistration section 8.4 both go wire check → exposure rows →
   flight. The wire check exercised all 4,000 requests contact-free through the real client, adapter and
   payload binding and then sealed and scored them, and the token-match row had already made live server
   contact at this exact geometry with these exact system messages. Recorded as a deliberate departure from
   the predecessor's sequence, decided before the first contact and not after a failure.
5. **The KC-A1c wire check was overlapped onto the KC-A1 flight and its first attempt failed on the D3
   gate.** A foreign process wrote `__pycache__` under the frozen scoring package at 15:26:45Z, mid-flight,
   without `PYTHONDONTWRITEBYTECODE`; the scoring freeze binds source bytes and refused it. That is the gate
   working, not a defect of either cell. Purging the bytecode fixed it and, more importantly, fixed the
   KC-A1 flight's own scoring stage, which would have hit the same gate twenty minutes later. The wire check
   was re-run alone and came back `seal_and_score: OK`. The overlap also cost throughput (section 7); it is
   not repeated for the twin.
6. **Serving geometry, seed and temperature.** `-c 49152 -np 2`, 24,576 tokens per slot, `max_tokens` 256,
   seed 20260803 and temperature 0, both inert under greedy decoding. Identical in both arms.
7. **Per tier × domain is not reported** (section 2), a declared reporting gap in the registered N-arm
   analysis rather than a decision-relevant omission.

## 7. Throughput

| quantity | KC-A1 | KC-A1c |
|---|---:|---:|
| contacts | 4,000 of 4,200 registered (4,008 planned) | 4,000 of 4,200 registered |
| speech audio | 23,418.083083 of 24,600 registered s | 23,418.083083 of 24,600 s |
| serving geometry | `-c 49152 -np 2`, 24,576 tokens per slot | identical |
| model load | 10.037 s | 15.034 s |
| generation wall | 3,970 s (15:04:30Z → 16:10:40Z) | 2,803 s (16:48:27Z → 17:35:10Z) |
| summed per-call latency | 2,257.268 s | 2,113.302 s |
| mean per-call latency | 0.564 s | 0.528 s |
| **prompt tokens per call** | **3,709.74825** | **3,709.74825** |
| completion tokens per call | 16.577 | 16.153 |
| parse failures | 8 of 4,000 | 5 of 4,000 |
| GPU `enforced.power.limit` before / after | 100.00 W / 100.00 W | 100.00 W / 100.00 W |

Both attempts COMPLETED and FINALIZED, zero aborted, zero orphans, **no recovery re-registration used on
either run id**, `study_repo_dirt` empty on both.

**The prompt-token row is the token match, realized.** 3,709.74825 prompt tokens per call in both arms,
identical to five decimal places over 14,838,993 tokens each, against the sealed baseline cells' 3,633 /
3,674.5 / 3,667.4. The +44 the token-match row measured offline arrived on the wire, and it arrived equally
in both arms. A character-matched control would have been 14 tokens cheaper per rendering; this one is zero
tokens cheaper, which is the only condition under which "KC-A1 minus KC-A1c" means what section 6 of the
preregistration says it means.

KC-A1's generation ran 3,970 s against KC-A1c's 2,803 s on the same roster and geometry because the KC-A1c
wire check was deliberately overlapped onto its first 46 minutes and competed for CPU; the rate recovered to
the predecessor's 1.45 calls/s once the wire check finished. It cost wall time and nothing else.

## 8. What this authorizes

Nothing new. The population is discovery data already exposed on 2026-09-04 and 2026-09-05, no knob was
tuned on it, and this is not a superiority, generality or Stage-3 claim.

What it settles:

- **KC-A1 is NULL and is not admitted.** The pooled CI90 includes zero, the target-pair share of the gain is
  0.198 against a required 0.5, and the content contrast does not clear zero. Program section 4a routes a
  NULL with separability ≥ 0.80 to **EVO-A1 from the official baseline**, which is where this goes.
- **The direct baseline is unchanged**, as the preregistration required of every outcome.
- **A same-shape token append is nearly free on this carrier: +0.25 pp, CI90 [−0.30, +0.80].** This is the
  first *measured* form cost in the study, and it retires the working assumption that ORG-1's three points
  were partly a length tax. They were not. Any future ORG or SUPPLY mechanism that keeps the 152-line shape
  and appends can budget tokens against a measured zero rather than against a cap; one that changes the
  block's structure still owes its own twin, because the thing that cost three points was structure.
- **The form twin earns its place in the protocol.** With ORG-1's design this flight would have reported
  "+0.42 pp, promising"; with the twin it reports "+0.17 pp of content, indistinguishable from zero". The
  2026-09-06 ruling that made the control unconditional is what turned an ambiguous null into an
  attributable one, and it should stay unconditional.
- **A deterministic per-tool contrast note is not the lever, and the reason is specific.** It removes the
  cross-domain confusion it names — the three `→ setAmbientLighting` rows halve — and the rows it frees land
  on the nearest same-domain neighbour instead, exactly as ORG-1's domain header did. Distinguishing two
  tools *inside* one domain is the unsolved problem on this carrier, and eight hand-derived notes built only
  from registry columns do not solve it. That is the constraint EVO-A1 inherits: a rewrite that separates
  `setColor` from `setLighting` and `setGroupLightState` from `setLighting` is worth more than any number of
  notes that separate either from `setAmbientLighting`.
