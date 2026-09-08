# Verdict — the Earnings-21 full-44 buf90 windows re-flown with a 2.0 s silence tail

Run `SAEA-E21-FULL44-TAIL2S-V1`, attempt `attempt-20260907T231248Z-00f13c`, `COMPLETED` and
`FINALIZED` on study commit `81f2b1e9`, **1,593 of 1,593 windows over all 44 calls**, one attempt,
none aborted, **no recovery re-registration used**, `study_repo_dirt` empty. The Earnings-21 cell of
`docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md` §§1.4, 4.3 and 6.3,
flown on the owner GO of 2026-09-07 recorded in its own exposure row before the first contact.

---

## 0. The answer

**Corpus Whisper-normalized WER falls from 8.1995 % to 7.2714 %, a paired −0.9281 points
[−1.0514, −0.7949], and the cell is NOT ADMITTED anyway.** Two of §4.3's three clauses pass; the
one that fails is the clause that exists to catch exactly what happened.

| | value |
|---|---:|
| corpus WER, cell (`asr-wer-whisper`) | **7.2714 %** |
| corpus WER, sealed comparator `SAEA-E21-FULL44-DIRECT-BASELINE-V2` | 8.1995 % |
| paired delta, **call-clustered CI90 — the honest interval** | **−0.9281** [−1.0514, −0.7949] |
| paired delta, window-level stratified by call (optimistic bound) | −0.9281 [−1.0632, −0.7782] |
| **§4.3 clause 1 — corpus WER beats the imported null** | **PASS** |
| **§4.3 clause 2 — no agentic metric worsens** | **FAIL** |
| **§4.3 clause 3 — the effect concentrates where the audit predicts** | **PASS** |
| **verdict** | **NOT ADMITTED** |
| §5 prediction (−0.2 to −1.5 points) | **held** |

**What the number is, and what it is not.** This is discovery data on the 44-call `earnings21-original`
discovery split. Every request carried 2.0 s of digital silence the published systems did not append,
so it is **not a like-for-like reproduction of any published protocol** and must never be reported as
one. §8 is what it licenses.

---

## 1. The falsifier, run before any score file was opened

**§4.4 HOLDS ON 1,593 OF 1,593 WINDOWS, and on 13 of 13 in the smoke.**

| check | flight | smoke |
|---|---:|---:|
| windows checked | **1,593 of 1,593** | 13 of 13 |
| emitted slice SHA-256 equals the committed `@ts2` entry | **1,593** | 13 |
| delivered byte count equals the committed entry | **1,593** | 13 |
| delivered seconds = cut seconds + exactly 2.0 | **1,593** | 13 |
| byte count equals `44 + 2 × round(delivered × 16000)` | **1,593** | 13 |
| `preprocess` declares `tail-silence-2s` | **1,593** | 13 |
| `audio_seconds` still equals the CUT span | **1,593** | 13 |
| `pre_sha256` equals the SEALED comparator's own cut for that window | **1,593** | 13 |
| window spans equal to the comparator's | **1,593** | 13 |
| **disagreeing rows** | **0** | **0** |

Delivered total **144,531.852688 s** and **4,625,089,378 bytes**, both exactly the committed
supplement's own `audio_seconds_total` and `total_bytes`. The cut total is 141,345.852688 s, which is
what `SliceRecord.audio_seconds` meters and what the manifest charges.

**One defect was found, and it was in the checker rather than in the cell.** The first pass flagged
11 rows on delivered seconds. All eleven were the same rounding artifact: the committed supplement
stores seconds to six decimals (22.914313) while the runtime's cut span is exact (20.9143125 → 22.9143125),
a 5 × 10⁻⁷ gap at the receipt's own precision limit. The SHA-256 and byte-count checks — which pin
the delivered sample count exactly, since a 16-bit mono WAV is `44 + 2 × samples` — passed on all
1,593 rows on that first pass too. The comparison is now made at the receipt's own precision with the
byte-count identity checked alongside it, and the record says so here rather than quietly re-running.

The `pre_sha256` chain is the part that could not be checked offline: it proves the bytes this flight
actually sent are the sealed comparator's own 90-second cuts with 32,000 zero samples appended, and
nothing else, on every window.

