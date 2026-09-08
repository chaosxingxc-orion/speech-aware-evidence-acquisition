# OBS-E1 — the Earnings-21 transport unit as the speaker turn: REJECTED

**REJECTED (HARM), under section 6's rule exactly as written.** The cell moved corpus WER by
**+1.0487 points of improvement, CI90 [+0.9253, +1.1745]** — the largest clean corpus-WER movement
this carrier has produced — and moved its own headline metric, **ConEC-mirror PERSON entity WER, the
wrong way by 2.0912 points, CI90 [−3.1701, −1.0978]**. Section 6's HARM branch fires on
`CI90 UB(ΔPERSON) < 0`, and −1.0978 is below zero, so the cell is REJECTED with the failing half
named: **the transport unit buys general transcription and sells person names.**

| | |
|---|---|
| run | `SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1`, attempt `attempt-20260908T150858Z-c597a8` |
| comparator | `SAEA-E21-FULL44-DIRECT-BASELINE-V2`, attempt `attempt-20260904T233816Z-bcd338` |
| preregistration | `docs/readiness/2026-09-07-e21-obs-speaker-turn-units-v1-preregistration.md` (with its 2026-09-08 and 2026-09-08 (v2) addenda) |
| owner GO | 2026-09-07, umbrella Decision 4 |
| manifest | `COMPLETED`, `FINALIZED`, study commit `979a730e`, `study_repo_dirt` empty |
| identity | config `4e5549ee…`, protocol `39b7cc2c…` — both equal to the model-free seam-v2 wire check's own recorded values, checked BEFORE the first contact as a preregistered stop condition and re-read from the sealed manifest; split identity `fcc1b0bc…d69e`, the comparator's, unchanged |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-obs-e1-flight-v1/` |

**One attempt, no recovery re-registration.** The permitted recovery remains unspent. One launch was
refused before it opened an attempt — the first execution-plan file carried no `attempt_id`, and
`core.model.lifecycle` refused it with `FrozenCoreError` — so it spent zero contacts, zero audio and
zero GPU seconds, opened no attempt record and is not a recovery.

---

## 1. Contacts and delivered audio, per arm — and the confound, in the same table

| | comparator | cell |
|---|---:|---:|
| transport unit | fixed 90-second window | speaker-turn unit (hash-pinned v2 plan) |
| contacts (one pass) | **1,593** | **5,122** |
| mean unit seconds | 88.729 | **27.596** |
| cut audio seconds | 141,345.852687 | **141,345.852687** (identical to the digit) |
| delivered audio seconds | 141,345.852687 | **151,589.852687** (+5,122 × 2.0 s of tail) |
| realized GPU-hours | 0.9734 | **1.0657** |
| prompt tokens | 1,935,965 | **2,255,812** (+16.5 %) |
| completion tokens | 439,532 | **445,342** (+1.3 %) |

**The confound is stated here, in the same paragraph as the headline, exactly as section 5 requires.**
A contact-matched control is impossible by construction: a call cut at its speaker turns yields 5,122
pieces, and there is no way to cut it into speaker-turn units *and* into 1,593 of them. What this
cell contrasts is therefore the **transport unit as a whole**, and it confounds three things that
move together — boundary placement (11.0 % of unit cuts land mid-speech against 65.5 % of window
cuts), speaker purity (76.1 % single-speaker units against 40.5 %) and contact count/length (5,122 ×
27.60 s against 1,593 × 88.73 s). Neither the corpus-WER gain nor the PERSON regression can be
attributed to any one of the three by this cell alone. The control that would separate contact count
— a fixed-window arm at `obs_buffer_seconds` 27.60, **OBS-E1b** — is named as the follow-up and is
deliberately not registered here.

## 2. Two gates that ran before any score file was opened

**The identity anchor holds.** The comparator reproduces its own sealed numbers through this
verdict's instrument, to five decimals: corpus WER **8.19952** (sealed 8.1995), ConEC overall
**8.19952** (8.200), non-entity **4.73038** (4.730), PERSON **22.48886** (22.5), numeric-value
accuracy **90.73351** (90.7335), semantic high-impact **0.02780** (0.02780). Result **PASS**.

**Section 6's byte-level falsifier holds on 44 of 44 calls, zero failures.** For every one of the
5,122 units the emitted `SliceRecord` reproduced the pinned plan's span to 1e-6 s, `audio_seconds`
still equalled the CUT span (so the tail moved no boundary), `iteration = unit_index − 1`,
`preprocess` declared exactly one `tail-silence-2s`, the delivered byte count was the untailed cut
plus exactly 2.0 s of samples, those samples were digital silence, `sha256` matched the delivered
bytes and `pre_sha256` chained to the untailed cut; the OBS trace carried the unit's id, speaker and
end-cut. And per call, **concatenating the delivered unit slices with the 2.0-second tails removed
reproduced that call's committed `saea-diarization-v1` `audio_sha256` exactly** — 44 of 44. Totals
land on the plan's own figures: 5,122 units, 141,345.852687 s cut, 151,589.852687 s delivered.
Result **PASS**. Receipt: `flight/falsifier.json`.

## 3. The primary read — 44 clusters, one per call

`analysis.paired.resampled_statistic` on the pooled ratio, clustered by CALL, seed 20260903, 10,000
replicates, CI90. `improvement` is signed so that POSITIVE means the cell is better.

| metric | comparator | cell | improvement | CI90 | own-null half-width | ×hw |
|---|---:|---:|---:|---|---:|---:|
| **`asr-wer-whisper` corpus WER** | 8.19952 | **7.15078** | **+1.0487** | **[+0.9253, +1.1745]** | 0.05793 | **18.1** |
| `conec-entity-wer-official` overall | 8.19952 | 7.15078 | +1.0487 | [+0.9253, +1.1745] | 0.05793 | 18.1 |
| **ConEC PERSON** | 22.48886 | **24.58005** | **−2.0912** | **[−3.1701, −1.0978]** | 0.25009 | **8.4** |
| ConEC non-entity | 4.73038 | 4.71559 | +0.0148 | [−0.1014, +0.1397] | 0.06475 | 0.2 |
| ConEC ORG | 17.21293 | 16.70869 | +0.5042 | [−0.5743, +1.5750] | 0.35609 | 1.4 |
| `numeric-value-accuracy-v1` | 90.73351 | 90.92870 | +0.1952 | [−0.1084, +0.4832] | 0.15651 | 1.2 |
| `semantic-high-impact-error-rate-v1` | 0.02780 | 0.02696 | +0.0008 | [−0.0033, +0.0055] | 0.00148 *(advisory)* | 0.6 |
| ConEC GPE | 18.67274 | 19.58360 | −0.9109 | [−2.2808, +0.6740] | — | — |
| ConEC LOC | 2.47423 | 3.50515 | −1.0309 | [−2.2624, +0.0000] | — | — |
| ConEC PRODUCT | 19.23077 | 18.71795 | +0.5128 | [−1.9657, +3.0676] | — | — |
| ConEC EVENT | 2.42915 | 2.42915 | +0.0000 | [−0.5168, +0.4167] | — | — |
| ConEC NORP | 9.74576 | 10.16949 | −0.4237 | [−1.1070, +0.0000] | — | — |
| ConEC FAC | 21.31148 | 17.21311 | +4.0984 | [+1.0417, +8.4211] | — | — |

Equal-stratum (unweighted per-call mean) weighting tells the same story: corpus WER 8.00364 →
6.98931, PERSON 22.01318 → 24.75813.

**Saves / harms / ties at the paired grain (44 calls).** Corpus WER **43 saves / 1 harm / 0 ties**;
PERSON **10 saves / 27 harms / 7 ties**; ORG 23 / 17 / 4. The corpus-WER gain is not carried by a few
calls — it is on 43 of 44 — and the PERSON regression is not carried by a few either.

### 3.1 The decision, under section 6's rule as written

| clause | evaluated | result |
|---|---|---|
| **WIN** | `CI90 LB(ΔPERSON) > 0` AND `CI90 LB(ΔWER) > 0` | **false** — LB(ΔPERSON) = −3.1701 |
| **WIN (entity-only)** | `CI90 LB(ΔPERSON) > 0` AND `CI90 LB(ΔWER) > −0.30` | **false** — same reason |
| **NO EFFECT** | neither, and CI90 on both deltas contains 0 | **false** — neither interval contains 0 |
| **HARM** | `CI90 UB(ΔPERSON) < 0` OR `CI90 UB(ΔWER) < −0.30` | **TRUE** — UB(ΔPERSON) = **−1.0978 < 0** |

**Verdict: HARM. Label: REJECTED.** The failing half is **ConEC PERSON entity WER**, and section 6
requires the gap decomposed per stratum and per call: sections 4 and 5 below do that.

Corpus WER is not the failing half and is not close to it: its non-inferiority under section 6's own
−0.30-point margin is satisfied with room to spare (LB **+0.9253** > −0.30), and the movement is an
improvement of 18.1 own-null half-widths — disjoint from the Earnings-21 replicate null by two orders
of magnitude.

### 3.2 The guards, read against the Earnings-21 own-null half-widths

The margins are `SAEA-E21-FULL44-NULL-REPLICATE-V1`'s own call-clustered CI90 half-widths
(`docs/readiness/2026-09-08-e21-own-null-replicate-v1-verdict.md`), which replace the imported
Earnings-22 ±0.1524 for this carrier. "Non-inferior" means `CI90 LB(improvement) > −half-width`;
"disjoint" means the interval clears ±half-width entirely.

| guard | improvement | CI90 | half-width | non-inferior? | disjoint from the null? |
|---|---:|---|---:|---|---|
| corpus WER / ConEC overall | +1.0487 | [+0.9253, +1.1745] | 0.05793 | **yes** | **yes — a measured improvement** |
| **ConEC PERSON** | −2.0912 | [−3.1701, −1.0978] | 0.25009 | **NO** | **yes — a measured harm** |
| ConEC non-entity | +0.0148 | [−0.1014, +0.1397] | 0.06475 | **no** (LB −0.1014 < −0.06475) | no |
| ConEC ORG | +0.5042 | [−0.5743, +1.5750] | 0.35609 | **no** (LB −0.5743 < −0.35609) | no |
| numeric-value accuracy | +0.1952 | [−0.1084, +0.4832] | 0.15651 | **yes** | no |
| semantic high-impact rate | +0.0008 | [−0.0033, +0.0055] | 0.00148 **(advisory)** | no | no |

**Read this table honestly.** Only two metrics are separated from the replicate null at all: corpus
WER (an improvement) and PERSON (a harm). Non-entity and ORG fail non-inferiority *only because
their intervals are wider than the null half-width* — their point estimates are small improvements
and neither interval excludes zero, so the correct statement is *not resolved at this power*, not
*harmed*. Numeric-value accuracy is non-inferior and its point estimate is a small improvement. The
semantic high-impact guard is **advisory by construction**: the own-null verdict measured that
metric moving +0.00222 with a CI90 that EXCLUDES ZERO under a null where nothing changed, so it
cannot carry a "does not rise" clause; the direction here is a slight improvement (97 high-impact
reference words against the comparator's 100).

## 4. Strata — every one reported, natural mixture and equal-stratum

**The paired strata are at the paired grain (the call), because that is the only grain at which both
arms produce a complete comparable quantity.** The tertile splits are on plan-derived features fixed
model-free before any score existed (`verdict/result-summary.json` carries the full tables).

**Sector (the release's own stratum, 9 levels).** Corpus WER improves in **every** sector, from
+0.757 (Technology) to +1.270 (Utilities). PERSON regresses in **7 of 9** — Technology −5.814,
Consumer Goods −4.202, Services −3.960, Conglomerate −3.665, Financial −3.559, Industrial Goods
−2.551, Basic Materials −0.915 — and improves in two, Utilities +2.362 and Healthcare +0.320.

**Sample rate (the release's own second stratum, 5 levels).** Corpus WER improves at every rate
(+0.951 to +1.293). PERSON is exactly **0.0000** at 16 kHz (6 calls) and 22.05 kHz (5 calls) and
regresses at 11.025 kHz (−2.655), 24 kHz (−2.690) and 44.1 kHz (−2.507).

**Dominance (the primary stratum), by the call's share of `dominated` units.** HIGH tertile corpus
WER +1.213 with PERSON −3.326; MID +0.990 / −1.306; LOW +0.974 / −1.689. **The purer the call's
units, the larger the corpus-WER gain — and, in the top tertile, the larger the PERSON loss.**

**Mean unit seconds.** HIGH +1.245 / PERSON −2.998; MID +1.088 / −2.172; LOW +0.797 / −1.134.
**Longer units help corpus WER more and hurt PERSON more** — which is the opposite of a "shorter
units lose context" story and is worth naming.

**Pause-cut share.** HIGH +1.276 / −2.690; MID +0.975 / −2.759; LOW +0.835 / −0.485.

**Units per call.** HIGH +1.098 / −1.520; MID +0.977 / −1.327; LOW +1.060 / **−4.865**.

**The unit-grain strata (section 4's own table) have no comparator counterpart — the comparator has
no units — so they are reported as the CELL's own distribution, never as a contrast.** Per-unit rows
come from `analysis.e21_window_pairing` through the registered instrument (5,122 rows, 44 calls,
25,726 errors over 359,765 reference words):

| stratum | units | reference words | WER, natural mixture | WER, equal-stratum |
|---|---:|---:|---:|---:|
| dominance `dominated` | 4,916 | 357,857 | 7.077 | 10.677 |
| dominance `shared` | 147 | 1,638 | **19.658** | 35.356 |
| dominance `silent` | 59 | 270 | **28.889** | 22.822 |
| speakers = 1 | 3,898 | 307,602 | 6.822 | 9.977 |
| speakers = 2 | 1,126 | 50,483 | 8.894 | 15.967 |
| speakers ≥ 3 | 39 | 1,410 | 12.340 | 19.674 |
| speakers = 0 | 59 | 270 | 28.889 | 22.822 |
| length `<1 s` | **0** | 0 | — | — |
| length 1–10 s | 2,006 | 20,980 | **12.560** | 17.463 |
| length 10–60 s | 2,284 | 181,746 | 7.234 | 8.146 |
| length ≥60 s | 832 | 157,039 | **6.332** | 6.505 |
| cut `pause` | 4,387 | 335,985 | 7.088 | 10.912 |
| cut `turn-boundary` | 676 | 19,495 | **8.602** | 15.413 |
| cut `forced-cap-split` | 15 | 3,115 | 4.687 | 4.749 |
| cut `call-end` | 44 | 1,170 | 7.521 | 9.672 |

**The two properties the preregistration told us to check are checked.** Zero of the 5,122 units are
under 1.0 s (v1's own 166 short-kept slivers are gone, as plan v2 intended), and exactly **one** unit
is attributed no reference word at all — reported here as its own stratum, contributing nothing to
any rate.

## 5. The no-pause call `4366522`, reported apart and never pooled away

Zero pauses of ≥300 ms over 1,817.7 s, so every one of its 36 units ends on an active frame: 22
turn-boundary cuts, 13 forced-cap splits, 1 call-end, mean unit 50.49 s, all 36 `dominated`.
Corpus WER **7.2277 → 5.8695, improvement +1.358** — better than the corpus average. PERSON
**11.111 → 22.222, improvement −11.111** over 27 reference words; ORG **42.708 → 32.292,
improvement +10.417**; numeric accuracy 89.286 → 88.571 (−0.714); non-entity 2.324 → 2.439 (−0.115).
On the one call where the transport unit can buy **no** silent boundary at all, corpus WER still
improves — which says the corpus-WER gain is not mainly a boundary-silence effect.

## 6. The preregistered secondary read — 1,593 rows on a common refinement

Section 4 preregisters exactly one secondary read, and this is it: **both arms' alignment operations
charged to the SEALED 90-second window grid by REFERENCE index** rather than by hypothesis index.
It buys a saves / harms / ties count and the per-window strata; **it does not buy power**, and
clustering by call it returns arithmetically the same interval as the primary. Operations are
conserved (comparator 29,499 errors, cell 25,726, both over 359,765 reference words).

* corpus WER 8.19952 → 7.15078, improvement **+1.0487 [+0.9253, +1.1745]** — identical to the primary.
* PERSON 22.48886 → 24.58005, **−2.0912 [−3.1701, −1.0978]** — identical to the primary.
* ORG 17.21293 → 16.70869, +0.5042 [−0.5743, +1.5750].
* **Saves / harms / ties: 1,085 / 326 / 177** over the 1,588 windows that carry reference words.

Per-window strata, by the composition of the plan units that overlap each sealed window:

| stratum | windows | comparator | cell | improvement | CI90 | saves / harms / ties |
|---|---:|---:|---:|---:|---|---|
| all-dominated | 1,461 | 8.0251 | 6.9210 | +1.1041 | [+0.9754, +1.2337] | 1,019 / 279 / 163 |
| any-shared | 127 | 10.1420 | 9.7102 | +0.4319 | [+0.1256, +0.7476] | 66 / 47 / 14 |
| longest unit ≥60 s | 1,158 | 8.0573 | 6.9840 | +1.0733 | [+0.9495, +1.2036] | 825 / 215 / 118 |
| longest unit 10–60 s | 429 | 8.5820 | 7.6039 | +0.9781 | [+0.7020, +1.3186] | 259 / 111 / 59 |
| 2–4 units per window | 1,091 | 7.6679 | 6.5080 | +1.1598 | [+1.0407, +1.2855] | 794 / 176 / 121 |
| ≥5 units per window | 495 | 9.3277 | 8.5201 | +0.8076 | [+0.5709, +1.0741] | 289 / 150 / 56 |

The two single-unit windows and the one all-under-10-s window are reported in the receipt and are too
small to read.

## 7. What flew, and what it cost

| | |
|---|---:|
| contacts | **5,122** of 5,635 planned, 6,000 registered |
| metered speech seconds | **141,345.8527** (the CUT span; the 2.0-second tails are delivered but not metered) of 167,000 planned, 170,000 registered |
| GPU hours | **1.0657** (3,836.49 GPU-seconds) of 3.4 planned, 4.0 registered |
| paid API spend | **0** |
| wall | 5,964 s = 99.4 min |
| throughput | **51.529 units per minute** (comparator 16.38 windows/min) |
| realized realtime factor | **36.84×** (metered cut audio / nvidia-smi busy seconds) |
| peak VRAM | 22,722 MiB (comparator 22,720) |
| gate setup | 12.08 s |
| CPU seconds | 412.45 |
| saturated units | **3** of 5,122 (`4346923#u0115`, `4389907#u0062`, `4397800#u0084`); skipped **0** |
| prompt tokens per unit | min **101** / p25 153 / median **309** / p75 673 / p99 1,232 / max **1,258** |
| worst-request slot margin | **4.88×** against the 6,144-token slot |

