# Verdict — Earnings-21's own greedy replicate null, measured

Run `SAEA-E21-FULL44-NULL-REPLICATE-V1`, attempt `attempt-20260908T113102Z-bdde07`, `COMPLETED`
and `FINALIZED` on study commit `839a73e5`, **1,593 of 1,593 windows over all 44 calls**, one
attempt, none aborted, **no recovery re-registration used**, `study_repo_dirt` empty. The cell of
`docs/readiness/2026-09-08-e21-own-null-replicate-v1-preregistration.md`, flown on owner Decision 8
of 2026-09-08 recorded in its own exposure row before the first contact.

---

## 0. The answer

**The same request, flown twice, moves corpus WER by −0.0200 points, CI90 [−0.0850, +0.0308].**
Sixty-six per cent of the 1,593 windows emitted different bytes. **This carrier's non-inferiority
margins are now measured rather than imported, and they are wrong in BOTH directions: the imported
±0.1524 was 2.6x too WIDE for corpus WER and 1.6x too NARROW for PERSON entity WER.**

| | value |
|---|---:|
| corpus WER, comparator `SAEA-E21-FULL44-DIRECT-BASELINE-V2` | 8.19952 % |
| corpus WER, replicate | **8.17951 %** |
| paired delta, **call-clustered CI90 — the honest interval** | **−0.02001** [−0.08502, +0.03085] |
| the null's own CI90 half-width, corpus WER | **0.05793** |
| per-window text-identity rate | **33.90 %** (540 of 1,593) |
| windows whose S/D/I counts moved | 634 of 1,593 (39.8 %) |
| saturated windows | **0**, as the comparator |
| falsifier — every emitted slice byte-identical to the comparator's | **PASS, 1,593 of 1,593** |
| identity gate — the comparator reproduces its published anchors | **PASS** |
| verdict | **there is none: this cell admits and refutes nothing** |

**This cell has no factor.** It is the sealed comparator's own configuration, flown again. There is
no ADMITTED / NOT-ADMITTED line here and no claim about the tail, the brief or any knob. What it
produces is a table of intervals and the margins section 4 of the preregistration derives from
them.

---

## 1. The falsifier, run before any score file was opened

**Section 2 HOLDS ON 1,593 OF 1,593 WINDOWS.**

| check | result |
|---|---:|
| emitted slice `sha256` equals the comparator's for that window | **1,593** |
| `bytes` equals the comparator's | **1,593** |
| `audio_seconds`, `start_seconds`, `end_seconds` equal the comparator's | **1,593** |
| `sample_rate_hz` and `parent_sha256` equal the comparator's | **1,593** |
| `preprocess` empty on both sides | **1,593** |
| **disagreeing rows** | **0** |

And at the wire:

| | comparator | replicate |
|---|---:|---:|
| **prompt tokens** | **1,935,965** | **1,935,965** — identical |
| metered speech seconds | 141,345.8526875 | 141,345.8526875 — identical |
| model calls | 1,593 | 1,593 |
| completion tokens | 439,532 | **439,342** (−190) |

**The request side is provably unchanged and only the completions moved.** That is what makes this
a null rather than a cell: the prompt bytes, the audio bytes and the encoder's token count are the
same to the digit, so nothing but decode-time batch composition can have produced the difference.

The composed identity holds too, re-read from the sealed manifest: config hash
`e4b133d1…c460ae`, protocol hash `06f7f308…330145`, split identity `fcc1b0bc…d69e` — the
comparator's three. The cell introduced no config fragment; it composed the comparator's own four.

---

## 2. The null table — the deliverable

Call-clustered bootstrap, 44 clusters, 10,000 replicates, seed 20260903, CI90.
Signed **replicate minus comparator**.

| metric | comparator | replicate | delta | CI90 | **half-width** | vs imported 0.1524 |
|---|---:|---:|---:|---|---:|---:|
| `asr-wer-whisper` corpus WER | 8.19952 | 8.17951 | **−0.02001** | [−0.08502, +0.03085] | **0.05793** | 0.38x — imported is 2.6x too wide |
| `conec-entity-wer-official` overall | 8.19952 | 8.17951 | −0.02001 | [−0.08502, +0.03085] | 0.05793 | 0.38x |
| ConEC non-entity | 4.73038 | 4.69390 | −0.03647 | [−0.11375, +0.01575] | 0.06475 | 0.42x |
| **ConEC PERSON** | 22.48886 | **22.48886** | **+0.00000** | [−0.24338, +0.25680] | **0.25009** | **1.64x — imported is too NARROW** |
| ConEC ORG | 17.21293 | 17.12125 | −0.09168 | [−0.44313, +0.26904] | **0.35609** | **2.34x — too narrow** |
| `numeric-value-accuracy-v1` | 90.73351 | 90.70269 | −0.03082 | [−0.18758, +0.12543] | 0.15651 | 1.03x |
| `semantic-high-impact-error-rate-v1` | 0.02780 | 0.03002 | **+0.00222** | **[+0.00080, +0.00377]** | 0.00148 | 0.01x |