**And the wire agrees, to the token.** Prompt tokens **1,977,383** against the comparator's
**1,935,965** — a difference of **41,418 = 1,593 × 26 exactly**, with no residue. 26 tokens is 2.0 s
at the encoder's 13 tokens per second. Per-window prompt tokens are 101 / 1,258 / 1,258 (min /
median / max) against a 6,144-token slot, margin factor 4.88. The prompt text is the comparator's
byte for byte; the only thing that grew is the audio.

---

## 2. The decision rule, quoted verbatim from §4.3 before it is applied

> **ADMITTED iff all three hold**:
>
> 1. **Corpus WER, and it must beat the null.** The CI90 upper bound on the delta is **< −0.2356** —
>    below zero and disjoint from the Earnings-22 same-request null's interval, which is the closest
>    measured null this carrier has and is labelled as imported.
> 2. **No agentic metric worsens.** `numeric-value-accuracy-v1` and `conec-entity-wer-official`
>    (overall and non-entity) are non-inferior at their own CI90, and
>    `semantic-high-impact-error-rate-v1` does not rise. Its sealed 0.02780 % is a strict lower bound
>    on the true content-impact rate and the verdict must repeat that when it uses it.
> 3. **The effect concentrates where the audit predicts.** The per-window contrast is larger on the
>    **1,088 interior windows that end within 20 ms of active speech** than on the 39 windows that
>    already carry 2.0 s or more of trailing silence.

### 2.1 Clause 1 — PASS

Delta **−0.9281**, CI90 **[−1.0514, −0.7949]**. The upper bound is 0.559 points below the −0.2356
threshold; the whole interval is disjoint from the imported null's [−0.2356, +0.0692].

**The null is IMPORTED, not measured.** §3 is explicit: no same-request null has ever been measured
on Earnings-21. The −0.2356 threshold is the Earnings-22 null's own lower bound, measured on 1,432
Earnings-22 rows whose request differed only by an inert integer. Measuring this carrier's own null
is the named next cell, not a footnote.

### 2.2 Clause 2 — FAIL, and the reason matters more than the verdict

| metric | comparator | cell | delta | CI90 (call-clustered) | non-inferiority at the imported margin ±0.1524 | reading |
|---|---:|---:|---:|---|---|---|
| `numeric-value-accuracy-v1` | 90.7335 | **90.7746** | **+0.0411** | [−0.2074, +0.2877] | **FAIL** (lower −0.2074 < −0.1524) | straddles zero |
| `conec-entity-wer-official` overall | 8.1995 | **7.2714** | **−0.9281** | [−1.0514, −0.7949] | PASS | improvement demonstrated |
| `conec-entity-wer-official` non-entity | 4.7304 | **4.8336** | **+0.1032** | [−0.0350, +0.2493] | **FAIL** (upper +0.2493 > +0.1524) | straddles zero |
| `semantic-high-impact-error-rate-v1` | 0.02780 | **0.02696** | **−0.00083** | [−0.0042, +0.0020] | PASS | straddles zero |

**Neither failing metric shows a demonstrated harm.** Both intervals straddle zero: the numeric
accuracy point estimate is even slightly positive. What fails is *non-inferiority at a margin this
carrier never measured* — the imported ±0.1524 half-width is **narrower than these two metrics' own
sampling noise at 44 clusters**, so the test cannot conclude either way. That is a statement about the
margin and the interval, not a measured worsening, and the rule as written admits nothing on an
inconclusive clause.

`semantic-high-impact-error-rate-v1` does not rise (−0.00083, and its interval straddles zero).
**Its 0.02780 % sealed value is a strict lower bound on the true content-impact rate**, as §4.3 item
2 requires this verdict to repeat: the taxonomy is a mechanical projection of the Earnings-22
content-impact word-pair model and classifies only what that model covers.

### 2.3 Clause 3 — PASS, and it is the cleanest result in the document

The mechanism concentrates exactly where the 2026-09-07 encoding audit said it would.