**The GPU projection was pessimistic and the honest bracket was the audio-proportional one.** Section
7 bracketed the cost between 1.044 GPU-h (audio-proportional) and 3.130 (contact-proportional) and
planned 3.4. The realized 1.0657 lands 2 % above the audio-proportional FLOOR, so on this carrier and
geometry the cost tracks **encoded seconds**, not requests — 5,122 contacts cost only 9.5 % more GPU
than the comparator's 1,593, because each is a third as long. The contact-proportional ceiling
over-predicted by 2.9×; a future Earnings cell that changes only the transport unit should bracket
from the audio side.

**Serving.** The flight **attached** to the coordinator's resident session
`e21-np6-c36864-20260908` (receipt sha256 `de3ff630…e7fc`) at that session's own
geometry `-c 36864 -np 6`, 6 slots × 6,144 tokens, port 8080 on loopback; it started no server and
stopped none, and `scripts/run_arm_sequence.sh` was deliberately not used.

**Monitor summary over the attempt's own contact window** (15:09:05Z → 16:48:29Z, 538 samples): wall
5,951.45 s, active **4,858.54 s (81.6 %)**, parked 1,092.91 s (18.4 %), 2,435 requests observed at
the 10-second sampling interval, mean **71.88 W**, peak 104.34 W, mean utilization **61.85 %**, host
free memory bottoming at **7.48 GB** and the VM working set peaking at **43.25 GB**. The host-memory
floor was crossed during the flight and nothing was killed, but it is recorded rather than smoothed:
a heavier co-tenant during a run of this shape would be at risk.

