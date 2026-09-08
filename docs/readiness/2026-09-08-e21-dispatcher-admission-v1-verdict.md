# Verdict — the cross-call dispatcher is NEUTRAL on Earnings-21, and it buys 17 % of throughput

**STATUS: NEUTRAL — ADMITTED TO THE DEFAULT PLAN AS A NO-HARM MODULE.** Not a gain on any
quality metric, and none was claimed: `obs_prefetch_depth` is a scheduler. Every gating metric's
paired delta against the sealed comparator lies inside this carrier's own measured replicate
margin, no gating CI90 excludes zero on the harmful side, and the two pairings agree. The module
delivers **+16.96 % windows per minute against the depth-0 arm on the same server**, cutting the
zero-slot share from 17.55 % to 3.75 % and the number of idle stretches from 43 to 10.

Run `SAEA-E21-FULL44-DISPATCH-ADMISSION-V1`, attempt `attempt-20260908T191537Z-ba0a08`,
`COMPLETED` and `FINALIZED` on study commit `a58a27e8`, **1,593 of 1,593 windows over all 44
calls**, one attempt, none aborted, **no recovery re-registration used**, `study_repo_dirt` empty.
The cell of `docs/readiness/2026-09-08-e21-dispatcher-admission-v1-preregistration.md`, flown on
the owner rule of 2026-09-08 — *every harness module shows gain or no harm before large-scale
use* — and recorded in its own exposure row before the first contact.

---

## 0. The answer

| | value |
|---|---:|
| **admission status** (section 4, pairing A) | **NEUTRAL** |
| status on pairing B (vs the depth-0 own-null replicate) | **NEUTRAL** — the two agree |
| gating metrics demonstrating harm | **none** |
| gating metrics demonstrating a gain | none, and none was expected |
| corpus WER, comparator → cell | 8.19952 % → **8.20730 %** |
| paired delta, call-clustered CI90 | **+0.00778** [−0.02329, +0.03856] |
| that delta as a share of the carrier's own null half-width | **0.13** |
| **falsifier — every emitted slice byte-identical to the comparator's** | **PASS, 1,593 of 1,593** |
| `prompt_tokens_total` | **1,935,965 — the comparator's, to the digit** |
| saturated windows | **0**, as the comparator and the replicate |
| **windows per minute (server-log replay), depth 0 → depth 1** | **17.244 → 20.168 (+16.96 %)** |
| **zero-slot share** | **17.55 % → 3.75 %** |
| **idle stretches ≥ 1 s** | **43 → 10**; idle seconds 972.6 → 177.5 |
| GPU hours | 1.0165 of 1.2 registered |

**What NEUTRAL licenses.** Section 8 of
`docs/readiness/2026-09-08-agent-system-episode-and-core-pressure-v1.md`: *the default plan
contains only admitted or neutral modules.* The dispatcher may now be turned on for Earnings-21
cells at this geometry. It is not a quality claim, and this verdict makes none.

---

## 1. The falsifier, run before any score file was opened

**Section 2 HOLDS ON 1,593 OF 1,593 WINDOWS.**

| check | result |
|---|---:|
| emitted slice `sha256` equals the comparator's for that window | **1,593** |
| `bytes`, `audio_seconds`, `start_seconds`, `end_seconds` equal the comparator's | **1,593** |
| `sample_rate_hz` and `parent_sha256` equal the comparator's | **1,593** |
| `preprocess` empty on both sides | **1,593** |
| **disagreeing rows** | **0** |

And at the wire:

| | comparator | null replicate | this cell |
|---|---:|---:|---:|
| **prompt tokens** | **1,935,965** | 1,935,965 | **1,935,965** — identical |
| metered speech seconds | 141,345.8526875 | 141,345.8526875 | 141,345.8526875 — identical |
| model calls | 1,593 | 1,593 | 1,593 |
| completion tokens | 439,532 | 439,342 | 439,455 |

**The dispatcher moved no request byte.** The prompt bytes, the audio bytes and the encoder's
token count are the same to the digit across all three arms; only the completions differ. That is
what makes this an admission test of a *scheduler* rather than of a mechanism, and it is proven on
the bytes rather than asserted from the design.