| window class | n | comparator WER | cell WER | delta | CI90 (clustered by call) |
|---|---:|---:|---:|---:|---|
| **interior, ends within 20 ms of active speech** | **1,088** | 8.2007 | **7.2227** | **−0.9780** | [−1.1609, −0.7737] |
| remainder | 466 | 8.1900 | 7.3451 | −0.8449 | [−0.9353, −0.7530] |
| **already carries 2.0 s or more** | **39** | 8.3027 | **7.9358** | **−0.3669** | [−0.7585, −0.0178] |

The mid-speech-ended interior windows gain **2.7 times** what the already-silent windows gain. The
39-window stratum is thin and its interval is correspondingly wide, but the ordering is the one §4.3
item 3 fixed before any number existed, and it is the clause that could have falsified the mechanism
even while the pooled number moved. It did not.

The strata are the committed `@ts2` roster receipt's own per-window
`source_trailing_silence_seconds`, measured by `analysis.e22_clip_boundary.energy_margins` on the
SEALED slices, and they reproduce §1.4's published counts exactly: 1,549 interior windows, 1,088 of
them ending within 20 ms of active speech, 39 already at 2.0 s or more, 44 final windows at a median
0.560 s.

---

## 3. What actually moved: the entire gain is an insertion collapse

| | comparator | **cell** | change |
|---|---:|---:|---:|
| substitutions | 13,098 | **12,931** | −167 |
| deletions | 5,701 | **6,192** | **+491** |
| insertions | 10,700 | **7,037** | **−3,663** |
| errors | 29,499 | 26,160 | −3,339 |
| **substitution + deletion block** | **18,799** | **19,123** | **+324 WORSE** |
| reference words | 359,765 | 359,765 | 0 |
| insertion share of errors | 36.27 % | **26.90 %** | −9.37 pp |
| completion tokens | 439,532 | 435,392 | −4,140 |

**This is the Earnings-22 finding again, on a different carrier and at a different scale.** That
verdict recorded an 87-operation worsening of the substitution-plus-deletion block against a
3,364-insertion collapse. Here the S+D block is **324 operations worse** against a **3,663-insertion
collapse**. The tail does not make the model transcribe better; it stops the model running past the
end of the clip, and it pays for that with deletions.

**And that is precisely why the two families of metric move in opposite directions.** ConEC's
definition, transcribed from fstalign, cannot attribute an insertion to a tag, so **every entity
bucket and the `__NON_ENTITY__` bucket see only the S+D block** — the half that got worse. Corpus WER
counts all three operations. One media change, two honest metrics, opposite signs; neither is wrong.

### 3.1 The per-entity table, and the one that is a demonstrated harm

| class | ref words | comparator | **cell** | delta | CI90 (call-clustered) |
|---|---:|---:|---:|---:|---|
| **PERSON** | 2,917 | 22.4889 | **23.1745** | **+0.6856** | **[+0.1314, +1.3467]** |
| ORG | 4,363 | 17.2129 | **16.8691** | −0.3438 | [−0.9608, +0.2651] |
| non-entity | 304,331 | 4.7304 | **4.8336** | +0.1032 | [−0.0350, +0.2493] |

The cell's own full 30-class table is in `verdict/result-summary.json`; PERSON and ORG carry the two
largest entity supports (2,917 and 4,363 reference words) and are the two the agentic-metric baseline
identified as the ones that carry real weight.

**PERSON entity WER worsens by +0.6856 points with a CI90 that excludes zero.** That is the only
demonstrated harm in this cell, and it lands on the class the 2026-09-06 agentic-metric baseline
named "the open class" — the one metric the whole Earnings mechanism ladder is aimed at, sitting
between Whisper-large's 28.9 and ConEC's own oracle ceiling of 13.0. §4.3 clause 2 names only the
overall and non-entity buckets, so PERSON does not formally block admission; it is reported here
because a cell that buys 0.93 corpus-WER points by losing 0.69 points of PERSON accuracy is not a
free improvement, and the next Earnings mechanism cell has to know that.

**It is not an artifact of the one saturated window.** Dropping call `4346818` entirely (§5) leaves
PERSON at +0.5975 [+0.0380, +1.2616] — still excluding zero — while the corpus-WER delta strengthens
to −0.9825 [−1.0822, −0.8828].