**Two of these rows are the reason the measurement was worth flying.**

### 2.1 PERSON entity WER: a delta of exactly zero with an interval of ±0.25

The corpus PERSON figure is **identical to five decimal places** — 656 errors over 2,917 reference
words on both arms. It is a coincidence, and the per-call rows say so: **17 of the 44 calls moved
their PERSON error count** (23→24, 46→45, 17→18, 29→30, 14→13, …) and the movements happened to
cancel. The cluster bootstrap resamples calls, so it sees that churn and returns ±0.25 points even
though the pooled delta is 0.

**The imported ±0.1524 margin was 1.6x too narrow on the one metric the Earnings mechanism ladder
is aimed at.** Any Earnings-21 PERSON claim smaller than a quarter of a point is inside this
carrier's own replicate noise.

### 2.2 The semantic high-impact rate: a null whose interval EXCLUDES ZERO

`semantic-high-impact-error-rate-v1` rose from 0.02780 % to 0.03002 %, **+0.00222 [+0.00080,
+0.00377] — an interval that does not contain zero, under a null where nothing changed.**

The mechanism is arithmetic, not statistical mischief: the metric counts high-impact reference-word
mass, and that mass is **100 words on one arm and 108 on the other, out of 359,765**. Nine of the
44 calls moved (seven up, two down), so the movement is spread across clusters rather than
concentrated, and the bootstrap resolves it.

**A metric whose same-request null excludes zero cannot carry a "does not rise" clause.** Section
4.3 item 2 of the cross-carrier preregistration gave it exactly that clause. That clause was never
answerable on this carrier and this measurement is what shows it.

---

## 3. The margins, and the rule now in force

Section 4 fixed the rule before any number existed:

> For each metric, the Earnings-21 non-inferiority margin becomes **the half-width of this null's
> own call-clustered CI90 on that metric**. A future Earnings-21 cell demonstrates an effect on
> metric *m* iff its CI90 is disjoint from **this null's measured interval**, not merely from zero.

| metric | **margin (measured)** | **null interval to be disjoint from** |
|---|---:|---|
| corpus WER / ConEC overall | **0.05793** | [−0.08502, +0.03085] |
| ConEC non-entity | **0.06475** | [−0.11375, +0.01575] |
| ConEC PERSON | **0.25009** | [−0.24338, +0.25680] |
| ConEC ORG | **0.35609** | [−0.44313, +0.26904] |
| numeric-value accuracy | **0.15651** | [−0.18758, +0.12543] |
| semantic high-impact rate | **0.00148** | [+0.00080, +0.00377] |

These replace the imported Earnings-22 half-width of ±0.1524 **for Earnings-21 only**, from this
cell's closure. They are never carried to SLURP or Audio2Tool, which still have no measured null of
their own.

**The caveat travels with the margin.** A single replicate measures this null with 44 clusters and
no more. The intervals are themselves uncertain; they are better margins than an imported one, not
exact ones, and every verdict that uses them must name this cell.

### 3.1 The clause-1 threshold moves, and it moves LOOSER

The imported clause-1 rule asked a corpus-WER effect to clear **−0.2356**. Measured, the bar is
disjointness from [−0.08502, +0.03085], i.e. **a CI90 upper bound below −0.08502**. The imported
threshold demanded 2.8x more effect than this carrier's own noise requires — it was conservative,
not lax.

---

## 4. Re-adjudicating the silence-tail cell against the measured null

`SAEA-E21-FULL44-TAIL2S-V1` was judged against the imported margin and came out NOT ADMITTED with
clause 2 failing on two metrics whose intervals were wider than that margin. Re-read against the
margins this cell measured:

| metric | tail delta | tail CI90 | \|delta\| / null half-width | disjoint from the null? | non-inferior at the measured margin? |
|---|---:|---|---:|---|---|
| corpus WER | −0.9281 | [−1.0514, −0.7949] | **16.0** | **YES** | **PASS** |
| ConEC overall | −0.9281 | [−1.0514, −0.7949] | 16.0 | **YES** | PASS |
| ConEC non-entity | +0.1032 | [−0.0350, +0.2493] | 1.59 | no | FAIL |
| **ConEC PERSON** | +0.6856 | [+0.1314, +1.3467] | 2.74 | **no** | **FAIL** |
| ConEC ORG | −0.3438 | [−0.9608, +0.2651] | 0.97 | no | PASS |
| numeric accuracy | +0.0411 | [−0.2074, +0.2877] | 0.26 | no | FAIL |
| semantic high-impact | −0.00083 | [−0.0042, +0.0020] | 0.56 | no | FAIL |

**Three findings, and none of them is the comfortable one.**

1. **The tail cell's corpus-WER effect is real and enormous relative to this carrier's noise.**
   −0.9281 is **16 null half-widths**; the two intervals are separated by 0.71 points. Whatever
   else is true of that cell, its headline number is not replicate noise.
2. **The PERSON regression does NOT survive the measured null.** The tail verdict called
   +0.6856 [+0.1314, +1.3467] "the only demonstrated harm in this cell" on an excludes-zero basis.
   Zero was the wrong reference: against [−0.2434, +0.2568] the two intervals **overlap**, and the
   claim weakens from *demonstrated harm* to *2.7 null half-widths, consistent with replicate noise
   at its low end*. The point estimate is still the largest PERSON movement anyone has measured on
   this carrier and it still deserves the next cell's attention — but it is no longer a
   demonstrated harm, and this verdict corrects the tail verdict's reading rather than restating
   it.
3. **Measuring the null did not rescue clause 2; it made it harder.** The tail cell fails
   non-inferiority on *four* metrics at the measured margins instead of two, because on this
   carrier those metrics' own noise at 44 clusters is comparable to or larger than the effects
   being tested. **`SAEA-E21-FULL44-TAIL2S-V1` stays NOT ADMITTED, now for a measured reason
   instead of an imported one.** The honest reading of the tail cell is unchanged in substance:
   an insertion repair worth 0.93 corpus-WER points, whose cost to the entity metrics this study
   cannot yet resolve at n = 44.

**What this implies for the roster.** Four of the six agentic metrics cannot resolve a
half-point effect at 44 call clusters. Earnings-21 mechanism claims on PERSON, ORG, numeric
accuracy and the semantic rate need more clusters, not a tighter margin.

---

## 5. What actually moved

| | comparator | replicate | change |
|---|---:|---:|---:|
| substitutions | 13,098 | 13,126 | **+28** |
| deletions | 5,701 | **5,570** | **−131** |
| insertions | 10,700 | 10,731 | +31 |
| errors | 29,499 | 29,427 | −72 |
| substitution + deletion block | 18,799 | 18,696 | −103 |
| reference words | 359,765 | 359,765 | 0 |

**The replicate's whole corpus gain is a deletion swing**, which is the same channel the tail cell
paid its own cost in. 131 deletions over 359,765 words is 0.036 points — the size of the null.

Per bucket: ConEC non-entity errors 14,396 → 14,285 (−111, moving on 38 of 44 calls); ORG errors
751 → 747 (−4); PERSON errors 656 → 656 (moving on 17 calls, net 0); numeric matched 8,832 → 8,829
(−3 of 9,734, moving on 21 calls); semantic high-impact mass 100 → 108 (moving on 9 calls).

### 5.1 Per call — and the number that should worry a per-call reader

**18 calls better, 26 worse, 0 identical**, range **−1.0667 to +0.2330**.

| call | sector | rate | windows | ref words | comparator | replicate | delta | comparator S/D/I | replicate S/D/I |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| `4346818` | Industrial Goods | 11,025 | 45 | 10,968 | 10.9500 | **9.8833** | **−1.0667** | 542/362/297 | 552/**214**/318 |
| `4367535` | Healthcare | 24,000 | 36 | 6,914 | 11.4261 | 11.0645 | −0.3616 | 409/111/270 | 400/113/252 |
| `4394084` | Technology | 16,000 | 20 | 3,636 | 12.1562 | 11.8812 | −0.2750 | 214/85/143 | 215/81/136 |
| `4384744` | Technology | 16,000 | 37 | 8,155 | 9.2213 | 9.4543 | +0.2330 | 354/155/243 | 360/156/255 |