The composed identity is the preregistered one, re-read from the sealed manifest: config hash
`94af86c3…0bf33e`, protocol hash `5ebcb722…69f6fc`, split identity `fcc1b0bc…d69e` — the
comparator's split, and hashes that differ from its `e4b133d1…` / `06f7f308…` because one baseline
key moved. The pre-contact identity anchor recomputed both hashes **and** diffed the two composed
configs key by key, and the flight log records what it found:

```
identity anchor OK  config=94af86c3 protocol=5ebcb722 one_key_diff=['obs_prefetch_depth'] depth=1
```

**Exactly one key.**

---

## 2. Pairing A — against the sealed comparator, which decides the status

Call-clustered bootstrap, 44 clusters, 10,000 replicates, seed 20260903, CI90. Signed **cell minus
comparator**; on WER a negative delta is better, on numeric accuracy a positive delta is.

| metric | comparator | cell | delta | CI90 | margin | \|δ\|/margin | inside? |
|---|---:|---:|---:|---|---:|---:|---|
| `asr-wer-whisper` corpus WER | 8.19952 | 8.20730 | **+0.00778** | [−0.02329, +0.03856] | 0.05793 | **0.13** | **yes** |
| `conec-entity-wer-official` overall | 8.19952 | 8.20730 | +0.00778 | [−0.02329, +0.03856] | 0.05793 | 0.13 | yes |
| ConEC non-entity | 4.73038 | 4.72775 | −0.00263 | [−0.01994, +0.01574] | 0.06475 | 0.04 | yes |
| ConEC PERSON | 22.48886 | 22.69455 | +0.20569 | [−0.07995, +0.51951] | 0.25009 | 0.82 | yes |
| ConEC ORG | 17.21293 | 16.89205 | −0.32088 | [−0.88314, +0.19584] | 0.35609 | 0.90 | yes |
| `numeric-value-accuracy-v1` | 90.73351 | 90.68215 | −0.05137 | [−0.19511, +0.09794] | 0.15651 | 0.33 | yes |
| `semantic-high-impact-error-rate-v1` *(advisory)* | 0.02780 | 0.03002 | **+0.00222** | **[+0.00110, +0.00343]** | 0.00148 | **1.50** | **no** |

**Every gating metric is inside its margin, and not one gating CI90 excludes zero in either
direction.** Six of the seven intervals straddle zero; the two largest movements in margin units —
ORG at 0.90 and PERSON at 0.82 — are also the two metrics the null replicate showed this carrier
cannot resolve at 44 clusters, and both intervals are more than half a point wide.

The equal-stratum weighting says the same thing: 8.00364 → 8.00919, **+0.00554**, smaller than the
natural mixture's already-tiny delta. Both weightings are reported because the engineering rules
require both, and here they agree.

### 2.1 The advisory metric, and why the exclusion was preregistered rather than convenient

`semantic-high-impact-error-rate-v1` rose +0.00222 [+0.00110, +0.00343] against the comparator —
an interval that excludes zero, and a point delta 1.5x its margin. Under a rule that gated on it,
this cell would read **HARMFUL**.

Section 4 of the preregistration removed it from the gate **before any number existed**, on the
null replicate's own finding (its verdict section 2.2): the metric's *same-request* null already
excludes zero, so it can never carry a "does not rise" clause on this carrier. This cell then
produced the cleanest possible confirmation of that reasoning:

| arm | high-impact reference words | of |
|---|---:|---:|
| comparator | **100** | 359,765 |
| null replicate (depth 0, same request) | **108** | 359,765 |
| **this cell (depth 1)** | **108** | 359,765 |

**The cell's high-impact mass is the null replicate's, word for word**, and the pairing-B delta on
this metric is **+0.00000 [−0.00088, +0.00086]** — zero to five decimal places. The +0.00222 that
looks like harm against the comparator is *precisely* the movement a re-fly produces with nothing
changed; the dispatcher adds none of it. A metric that counts about a hundred words out of 359,765
resolves a two-word churn as a significant interval, and named-entity item 2 of the null replicate's
next steps ("this metric needs a decision, not a margin") is now supported by a second measurement
rather than one.

This is reported, not buried: **if the advisory metric were gating, the status would be HARMFUL**,
and the verdict says so in its own machine-readable summary
(`admission.status_if_advisory_were_gating`).

---

## 3. Pairing B — against the depth-0 own-null replicate, on the same server

Signed **cell minus replicate**. Both arms attached to the same resident session
`e21-np6-c36864-20260908`, so this pairing isolates the dispatcher from the process-instance
difference the comparator carries.