---

## 4. The mandatory slices

### 4.1 Natural mixture beside equal-stratum weighting

| | natural mixture (corpus) | equal call |
|---|---:|---:|
| comparator | 8.1995 | 8.0036 |
| **cell** | **7.2714** | **7.0638** |
| delta | **−0.9281** | −0.9399 |

The two weightings agree to within 0.012 points: the effect does not depend on the long calls.

### 4.2 By sector, and by sample rate — every stratum moves the same way

| sector | calls | ref words | comparator | **cell** | delta |
|---|---:|---:|---:|---:|---:|
| Basic Materials | 5 | 35,678 | 8.4366 | **7.4808** | −0.9558 |
| Conglomerate | 4 | 40,852 | 7.3607 | **6.4379** | −0.9228 |
| Consumer Goods | 5 | 49,971 | 7.0521 | **6.0375** | −1.0146 |
| Financial | 5 | 42,427 | 8.7232 | **8.0232** | −0.7000 |
| Healthcare | 5 | 36,137 | 7.9918 | **6.8157** | −1.1761 |
| Industrial Goods | 5 | 43,865 | 10.6623 | **10.1744** | −0.4879 |
| Services | 5 | 34,029 | 6.4680 | **5.4042** | −1.0638 |
| Technology | 5 | 28,134 | 9.1526 | **8.4382** | −0.7144 |
| Utilities | 5 | 48,672 | 8.0457 | **6.7821** | −1.2636 |

| sample rate | calls | ref words | comparator | **cell** | delta |
|---|---:|---:|---:|---:|---:|
| 11,025 Hz | 5 | 48,023 | 11.0780 | **10.6199** | −0.4581 |
| 16,000 Hz | 6 | 42,675 | 10.7370 | **9.6919** | −1.0451 |
| 22,050 Hz | 5 | 34,619 | 7.5768 | **6.0949** | −1.4818 |
| 24,000 Hz | 21 | 165,974 | 7.3198 | **6.3751** | −0.9447 |
| 44,100 Hz | 7 | 68,474 | 7.0465 | **6.1819** | −0.8646 |

**Nine sectors of nine and five sample rates of five improve.** The two weakest strata are the two
with the highest baseline WER (11,025 Hz at 11.08, Industrial Goods at 10.66), which is the opposite
of what a systematic harness artifact would look like.

### 4.3 Per call — 42 of 44 improve

The full 44-row table, with each call's sector, sample rate, window count, reference words, both
corpus-WER figures and both S/D/I triples, is in `verdict/per-call-table.md` and in
`verdict/result-summary.json`. Summary: **42 calls improve, 2 worsen, 0 tie.**

The two that worsen:

| call | sector | rate | windows | ref words | comparator | cell | delta | comparator S/D/I | cell S/D/I |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| `4346818` | Industrial Goods | 11,025 | 45 | 10,968 | 10.9500 | 11.7524 | **+0.8023** | 542/362/297 | 521/**604**/164 |
| `4366302` | Financial | 44,100 | 40 | 10,013 | 5.8025 | 6.0421 | +0.2397 | 257/90/234 | 253/**197**/155 |

Both regressions are deletion-driven, which is the same mechanism as the gain, running the other way.
`4346818` is also the call that carries this cell's one saturated window — see §5.

---

## 5. Decode-cap saturation — one window, and it is a named covariate of this family

`saturated_slice_count` is **1**; `skipped_slice_count` is **0**.

| call | window | window seconds | raw response | accepted |
|---|---|---|---:|---:|
| `4346818` | `#w0035` | 3,060–3,150 s | 3,135 chars | 0 |

`reproduction.obs_loop` treats a slice that reaches the 1,024-token cap as a truncated decode rather
than a transcript end: it contributes the empty string to the stitched hypothesis and is counted,
never scored silently. 3,135 characters against a ~1,550-character typical window is over-generation,
not a window lost at random.

**The four cells in this family saturate four different calls, and the comparator saturates none.**