**The largest single-call movement under a pure null is −1.0667 points — larger in magnitude than
the tail cell's entire corpus effect.** And it lands on `4346818`, the very call the tail cell's
per-call table named as one of only two that worsened (+0.8023, deletions 362 → 604). Here, with
*nothing changed*, the same call's deletions fall 362 → 214 and it improves by a point.

**Per-call Earnings-21 readings carry about ±1 point of replicate noise even though the corpus null
is ±0.058.** No per-call story on this carrier is admissible without its own replicate. The full
44-row table is `verdict/per-call-table.md`.

The strata behave as a null should: sector deltas span −0.2941 (Industrial Goods, which contains
`4346818`) to +0.0519 (Financial), with Conglomerate at exactly 0.0000; sample-rate deltas span
−0.1749 (11,025 Hz, again `4346818`) to +0.0231 (22,050 Hz). No stratum moves in a way the pooled
figure does not explain.

---

## 6. The text, window by window

| | value |
|---|---:|
| windows paired | 1,593 |
| **accepted span byte-identical** | **540 (33.90 %)** |
| raw `MODEL_RESPONSE` byte-identical | 540 (33.90 %) |
| windows differing | 1,053 (66.10 %) |
| windows whose S/D/I counts differ | 634 (39.80 %) |
| calls with every window identical | **0 of 44** |
| lowest per-call identity | `4344338` 19.4 %, `4383161` 21.1 %, `4367535` 25.0 % |
| highest per-call identity | `4384198` 60.0 %, `4387383` 58.3 %, `4360674` 50.0 % |

The accepted-span and raw-completion rates are equal because nothing saturated on either arm, so
`obs_loop`'s quarantine is a measured no-op on both.

**Two thirds of the windows come back different and 60 % of them still score the same.** 1,053
windows changed text; only 634 changed their operation counts. The remaining 419 are rewordings
that the Whisper normalizer and the alignment absorb — which is precisely why the corpus null
(±0.058) is two orders of magnitude tighter than the byte-level disagreement rate suggests.

For scale: Earnings-22's own null saw 302 of 1,432 rows (21.1 %) differ on 3-second utterances.
A 90-second window has roughly 30x more tokens to diverge in, and 66.1 % of them do.

---

## 7. Cost, serving and throughput

| | realized | ceiling |
|---|---:|---:|
| model calls | **1,593** | 1,750 |
| speech-audio seconds (metered) | **141,345.8527** | 150,000 |
| GPU hours (manifest nvidia-smi sampler) | **1.0085** | 1.2 |
| paid API spend | 0 | 0 |

**The cost side is a null measurement too, and it is not zero.** The identical 1,593 requests cost
**0.9734 GPU-h** on the comparator and **1.0085** here — a **3.6 % spread on byte-identical work**,
landing at the top of the family band (comparator 0.9734, `SAEA-E21-KC-E1-BRIEF-44-V1` 0.9948,
`SAEA-E21-KU-E1C-PLACEBO-44-V1` 1.0087, `SAEA-E21-FULL44-TAIL2S-V1` 0.9765). No GPU-hour comparison
inside this family is meaningful below about 4 %.

**Attached, never started, never stopped.** `saea-driver run --session-receipt` reached the
coordinator's resident session `e21-np6-c36864-20260908` through `core.session.attach_session`;
geometry `-c 36864 -np 6`, 6 slots of 6,144 tokens, port 8080, fragment
`q4km-e21-buf90-mmproj-gpu-04ccc72a-np6`, bf16 mmproj resident on the GPU, raw audio, no feature
cache. Session receipt sha256 `de3ff630…e7fc`. `scripts/run_arm_sequence.sh` was deliberately not
used: its pre-arm cleanup refuses while a serving session is resident and its smoke step would have
spawned a second llama-server.

Monitor summary over this attempt's own contact window (11:31:02Z to 13:04:15Z), 494 samples:

| wall | active | parked | requests | mean / peak power | mean util | host free min | VM avail min |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5,583.79 s | 4,486.50 s (80.3 %) | 1,097.29 s (19.7 %) | 1,581 | 73.01 W / 99.93 W | 61.3 % | 14.36 GB | 29.42 GB |

`requests_delta` is a lower bound at the 10-second sampling interval; the charged count is 1,593.
Host free memory bottomed at **14.36 GB**, above the 12 GB floor `serving_session.sh start` refuses
below, with the VM's working set peaking at 34.88 GB of its 44 GB cap.