| metric | replicate | cell | delta | CI90 |
|---|---:|---:|---:|---|
| corpus WER / ConEC overall | 8.17951 | 8.20730 | +0.02780 | [−0.02052, +0.09427] |
| ConEC non-entity | 4.69390 | 4.72775 | +0.03384 | [−0.01134, +0.10702] |
| ConEC PERSON | 22.48886 | 22.69455 | +0.20569 | [−0.03577, +0.44875] |
| ConEC ORG | 17.12125 | 16.89205 | −0.22920 | [−0.58612, +0.09272] |
| numeric-value accuracy | 90.70269 | 90.68215 | −0.02055 | [−0.11017, +0.07806] |
| semantic high-impact | 0.03002 | 0.03002 | **+0.00000** | [−0.00088, +0.00086] |

**Status on pairing B: NEUTRAL. The two pairings agree**, which is the outcome the preregistration
said would need no explanation and the one that arrived.

### 3.1 The finding neither pairing was designed to produce

| pair | windows byte-identical | rate |
|---|---:|---:|
| comparator vs null replicate (depth 0 vs depth 0, different server process) | 540 | 33.90 % |
| comparator vs **this cell** (depth 0 vs depth 1, different server process) | 519 | **32.58 %** |
| null replicate vs **this cell** (depth 0 vs depth 1, **same** server process) | **722** | **45.32 %** |

**The two arms that shared a server process agree on 45 % of windows; the two that did not agree on
33 %, whether or not the depth changed.** Turning the dispatcher on cost 1.3 points of text
identity (33.90 % → 32.58 %); running on a different `llama-server` process instance cost 12
points. Under greedy decoding on this runtime, **which process answered matters more than how the
requests were batched** — an observation this study has never had a controlled read on, and one
that says every "same request, different day" comparison in this repository carries a process
term it has not been measuring.

It is a single observation from one triangle of arms and it is reported as such: it changes no
margin, and the null replicate's measured intervals stay the reference until a cell is designed to
test it.

---

## 4. What actually moved

| | comparator | null replicate | cell | cell − comparator | cell − null |
|---|---:|---:|---:|---:|---:|
| substitutions | 13,098 | 13,126 | 13,085 | **−13** | −41 |
| deletions | 5,701 | 5,570 | 5,696 | −5 | +126 |
| insertions | 10,700 | 10,731 | 10,746 | **+46** | +15 |
| errors | 29,499 | 29,427 | 29,527 | **+28** | +100 |
| reference words | 359,765 | 359,765 | 359,765 | 0 | 0 |

**The cell's whole +0.00778 is 28 extra errors out of 29,499, and 46 of them are insertions offset
by 18 fewer substitutions and deletions.** The null replicate's own movement was a 131-deletion
swing in the other direction. Both are the same channel and the same order of magnitude; neither
is a mechanism.

Per bucket: PERSON errors 656 → **662** (+6 of 2,917 reference words); ORG 751 → **737** (−14);
non-entity 14,396 → 14,388; numeric matched 8,832 → **8,827** (−5 of 9,734); semantic high-impact
mass 100 → 108, i.e. the replicate's own 108.

### 4.1 Per call

**14 calls better, 27 worse, 3 identical**, range **−0.4366 to +0.2283**.

| call | sector | rate | windows | comparator | cell | delta | comparator S/D/I | cell S/D/I |
|---|---|---:|---:|---:|---:|---:|---|---|
| `4366522` | Healthcare | 22,050 | 21 | 7.2277 | **6.7912** | **−0.4366** | 147/34/117 | 133/34/113 |
| `4367535` | Healthcare | 24,000 | 36 | 11.4261 | 11.1224 | −0.3037 | 409/111/270 | 401/118/250 |
| `4389907` | Technology | 24,000 | 23 | 13.1405 | 13.3688 | **+0.2283** | 235/40/243 | 240/38/249 |
| `4346923` | Industrial Goods | 16,000 | 53 | 18.9416 | 18.7149 | −0.2267 | 917/426/579 | 922/408/569 |
| `4344338` | Conglomerate | 44,100 | 31 | 4.7221 | 4.5206 | −0.2016 | 123/55/150 | 119/53/142 |

**The largest per-call movement here is −0.4366 — less than half the −1.0667 the null replicate
produced with nothing changed.** The full 44-row table, with both pairings and both identity rates,
is `verdict/per-call-table.md`. No per-call reading on this carrier is admissible outside the
replicate's ±1-point band, and every row of this cell is inside it.