| cell | saturated | windows |
|---|---:|---|
| comparator `SAEA-E21-FULL44-DIRECT-BASELINE-V2` | **0** | — |
| `SAEA-E21-KC-E1-BRIEF-44-V1` | 2 | `4360717` @1,980–2,070 s, `4363614` @2,340–2,430 s |
| `SAEA-E21-KU-E1C-PLACEBO-44-V1` | 2 | `4384683` @1,260–1,350 s, `4397829` @360–450 s |
| **this cell** | **1** | **`4346818` @3,060–3,150 s** |

All five saturated windows are on five different calls, so the covariate is arm-local everywhere and
no window is a shared exclusion. It costs this measurement 90 s of 141,345.85 — 0.064 % of the audio.

**Its cost is bounded and reported rather than repaired.** The comparator charged **250 reference
words** to `4346818#w0035`; this cell's deletions on that call rose by **242**. The two numbers agree
to within 8, so the one saturated window accounts for essentially the whole of that call's regression.
Dropping the call entirely moves the corpus-WER delta from −0.9281 to **−0.9825** [−1.0822, −0.8828]:
the cell's headline result is, if anything, held back by it.

---

## 6. The instrument, and the defect it carries

The per-window decomposition runs through `analysis.e21_window_pairing` — the registered instrument
of `SAEA-E21-MF-WINDOW-PAIRING-V1` — and its own proof,
`assert_stitch_reproduces_outputs`, rebuilt every one of the 44 sealed hypotheses byte for byte on
both arms before a single per-window number was computed. 1,593 windows paired on both sides, **0
span misalignments**: every paired window id carries the same cut span in both arms, which is what
makes the pairing exact.

`stitched_windows_from_trace` recovers a window's text from its raw `MODEL_RESPONSE` and does not
read the `OBS` record's `obs_saturated`, so on a call that saturated it re-admits exactly the text
`obs_loop` excluded from the stitch. **The KC-E1 closure named that defect** and it is repaired under
the instrument's own row. This verdict did **not** re-implement the reader and did **not** edit the
shared module: it applies `obs_loop`'s own quarantine rule on top of the instrument's output — a
saturated window's recovered text is forced empty — and then lets
`assert_stitch_reproduces_outputs` prove the result, so a wrong quarantine could not have passed
silently. On the comparator, which saturated nothing, the step is a measured no-op; on this cell it
touches exactly `4346818#w0035`. Validated on both sealed sibling traces first: the comparator passes
raw and after the quarantine, `SAEA-E21-KU-E1C-PLACEBO-44-V1` is refused raw and passes after it,
quarantining exactly the two windows its own receipt names.

---

## 7. Cost, serving and throughput

| | realized | ceiling |
|---|---:|---:|
| model calls | **1,593** | 1,750 |
| speech-audio seconds (metered cut span) | **141,345.8527** | 150,000 |
| delivered speech-audio seconds | 144,531.8527 | — |
| GPU hours (manifest nvidia-smi sampler) | **0.9765** | 1.2 |
| paid API spend | 0 | 0 |

At the same geometry and the same convention: the sealed comparator realized 0.9734 GPU-h, KC-E1
0.9948 and KU-E1c 1.0087. This cell is the cheapest of the three post-comparator passes despite
carrying 2.3 % more audio per request.

**Attached, never started, never stopped.** `saea-driver run --session-receipt` reached the
coordinator's resident session `e21-np6-c36864-20260907b` through `core.session.attach_session`;
geometry `-c 36864 -np 6`, 6 slots of 6,144 tokens, port 8080, fragment
`q4km-e21-buf90-mmproj-gpu-04ccc72a-np6`, bf16 mmproj resident on the GPU, raw audio, no feature
cache. `scripts/run_arm_sequence.sh` was deliberately not used: its pre-arm cleanup refuses while a
serving session is resident and its smoke step would have spawned a second llama-server.

Monitor summary over this attempt's own contact window (23:12:50Z to 00:45:19Z):

| wall | active | parked | requests | mean / peak power | mean util | host free min | VM avail min |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5,544.30 s | 4,549.85 s (82.1 %) | 994.45 s (17.9 %) | 1,584 | 74.08 W / 99.51 W | 60.8 % | 12.96 GB | 24.89 GB |