**Throughput: 1,593 windows in 5,593 s (93.22 min) — 17.089 windows per minute**, realized realtime
factor **38.93x**, 3,630.76 GPU-seconds, latency summed over 6 slots 33,206.9 s, CPU 357.9 s, peak
VRAM 22,722 MiB (comparator 22,720), gate setup 20.7 s. Per-window prompt tokens 75 / 1,232 / 1,232
(min / median / max) against a 6,144-token slot, margin factor 4.99. Family rates: comparator
16.38, KC-E1 16.244, KU-E1c 16.482, tail2s 17.225. Finalize took a further 31 min.

Scored **once** over the complete manifest, never sharded: `saea-driver finalize` verified the
bundle, scored all four declared scorers and settled the attempt `FINALIZED` (MLflow run
`6888744857fe4f6c876cd075198fe645`). The four agentic metrics then came out of four re-scoring
bundles through `core.scoring_batch`, one complete verified manifest per process, one worker,
`--include-per-sample`, 4 of 4 succeeded.

---

## 8. The signed predictions of section 5, checked

| prediction | outcome |
|---|---|
| corpus-WER delta inside −0.35 to +0.35 | **HELD** — −0.02001 |
| the CI90 half-width is **wider** than the imported 0.1524 | **FAILED** — 0.05793, i.e. 2.6x **narrower** |
| text-identity rate below 60 % | **HELD** — 33.90 % |
| saturation between 0 and 2 windows | **HELD** — 0, matching the comparator |
| both tail-cell clause-2 failures have null half-widths above 0.1524 | **FAILED** — numeric 0.1565 clears it by 0.0041, non-entity 0.0648 does not |

**Two of five predictions failed and the failures are the informative half.** The reasoning behind
the second was that a 90-second unit with a 1,024-token cap would be noisier than Earnings-22's
3-second utterances. It is noisier **per window** — 66 % of windows differ against Earnings-22's
21 % of rows — but the corpus aggregate is *quieter*, because 359,765 reference words average the
churn away and 419 of the 1,053 changed windows do not move a single operation. Volatility at the
unit and stability at the corpus are not the same quantity, and the prediction conflated them.

The fifth failed for a related reason: the imported margin is not uniformly too wide or too narrow,
it is simply unrelated to this carrier's metrics. It is too wide for the three WER-shaped ones and
the semantic one, about right for numeric accuracy, and too narrow for the two entity classes.

---

## 9. What this cell cannot conclude

* **Nothing about the Earnings-21 test split, and nothing published.** These are the 44 discovery
  calls; no new speech exposure, since the request bytes are the comparator's own.
* **Nothing about any mechanism.** No factor was moved. Section 4's re-adjudication of the tail
  cell is a re-reading of that cell's already-sealed numbers against a new reference, not a new
  measurement of it.
* **Not that the margins here are exact.** 44 clusters, one replicate. A second replicate would
  produce a different interval, and the margins should be re-measured if the geometry, the build or
  the population changes.
* **Not that the runtime is deterministic anywhere else.** This is one carrier, one geometry
  (`-c 36864 -np 6`), one build (`04ccc72a`), one decoding setting. SLURP and Audio2Tool still have
  no measured null, and the two consequences section 3 of the cross-carrier preregistration binds
  to that remain in force for them.
* **Not that a per-call Earnings-21 reading is safe.** Section 5.1 measured ±1 point of per-call
  replicate noise. It is not safe.

---

## 10. Named next steps

1. **Re-read every open Earnings-21 claim against the table in section 3.** The tail cell is done
   here; the KC-E1 / KU-E1c / KC-E1F / KU-E1FC family has not been re-adjudicated and its entity
   claims sit in exactly the band this null cannot resolve.
2. **`semantic-high-impact-error-rate-v1` needs a decision, not a margin.** Its null excludes zero
   because it counts about a hundred words out of 359,765. Either the taxonomy widens until the
   metric has mass, or the metric stops carrying admission clauses on this carrier.
3. **Entity claims need clusters, not tighter margins.** PERSON at ±0.25 and ORG at ±0.36 on 44
   calls cannot resolve the half-point effects the mechanism ladder is aiming at. More calls, or a
   different estimand.
4. **Measure the same-request null on SLURP and on Audio2Tool.** This cell proves the imported
   margin was wrong in both directions on the one carrier where it could be checked. There is no
   reason to expect it is right on the other two.