The strata behave as they should. Sector deltas against the comparator span −0.0913 (Healthcare) to
+0.1102 (Technology); sample-rate deltas span −0.0656 (16 kHz) to +0.0979 (11.025 kHz). Industrial
Goods, which carries the 16 kHz `4346923` the Earnings-21 paper singles out, moves −0.0456. Nothing
moves in a way the pooled figure does not explain.

### 4.2 The window level

| | vs comparator | vs null replicate |
|---|---:|---:|
| windows paired | 1,593 | 1,593 |
| span misalignment | 0 | 0 |
| windows whose S/D/I counts moved | 649 (40.7 %) | 470 (29.5 %) |
| corpus-WER delta, clustered by call | +0.00778 [−0.02329, +0.03856] | +0.02780 [−0.02052, +0.09427] |
| corpus-WER delta, stratified by call (optimistic) | +0.00778 [−0.02286, +0.03999] | +0.02780 [−0.05165, +0.11860] |
| saturated windows | 0 on all three arms | 0 |

All three arms re-aggregate from their per-window rows to their own published corpus totals before
a single contrast is computed, and all three gates PASS.

---

## 5. The throughput claim — the reason the module exists

All three arms measured by **one instrument**: `slot launch_slot_` → `slot release` on llama.cpp's
own microsecond clock, through `scripts/obs_pipeline_dry_run.py`'s parsing and occupancy
arithmetic. The comparator's numbers are quoted from the committed dry-run receipt; the two
attached arms are carved out of the resident session's own `server.log` by
`scripts/e21_attempt_slot_occupancy.py`, which selects a task only when both its launch and its
release fall inside that attempt's contact window. Its own sanity check passed on both: **1,593
tasks in the window, exactly the 1,593 windows charged.**

| arm | depth | server | windows/min | mean slot use | **zero-slot share** | idle runs ≥ 1 s | idle seconds |
|---|---:|---|---:|---:|---:|---:|---:|
| `SAEA-E21-FULL44-DIRECT-BASELINE-V2` | 0 | own | 17.770 | 77.73 % | 15.40 % | 43 | 828.4 |
| `SAEA-E21-FULL44-NULL-REPLICATE-V1` | 0 | this session | 17.244 | 75.43 % | 17.55 % | **43** | 972.6 |
| **this cell** | **1** | this session | **20.168** | **91.93 %** | **3.75 %** | **10** | **177.5** |

| gain | vs the comparator's own server | **vs the depth-0 arm on this server** |
|---|---:|---:|
| windows per minute | 17.770 → 20.168, **+13.49 %** | 17.244 → 20.168, **+16.96 %** |
| mean slot utilisation | 77.73 % → 91.93 % | 75.43 % → 91.93 % |
| zero-slot share | 15.40 % → 3.75 % | 17.55 % → 3.75 % |
| idle seconds recovered | 651 s | **795 s** |

**The like-for-like number is +16.96 %.** The dry run predicted +22.8 % and the purely measured
ceiling was +18.2 %; the realized gain is **93 % of that measured ceiling and 74 % of the
simulator's**, and the simulator's own receipt warned it was optimistic (its depth-0 arm predicted
the measured wall to −4.04 %).

The wall says the same thing from the other side: **4,798 s of run wall against the replicate's
5,593 s — 13.2 minutes saved on an identical 1,593 requests**, and 19.921 windows per minute over
the whole run wall including gate setup, against the replicate's 17.089 (+16.6 %).

### 5.1 The 10 stretches that are left, and why

At depth 0, **every** idle second was a call boundary: 43 gaps, one per boundary, 100 % of the
zero-busy time. At depth 1 the count falls to **10** and the seconds to 177.5 — but the residual
is not noise, and it has a mechanism.

| longest residual idle stretch | seconds | at run offset |
|---|---:|---:|
| 1 | 39.3 | 2,699 s |
| 2 | 37.1 | 755 s |
| 3 | 25.3 | 3,303 s |
| 4 | 22.5 | 192 s |
| 5 | 18.5 | 492 s |

Depth 1 hides one boundary's CPU phase behind **one** sample's decode. That works whenever the
current call's remaining decode outlasts the next call's decode/cut/encode phase — which is most
of the time, since the median boundary gap was 17.9 s and a typical call's body is minutes. It
fails when a **short** call precedes a **long-CPU** one: a 13-to-21-window call can drain in less
time than a 75-minute MP3 takes to decode and slice, and the pipeline runs dry exactly there. Ten
of the 43 boundaries have that shape.