## 8. What this cell decides, and what it does not

**It decides one thing: the v2 speaker-turn transport unit is REJECTED for Earnings-21 under its own
preregistered rule**, because the metric it was aimed at moved decisively the wrong way. That is the
whole verdict.

**It is not a paper-facing effectiveness claim, in either direction.** n = 44 clusters is below the
program's `n >= 400` rule; this is discovery data; the interval and the direction are the deliverable.
No superiority, generality, published-comparison or Stage-3 claim is made, and the corpus-WER gain in
particular is **not** admissible as an Earnings-21 improvement claim on this evidence — it is a
direction worth decomposing, on a confounded contrast, at n = 44.

**Three things this cell surfaced that the next one should use.**

1. **The corpus-WER and PERSON effects have opposite signs and comparable magnitude.** Whatever the
   transport unit does, it is not a uniform quality change. A mechanism that keeps the corpus-WER
   half without the PERSON half is a real object to look for, and the strata say where: the gain is
   largest on pure, long-unit, high-pause-share calls, and the PERSON loss is largest on exactly the
   same calls. The two may share a cause.
2. **The named follow-up, OBS-E1b, is now worth its pass.** A fixed-window arm at
   `obs_buffer_seconds` 27.60 delivers 5,122 windows on the same calls — contact-count and
   mean-length matched, boundary-placement and purity unmatched. It is the one arm that separates
   factor 3 from factors 1 and 2, and this cell has produced a direction worth decomposing. It is
   still not registered here: one experiment in flight.
3. **Cost brackets from the audio side on this carrier.** See section 7.

## 9. Claim surface

Discovery data. No superiority, generality, published-comparison or Stage-3 claim; **no paper-facing
effectiveness claim at all** (n = 44 clusters, section 4 of the preregistration). No knob was tuned on
the evaluation ten — the plan's rules were fixed model-free before any score existed, and the tertile
splits in section 4 are on plan-derived features, not on scores. No Earnings-22 contact, no fstalign
install, no diarizer re-run, no speaker naming, no OBS-E1b contact-matched control. The
`paper-scale-confirmatory` profile is not available to this repository and was not requested.