`requests_delta` is a lower bound at the 10-second sampling interval; the charged count is 1,593.
Host free memory bottomed at **12.96 GB**, above the 12 GB floor `serving_session.sh start` refuses
below and above KU-E1c's 12.18 GB, with the VM's working set peaking at 38.93 GB of its 44 GB cap.
A CPU-only sibling task ran for part of the pass.

**Throughput: 1,593 windows in 5,549 s (92.48 min) — 17.225 windows per minute**, realized realtime
factor **40.21×**, 3,515.49 GPU-seconds, latency summed over 6 slots 31,999.2 s, CPU 346.2 s, peak
VRAM 22,726 MiB, gate setup 9.9 s. The fastest pass of the family: comparator 16.38, KC-E1 16.244,
KU-E1c 16.482 windows per minute. Finalize took a further 2,807 s and the whole-manifest score read
its own pass.

Scored **once** over the complete manifest, never sharded: `saea-driver finalize` verified the bundle,
scored all seven declared scorers and settled the attempt `FINALIZED` (MLflow run
`37dbaa7004d547cf9bda1e85fcd58b7c`), and a `core.scoring_batch` read with `--include-per-sample` over
the same complete manifest reproduced its aggregates.

---

## 8. What this cell cannot conclude

* **Nothing about the Earnings-21 test split, and nothing published.** These are the 44 discovery
  calls. A media-changed number is never reported as a like-for-like reproduction of a published
  protocol, and none of ConEC's Table 2 rows appended silence.
* **Nothing about generalization or superiority**, and nothing that belongs to Stage-3. §9 of the
  preregistration applies unchanged.
* **Not that the tail is universally good.** It is admitted on neither this carrier's own rule nor,
  yet, anywhere: the clause it fails is the one asking whether anything got worse, and the answer at
  the imported margin is *cannot tell*.
* **Not that the encoder pad was removed.** Appending whole mel blocks leaves the residue
  `(n_samples // 160) % 100` unchanged, so the same padded block is still sent, two seconds later.
* **Not that a positive result here predicts SLURP or Audio2Tool.** That is the hypothesis under
  test, and §5 signed three different predictions precisely so the answer cannot be read backwards
  from whichever cell flew first.

---

## 9. The prediction of §5, checked

> **Earnings-21: largest effect, same direction, smaller in size than Earnings-22's.** The population
> is 65.5 % mid-speech-ended and the task is transcription, so the insertion-collapse mechanism
> applies almost unchanged. But the unit is a 90-second window, not a 3-second utterance […]
> Predicted corpus-WER delta **−0.2 to −1.5 points** from the sealed 8.1995.

**Observed −0.9281. The prediction holds**, comfortably inside its own range and roughly a seventh of
Earnings-22's −6.6988, exactly as the 90-second-versus-3-second argument said it would be. The
mechanism prediction holds too: the gain is an insertion collapse and it concentrates on the
mid-speech-ended windows.

**What §5 did not predict, and what this cell adds to the transfer story**, is that the repair is not
free. Earnings-22's verdict already found the substitution-plus-deletion block 87 operations worse;
at Earnings-21's scale that cost is 324 operations, and because ConEC's definition cannot attribute
an insertion to a tag, it surfaces as a **demonstrated PERSON-entity regression** on the very metric
the Earnings mechanism ladder is built around. The honest one-line reading of this cell is: **the
silence tail transfers to Earnings-21 as an insertion repair, it is worth 0.93 corpus-WER points, and
it costs entity accuracy.**

---

## 10. Named next steps

1. **Measure this carrier's own same-request null.** §3 said it in advance and this cell is why it
   matters: two of the four agentic metrics failed non-inferiority against an *imported* margin
   narrower than their own noise, so the admission question is currently unanswerable rather than
   answered. This is the named next cell.
2. **The PERSON regression is a finding, not a nuisance.** A tail that trades insertions for
   deletions will move every insertion-blind metric the wrong way; any future Earnings media
   convention has to be judged on the S+D block as well as on corpus WER.