**The named fix is depth ≥ 2**, which the pipeline note already costs at about one decoded call's
PCM in RAM per extra lookahead (~145 MB) and warns buys progressively less. This verdict does not
fly it: the engineering rules admit one module at a time, and depth 1 now holds a receipt while
depth 2 holds none. The residual is 3.75 % of wall — the honest statement is that the dispatcher
removed **82 %** of this carrier's boundary idle, not all of it.

### 5.2 The monitor, over this attempt's own contact window

`core.session.serving.summarize_monitor_file` over 19:15:37Z–20:35:35Z, 422 samples:

| wall | active | **parked** | requests | mean / peak power | mean util | host free min | VM avail min |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,786.73 s | 4,553.43 s (**95.1 %**) | **233.30 s (4.87 %)** | 1,568 | 80.62 W / 100.72 W | **71.35 %** | 8.00 GB | 21.85 GB |

Against the replicate's own window: parked **19.7 % → 4.87 %**, mean utilisation **61.3 % →
71.35 %**, mean power **73.01 W → 80.62 W**. `requests_delta` is a lower bound at the 10-second
sampling interval; the charged count is 1,593.

**One operational warning, recorded because it nearly cost the flight.** Host free memory bottomed
at **8.00 GB**, below the 12 GB floor `serving_session.sh start` refuses under, with the VM's
working set peaking at 42.94 GB of its 44 GB cap. Two of those gigabytes were self-inflicted: the
analysis passes over the resident session's 440 MB `server.log` pull it into the VM page cache, and
running them *during* a flight charges that against the host's headroom. `posix_fadvise(DONTNEED)`
on that file returned about 1 GB immediately. **The server-log replay belongs after the flight, not
beside it** — the E7c incident took a flight down at 42 of 44 calls for exactly this reason.

---

## 6. Cost

| | realized | ceiling |
|---|---:|---:|
| model calls | **1,593** | 1,750 |
| speech-audio seconds (metered) | **141,345.8527** | 150,000 |
| GPU hours (manifest nvidia-smi sampler) | **1.0165** | 1.2 |
| paid API spend | 0 | 0 |

3,659.31 GPU-seconds, CPU 438.22 s, latency summed over 6 slots 34,549.37 s, peak VRAM 22,722 MiB
(comparator 22,720, replicate 22,722), gate setup 22.66 s, realized realtime factor 38.63x.

**1.0165 GPU-h is the top of the family band** (comparator 0.9734, `SAEA-E21-KC-E1-BRIEF-44-V1`
0.9948, `SAEA-E21-KU-E1C-PLACEBO-44-V1` 1.0087, `SAEA-E21-FULL44-TAIL2S-V1` 0.9765, null replicate
1.0085) and 0.8 % above the replicate's. The null replicate established that no GPU-hour comparison
inside this family is meaningful below about 4 % — it measured a 3.6 % spread on byte-identical
work — so this is inside the noise it measured, and the direction is what a denser flight should
produce anyway: the same GPU work in less wall means more *busy* seconds per second of wall, which
is what the sampler integrates. **The card did more work per unit time, not more work.**

**Attached, never started, never stopped.** `saea-driver run --session-receipt` reached the
coordinator's resident session `e21-np6-c36864-20260908` through `core.session.attach_session`;
geometry `-c 36864 -np 6`, six slots of 6,144 tokens, port 8080, fragment
`q4km-e21-buf90-mmproj-gpu-04ccc72a-np6`, bf16 mmproj resident on the GPU, raw audio, no feature
cache. `scripts/run_arm_sequence.sh` was deliberately not used.

Scored **once** over the complete manifest, never sharded: `saea-driver finalize` verified the
bundle, scored the four declared scorers and settled the attempt `FINALIZED` (MLflow run
`cf9b9160bfb64f018e1046add8823275`). The four agentic metrics then came out of four re-scoring
bundles through `core.scoring_batch`, one complete verified manifest per process, one worker,
`--include-per-sample`, 4 of 4 succeeded.

---

## 7. The signed predictions of section 6, checked

| prediction | outcome |
|---|---|
| status **NEUTRAL** | **HELD** |
| corpus-WER delta within ±0.10 of the comparator | **HELD** — +0.00778 |
| every gating metric inside its own margin | **HELD** — all six, max 0.90 margin units |
| the falsifier passes on 1,593 windows | **HELD** — 0 disagreeing rows |
| text identity below 60 % | **HELD** — 32.58 % |
| text identity below the replicate's own 33.90 % | **HELD** — 32.58 % |
| saturation 0 to 2 windows | **HELD** — 0 |
| **windows/min gain of +18 % to +23 %** | **FAILED** — +16.96 % vs the same-session depth-0 arm, +13.49 % vs the comparator's own server |
| **zero-slot share below 3 %** | **FAILED** — 3.75 % |
| **GPU hours ≤ 1.01** | **FAILED** — 1.0165 |

**Seven of ten held and the three failures are all on the throughput side, all in the same
direction, and all explained by one thing.** Section 5.1 has it: depth 1 hides one boundary's CPU
behind one sample's body, and ten boundaries where a short call precedes a long decode are not
covered by one sample of lookahead. That residual 3.75 % of idle is the missing 1–6 points of
windows-per-minute and, mechanically, the 0.8 % of GPU-hour: a flight that still parks for 177
seconds delivers slightly fewer windows per minute and slightly more integrated busy-time per
window than one that never parks.

**The predictions were written against the simulator's ceiling rather than against the shape of
the residual, and that is the modelling lesson.** The dry run's depth-1 arm modelled 99.9 %
occupancy — its own stated ceiling — by assuming greedy assignment in sample order with fixed
service times; it had no term for a call whose body is shorter than the next call's CPU phase.
The measured 91.93 % occupancy is what a one-sample lookahead actually achieves on this roster.
The honest revision, for the next receipt that quotes it: **depth 1 recovers about 80 % of the
measured boundary idle on Earnings-21, not all of it.**

---

## 8. What this cell cannot conclude

* **Nothing about quality, in either direction.** NEUTRAL means the score did not move outside
  this carrier's own replicate band. It is a licence to use the module, never evidence about
  knowledge, evidence supply, the agent layer or any mechanism.
* **Nothing about any other carrier.** SLURP and Audio2Tool have no measured null, so none of
  these margins travels to them, and the dispatcher's admission there is its own receipt. Their
  serving geometries and their per-request service times differ, so the throughput number does not
  travel either.
* **Nothing about `obs_prefetch_depth` ≥ 2**, which was not flown.
* **Nothing about the Earnings-21 test split**, which this row does not touch, and nothing
  published.
* **Not that the margins used here are exact.** They come from a single replicate at 44 clusters,
  and — the caveat section 4.1 fixed in advance — that replicate measured the noise of re-flying at
  **depth 0**, where a decode batch can only mix windows of one call. Depth 1 mixes two. The cell
  landing well inside those margins is evidence that the extra mixing costs little; it is not proof
  that a depth-0 margin is the right instrument for a depth-1 arm.
* **Not that the semantic high-impact rate is safe.** It is excluded from the gate, not vindicated,
  and this cell is the second measurement saying the metric cannot carry an admission clause on
  this carrier at this mass.

---

## 9. Named next steps

1. **Turn the dispatcher on for Earnings-21 cells at this geometry**, one fragment at a time, each
   with its own exposure row — `obs_prefetch_depth` moves the config hash by design, so a depth
   change can never ride along inside an unrelated cell, and a cell may not change depth
   mid-campaign.
2. **Decide `semantic-high-impact-error-rate-v1`, do not re-margin it.** Two cells have now shown
   its same-request null excludes zero because it counts about a hundred words. Either the taxonomy
   widens until the metric has mass, or it stops carrying admission clauses on this carrier.
3. **The process-instance term of section 3.1 deserves one cell.** Two arms on the same server
   agreed on 45 % of windows; two on different servers agreed on 33 %, depth change or not. If that
   holds, the carrier's replicate null is partly a *server* null, and every cross-day comparison in
   this repository carries a term nobody has measured.
4. **Depth 2 is the named throughput follow-up, not an assumption.** Ten short-call boundaries are
   what one sample of lookahead cannot cover; a second sample would cover them at the cost of one
   decoded call's PCM. It gets its own admission receipt or it does not get used.
5. **Run the server-log replay after the flight, never beside it.** Section 5.2: the analysis pass
   itself pulled the host to 8.00 GB free.
