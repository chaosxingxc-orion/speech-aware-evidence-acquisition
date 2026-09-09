# Verdict — SLURP's own greedy replicate null, measured

Run `SAEA-SLURP-DEV1000-NULL-REPLICATE-V1`, attempt `attempt-20260909T043847Z-f4306e`, `COMPLETED`
and `FINALIZED` on study commit `c6e8e95a`, **1,000 of 1,000 rows**, one attempt, none aborted,
**no recovery re-registration used**, `study_repo_dirt` empty. The cell of
`docs/readiness/2026-09-09-slurp-own-null-replicate-v1-preregistration.md`, flown on owner
Decision 10 of 2026-09-08 recorded in its own exposure row before the first contact.

---

## 0. The answer

**The same request, flown twice, moves intent accuracy by +0.50 pp, CI90 [−0.4049, +1.4341], and
micro SLU-F1 by +0.2873, CI90 [−0.9088, +1.4521]. Eighteen per cent of the 1,000 rows emitted
different bytes. Every one of the eleven measured metrics moved UP with nothing changed.**

| | value |
|---|---:|
| intent accuracy, comparator `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1` | 73.10 |
| intent accuracy, replicate | **73.60** |
| paired delta, **speaker-clustered CI90 — the honest interval** | **+0.5000** [−0.4049, +1.4341] |
| **the null's own CI90 half-width on intent — the new margin** | **0.9195** |
| SLU-F1 (micro), comparator → replicate | 35.80 → **36.09** (**+0.2873** [−0.9088, +1.4521]) |
| **the null's own CI90 half-width on micro SLU-F1** | **1.1804** |
| raw completion identity rate | **82.10 %** (821 of 1,000) |
| projected-intent flip rate | **5.20 %** (52 of 1,000) |
| falsifier — the request side identical on every row | **PASS, 1,000 of 1,000** |
| identity gate — the comparator reproduces its nine published anchors | **PASS** |
| verdict | **there is none: this cell admits and refutes nothing** |

**This cell has no factor.** It is the sealed comparator's own configuration, flown again. There is
no ADMITTED / NOT-ADMITTED line here and no claim about the tail, the media or any knob. What it
produces is a table of intervals and the margins section 4 of the preregistration derives from them.

**Three things it settles, and none of them is comfortable.**

1. **The imported ±0.60 pp margin was too narrow on every single metric**, by 1.28x to 2.12x — and
   too narrow is the dangerous direction: it made SLURP cells look more decidable than they are.
   Earnings-21's imported margin was wrong in both directions; SLURP's is wrong in one, uniformly.
2. **The imported 28.1 % flip floor was 1.57x too high.** Measured on this arm, this geometry and
   this build, byte-identical prompts return different text on **17.9 %** of rows, not 28.1 %.
3. **The silence-tail cell's clause 3 is not satisfiable by a null.** Its per-scenario harm bound —
   at most 2 of 18 scenarios lose anything, none by more than 3.0 pp — is broken by *this* cell,
   which moved nothing: **5 scenarios lose intent and the worst loses 5.13 pp.** A gate that a null
   fails is measuring the decoder, not the mechanism.

---

## 1. The falsifier, run before any score file was opened

**Section 2 HOLDS ON 1,000 OF 1,000 ROWS.**

| check | result |
|---|---:|
| rows paired against the comparator's roster | **1,000** |
| rows missing / extra | **0 / 0** |
| `MODEL_REQUEST` payload identical after removing `request_id` and `decoding_params.id_slot` | **1,000** |
| speech packet sha256 equal to the comparator's | **1,000** |
| delivered `audio_seconds` equal to the comparator's | **1,000** |
| `mmproj_loaded` false on both arms | **1,000** |
| rendered instruction sha256 = `4073f79e…0d37db` | **1,000** |
| **per-row `prompt_tokens` equal to the comparator's** | **1,000** |
| sample ids carrying a variant suffix | **0** |
| **disagreeing rows** | **0** |

**The prompt-token delta histogram is `{0: 1000}`** — not a total that happens to agree, but every
single row at exactly the comparator's token count, with no other value in the histogram. The two
excluded fields are the pair `docs/readiness/2026-09-06-slurp-evo-s1-round-1-verdict.md` section 1
already names as moving between any two runs for scheduling reasons alone; everything else the
request carries — the 7,583-character instruction, the packet hash, the media path, the audio
seconds, the history, the supplied evidence, temperature, seed and `max_tokens` — is inside the
compared bytes.

And at the manifest level:

| | comparator | replicate |
|---|---:|---:|
| calls | 1,000 | 1,000 |
| metered speech seconds | 2,884.793687 | 2,884.793687 — identical |
| **prompt tokens** | **2,190,161** | **2,190,161** — identical |
| completion tokens | 26,495 | **26,570** (+75) |

**The request side is provably unchanged and only the completions moved.** That is what makes this
a null rather than a cell.

The composed identity holds too, re-read from `FlightRuntime.preflight` before the first contact and
again from the sealed manifest: config hash `6be064ba…b894f`, protocol hash `7e83a705…951b2`, split
identity `8580d199…1e3c84`, split id `DEV-1000` — the comparator's three. The cell introduced no
config fragment; it composed the comparator's own four. The same three were computed **offline, with
zero contacts, before the exposure row was written**, so the anchor was not a post-hoc observation.

---

## 2. The identity gate, passed before the first contrast

The sealed comparator reproduces the 2026-09-06 projection-v2 re-lock's own published anchors from
its own sealed bytes, to the digit, on all nine:

| anchor | published | reproduced |
|---|---:|---:|
| scenario | 82.60 | **82.60** |
| action | 74.60 | **74.60** |
| intent | 73.10 | **73.10** |
| entities strict | 21.91 | **21.91** |
| Word-F1 | 33.69 | **33.69** |
| Char-F1 | 38.20 | **38.20** |
| SLU-F1 | 35.80 | **35.80** |
| unparsed | 3 | **3** |
| port-vs-official identity check | passed | **passed** (abs diff 0.0) |

Both arms were scored **once each over their complete 1,000-row manifest** through
`core.scoring_batch` with `include_per_sample=True`, one job per manifest, never sharded, 2 of 2
succeeded, both `verified: true`. The paper-facing scorer is `slurp-slu-official-projected-v2` and
`slurp-slu-f1-normalized-v1` runs beside it as the secondary. Neither is declared by the sealed
manifests — `scorers` is a baseline-fragment key and enters `config_hash`, which this cell holds
fixed — so **one derived manifest per arm** was written beside each sealed one, differing from it in
the `scorers` list and in nothing else; the sealed manifests were not touched and their sha256s are
in the receipt.

---

## 3. The null table — the deliverable

Speaker-clustered bootstrap, **124 clusters** (largest 55 rows, median 6), 10,000 replicates, seed
20260903, CI90, signed **replicate minus comparator**. The scenario-stratified family (18 gold
strata) is reported beside it; the two cannot be crossed on this carrier, because a SLURP speaker
records across scenarios.

### 3.1 The paper-facing micro (pooled) metrics

| metric | comparator | replicate | delta | speaker-clustered CI90 | **half-width** | vs imported 0.60 |
|---|---:|---:|---:|---|---:|---:|
| **SLU-F1 (micro)** | 35.8020 | 36.0893 | **+0.2873** | [−0.9088, +1.4521] | **1.1804** | **1.97x too narrow** |
| entities strict F1 (micro) | 21.9105 | 22.6667 | **+0.7562** | [−0.5225, +1.9988] | **1.2607** | 2.10x |
| Word-F1 (micro) | 33.6868 | 34.1168 | +0.4300 | [−0.7093, +1.5541] | **1.1317** | 1.89x |
| Char-F1 (micro) | 38.2007 | 38.3040 | +0.1033 | [−1.1904, +1.3582] | **1.2743** | 2.12x |

### 3.2 The per-row metrics

| metric | comparator | replicate | delta | speaker-clustered CI90 | **half-width** | saves | harms | ties | sign p |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| **intent (scenario+action)** | 73.1000 | 73.6000 | **+0.5000** | [−0.4049, +1.4341] | **0.9195** | 18 | 13 | 969 | 0.473 |
| scenario | 82.6000 | 83.0000 | +0.4000 | [−0.4188, +1.2322] | **0.8255** | 15 | 11 | 974 | 0.557 |
| action | 74.6000 | 75.0000 | +0.4000 | [−0.5882, +1.3699] | **0.9790** | 19 | 15 | 966 | 0.608 |
| entities strict F1 (per row) | 12.9593 | 13.2440 | +0.2848 | [−0.5063, +1.0329] | **0.7696** | 24 | 17 | 959 | 0.349 |
| Word-F1 (per row) | 18.8716 | 19.0595 | +0.1879 | [−0.6313, +0.9653] | **0.7983** | 39 | 34 | 927 | 0.640 |
| Char-F1 (per row) | 21.1274 | 21.1872 | +0.0599 | [−0.8437, +0.9050] | **0.8743** | 45 | 31 | 924 | 0.135 |
| SLU-F1 (per row) | 19.7464 | 19.8857 | +0.1393 | [−0.6963, +0.9413] | **0.8188** | 43 | 33 | 924 | 0.302 |

**Every metric moved up, and not one interval excludes zero.** That is what a null should look like
on the sign test and it is what it looks like — but the *magnitudes* are the point: 18 rows saved
and 13 harmed on intent, 43 saved and 33 harmed on SLU-F1, with nothing changed at all.

**Read the two estimands together.** Intent's half-width (0.9195) is *larger* than per-row SLU-F1's
(0.8188) but *smaller* than micro SLU-F1's (1.1804). The paper-facing SLU-F1 is a pooled ratio over
entity TP/FP/FN, and pooling over a resampled cluster set is noisier than averaging a bounded per-row
F1. **35.80 is a micro figure, so the margin that guards it is 1.1804, not 0.8188** — and a cell that
quotes the per-row number while claiming the micro headline is using the wrong margin.

### 3.3 Both weightings agree

The equal-stratum weighting — the unweighted mean over the 18 gold scenarios of each scenario's own
mean per-row delta — puts intent at **+0.3711** [−0.6421, +1.3092] speaker-clustered (half-width
0.9756) against the natural-mixture **+0.5000**. Nothing here depends on the scenario mixture.

The scenario-stratified family gives intent [−0.4000, +1.4000] (half-width 0.9000) and micro SLU-F1
[−0.8003, +1.4046] (1.1025) — the same picture, marginally tighter, which is why the
speaker-clustered family is the one read as honest.

### 3.4 The normalized secondary agrees in sign on eleven of eleven

`slurp-slu-f1-normalized-v1` puts micro SLU-F1 at 36.4281 → 36.6277 (**+0.1996**, half-width
1.2549) and intent at **+0.7000** (half-width 1.0139). **Every one of the eleven metrics has the
same sign under both scorers, and every normalized half-width is wider than its official
counterpart** — so nothing in section 4's margins is an artifact of the projection, and a cell read
under the normalizer needs a slightly wider bar, not a narrower one.

Full tables: `verdict/null-table.md`.

---

## 4. The margins, and the rule now in force

Section 4 of the preregistration fixed the rule before any number existed:

> For each metric, the SLURP non-inferiority margin becomes **the half-width of this null's own
> speaker-clustered CI90 on that metric**. A future SLURP cell demonstrates an effect on metric *m*
> iff its CI90 is disjoint from **this null's measured interval**, not merely from zero.

| metric | **margin (measured)** | **null interval to be disjoint from** |
|---|---:|---|
| **intent (scenario+action)** | **0.9195** | [−0.4049, +1.4341] |
| scenario | **0.8255** | [−0.4188, +1.2322] |
| action | **0.9790** | [−0.5882, +1.3699] |
| **SLU-F1 (micro, paper-facing)** | **1.1804** | [−0.9088, +1.4521] |
| entities strict F1 (micro) | **1.2607** | [−0.5225, +1.9988] |
| Word-F1 (micro) | **1.1317** | [−0.7093, +1.5541] |
| Char-F1 (micro) | **1.2743** | [−1.1904, +1.3582] |
| SLU-F1 (per row) | **0.8188** | [−0.6963, +0.9413] |
| entities strict F1 (per row) | **0.7696** | [−0.5063, +1.0329] |
| Word-F1 (per row) | **0.7983** | [−0.6313, +0.9653] |
| Char-F1 (per row) | **0.8743** | [−0.8437, +0.9050] |

These replace, **for SLURP only** and from this cell's closure:

* the silence-tail admission rule's imported **±0.60 pp** (Earnings-22's half-width on the same
  scale);
* **section 6.4 of `docs/readiness/2026-09-08-slurp-slot-knowledge-views-kv-v1-preregistration.md`**,
  whose own text says "the moment the SLURP own-null replicate lands, KV-0's non-inferiority margin
  is restated from it and this section is superseded". It is superseded here: **KV-0's
  non-inferiority margin on micro SLU-F1 is 1.1804 pp, and on the per-row estimand 0.8188 pp**;
* the **28 % flip floor** that KU-S3, KU-S4 and the logprob judge probe read against. The measured
  figure is **17.9 %** on raw completions and **5.2 %** on the projected intent.

They are never carried to Earnings-21, which has its own
(`SAEA-E21-FULL44-NULL-REPLICATE-V1`), or to Audio2Tool, which still has none.

**The caveat travels with the margin.** A single replicate measures this null with 1,000 rows and
124 clusters and no more. The intervals are themselves uncertain; they are better margins than
imported ones, not exact ones, and every verdict that uses them must name this cell.

### 4.1 The imported margin was wrong in one direction, on every metric

| metric | imported | measured | ratio |
|---|---:|---:|---:|
| entities strict F1 (micro) | 0.60 | 1.2607 | **2.10x** |
| Char-F1 (micro) | 0.60 | 1.2743 | 2.12x |
| SLU-F1 (micro) | 0.60 | 1.1804 | 1.97x |
| Word-F1 (micro) | 0.60 | 1.1317 | 1.89x |
| action | 0.60 | 0.9790 | 1.63x |
| **intent** | 0.60 | **0.9195** | **1.53x** |
| Char-F1 (per row) | 0.60 | 0.8743 | 1.46x |
| scenario | 0.60 | 0.8255 | 1.38x |
| SLU-F1 (per row) | 0.60 | 0.8188 | 1.36x |
| Word-F1 (per row) | 0.60 | 0.7983 | 1.33x |
| entities strict F1 (per row) | 0.60 | 0.7696 | 1.28x |

**Eleven of eleven too narrow.** Earnings-21's null found its imported margin 2.6x too wide on one
metric and 1.6x too narrow on another — unrelated to the carrier's own noise in either direction.
SLURP's is unrelated in one direction only, and it is the direction that lets a null through: a
SLURP cell whose interval cleared ±0.60 pp was never thereby shown to have cleared this carrier's
replicate noise.

---

## 5. Re-reading the silence-tail cell against the measured null — 2026-09-09

`SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-V1`
(`docs/readiness/2026-09-09-slurp-silence-tail-v1-verdict.md`) was judged against the imported
±0.60 pp and came out **NOT ADMITTED** on all three clauses. Re-read against the margins measured
here — **a re-reading of already-sealed numbers against a new reference, not a new measurement: that
cell is not re-flown, not re-scored, and its NOT ADMITTED status is not reopened by this cell** —
three of its findings move, and the net is that it stays NOT ADMITTED for a narrower and better
reason.

**Clause 1 fails harder, and the effect is not separable from the null at all.** The clause asked
the intent CI90 lower bound to exceed the bar. Sealed lower bound **+0.1934** against a measured
margin of **0.9195**: FAIL, by 0.73 pp of lower bound instead of 0.41. And the sharper test — the
one section 4 fixes — is disjointness: the tail's intent interval **[+0.1934, +2.4262]** and this
null's **[−0.4049, +1.4341]** **overlap over 1.24 pp of their length**. The tail's +1.30 pp is
**1.41 null half-widths**. Against Earnings-21's tail cell, whose corpus-WER effect stood at 16 null
half-widths and was disjoint from its null, this one is not in the same class: **a +1.30 pp intent
movement on 1,000 SLURP rows is inside this carrier's own greedy replicate noise**, and this null
moved intent +0.50 pp — **38 % of the tail's entire headline — with nothing changed at all.**

**Clause 2 flips from FAIL to PASS, and the tail verdict's narrow scenario failure was an artifact
of the imported margin.** Clause 2 asked SLU-F1, scenario and action to be non-inferior. It failed on
scenario alone, at **−0.6921** against a bar of −0.60 — a miss of 0.09 pp that the tail verdict
itself called "the clause failing on imprecision, not on measured harm". Measured, scenario's margin
is **0.8255**, so −0.6921 clears it; action's −0.0987 clears −0.9790; SLU-F1's per-row +0.1455 clears
−0.8188. **All three pass at the measured margins.** The tail verdict's clause-2 failure does not
survive this measurement, and this verdict records that correction rather than restating it.

**Clause 3 cannot decide anything, because a null fails it.** The rule allows at most 2 of 18
scenarios to lose intent and none to lose more than 3.0 pp. **This cell, with no factor at all,
loses intent on 5 scenarios and its worst loses 5.13 pp** — `takeaway` −5.13, `audio` −3.33, `music`
−1.96, `transport` −1.67, `datetime` −1.64, two of them past the 3.0 pp bound. The tail cell's own
failure was 5 losers and −10.26 pp, on `takeaway`, and **`takeaway` and `music` lose under the pure
null too** (`music` by exactly the same −1.96 pp). The tail's `takeaway` regression is about twice
the null's and its `recommendation` −3.33 and `iot` −3.28 are *not* reproduced here — so something
in that cell may still be real on those strata — but **the clause as written is not a discriminating
gate at n = 39 to 61 per stratum and must not be used as one until it is restated against per-stratum
noise this cell has now measured.**

**Net.** `SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-V1` **stays NOT ADMITTED**, and the reason narrows
from three clause failures to one that matters: its intent gain is not distinguishable from this
carrier's replicate noise. Nothing in the SLURP ladder moves; the comparator does not move; no
pending cell is invalidated.

---

## 6. What actually moved — the flip ladder

| surface | rows | rate |
|---|---:|---:|
| raw completion bytes **identical** | 821 | **82.10 %** |
| raw completion bytes differ | 179 | **17.90 %** |
| parsed slot set differs | 144 | 14.40 % |
| parsed `(scenario, action)` differs | 59 | 5.90 % |
| **projected intent differs** (what the paper-facing scorer reads) | **52** | **5.20 %** |
| parse success itself flips | 3 | 0.30 % |
| speaker clusters carrying at least one flip | 84 of 124 | 67.7 % |

**Divergence lands mostly in the slot fillers, not in the label.** Of the 179 rows that came back
different, 144 changed their slot set and only 59 changed their raw label — and after the legal-label
projection, 52. That is why intent's margin (0.9195) is narrower than micro SLU-F1's (1.1804)
despite intent being the coarser metric: free-text fillers are where a greedy decoder wanders.

**Against the imported floor.** EVO-S1 round 1 measured 286 of 1,019 byte-identically prompted rows
(28.1 %) returning different text on a different SLURP arm at this build. Measured here on the
comparator's own arm: **17.9 %**. The imported floor was **1.57x too high**, which is the opposite
direction from the margin error and for a plain reason — EVO-S1's arm rendered a longer, richer
schema block into the prompt, and more prompt is more room to diverge. **A flip rate is not
transferable between arms**, and this is the measurement that shows it.

`unparsed` moved 3 → 4 under the null. One row's parseability is inside this carrier's noise.

---

## 7. Per stratum and per cluster

**Per gold scenario** (full table `verdict/per-scenario-table.md`): intent deltas span **−5.13
(`takeaway`, n = 39) to +5.41 (`cooking`, n = 37)** with five scenarios losing, five exactly flat and
eight gaining. Per-row SLU-F1 deltas span **−5.11 (`alarm`) to +3.42 (`calendar`)**. Raw flip rates
span 3.3 % (`weather`) to 29.3 % (`alarm`).

**No per-scenario SLURP reading is admissible without its own replicate.** A five-point per-stratum
swing on this carrier costs nothing but a second pass of the same request.

**Per speaker cluster** (full table `verdict/per-cluster-table.md`): **22 of 124 clusters moved on
intent and 54 on per-row SLU-F1**, with nothing changed. The extremes are small clusters —
`spk:MO-038` +50.0 pp on n = 2, `spk:FO-228` −33.3 pp on n = 3, `spk:FO-180` +25.0 on n = 4 — which
is precisely the churn the cluster bootstrap is resampling over and the reason the honest interval is
as wide as it is.

---

## 8. The signed predictions of section 5, checked

| prediction | outcome |
|---|---|
| intent delta inside −0.8 to +0.8 pp | **HELD** — +0.5000 |
| the intent CI90 half-width is **below** the imported 0.60 | **FAILED** — 0.9195, i.e. 1.53x **above** it |
| raw text flip rate between 15 % and 40 % | **HELD** — 17.90 % |
| projected-intent flip rate under 5 % | **FAILED, narrowly** — 5.20 % |
| SLU-F1's half-width above intent's | **HELD on the micro estimand** (1.1804 > 0.9195), **FAILED on the per-row one** (0.8188 < 0.9195) |
| unparsed moves by at most 2 from 3 | **HELD** — 3 → 4 |

**The informative failure is the second, and it failed for the reason Earnings-21's failed in
reverse.** The prediction reasoned that a 64-token completion on a 2.9-second utterance has less room
to diverge than a 1,024-token, 90-second Earnings window, and that is true at the *unit* level —
17.9 % of SLURP rows differ against 66.1 % of Earnings windows. But Earnings-21 averages its churn
over 359,765 reference words and lands at a 0.058-point corpus half-width, while SLURP averages over
**1,000 rows** and lands at 0.92. **Unit volatility and aggregate stability are different
quantities, and the denominator decides which one you get.** The prediction imported the wrong one.

The fifth prediction's split is worth keeping: the estimand, not the metric, sets the margin.

---

## 9. Cost, serving and throughput

| | realized | registered ceiling | this cell's own budget |
|---|---:|---:|---:|
| model calls | **1,000** | 1,050 | 1,008 |
| speech-audio seconds (metered) | **2,884.7937** | 3,000 | 2,884.7937 |
| GPU hours (contact window) | **0.0637** | 1.0 | 0.30 stop threshold |
| paid API spend | 0 | 0 | 0 |

**Throughput: 1,000 rows in 229.38 s — 261.6 rows/min, 4.36 rows/s**, mean latency 1.695 s over 8
slots. Preprocess promoted 1,000 packets in 10.50 s (95.2 packets/s, 8 workers, every packet a cache
hit from the comparator's own base root). Seal took 114 s and the declared-scorer pass 78 s; takeoff
to receipt 7 min 37 s.

**The cost side is a null measurement too.** The identical 1,000 requests took **225.5 s** on the
comparator and **229.4 s** here — a **1.7 % spread on byte-identical work**, and the completion-token
total moved 26,495 → 26,570 (+0.28 %) while latency summed over 8 slots moved 1,621.68 → 1,695.32 s
(+4.5 %). No SLURP wall-clock or GPU-hour comparison below about 5 % is meaningful.

**Attached, never started, never stopped.** `FlightRuntime.serve` bound the coordinator's resident
session **`slurp-np8-base-c65536-20260909`** through `core.session.attach_session`
(`session_reused: true`, `stop_serving` a no-op returning `null`); geometry `-c 65536 -np 8`, 8 slots
of 8,192 tokens, port 8080 on loopback, fragment
`q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64`, mmproj-free with
`LLAMA_SPEECH_FEATURE_ROOT` on the comparator's own base packet root
`/home/chao/feat-cache/slurp-q4km-packets-04ccc72a`. The session was still live with the port
listening after the flight.

Monitor summary over this attempt's own contact window (04:39:22.72Z to 04:43:12.10Z), 21 samples at
10 s:

| wall | active | parked | requests | mean / peak power | mean util | host free min | VM avail min |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 221.14 s | 221.14 s (100 %) | 0.00 s (**0.0**) | 160 | 88.12 W / 94.47 W | **79.10 %** | 26.91 GB | 40.80 GB |

`requests_delta` is a lower bound at the 10-second sampling interval; the charged count is 1,000. The
card was **never idle inside the window**. Host free memory bottomed at 26.91 GB, far above the 12 GB
floor `serving_session.sh start` refuses below, and the VM working set peaked at 21.96 GB.

---

## 10. What this cell cannot conclude

* **Nothing about the SLURP `test` split or FINAL60.** Neither is touched; these are the 1,000 devel
  rows, and no new speech exposure occurred — the request bytes are the comparator's own.
* **Nothing about any mechanism.** No factor was moved. Section 5's re-reading of the tail cell is a
  re-reading of that cell's already-sealed numbers against a new reference, not a new measurement of
  it, and it changes that cell's *reason*, never its status.
* **Not that these margins are exact.** 1,000 rows, 124 clusters, one replicate. A second replicate
  would produce a different interval, and the margins should be re-measured if the geometry, the
  build, the prompt or the population changes.
* **Not that the flip rate transfers.** 17.9 % is this arm's rate. EVO-S1's 28.1 % was a different
  arm's, and section 6 is the demonstration that the two differ by more than half again.
* **Not that a null of this size is small.** It is not: 0.92 pp on intent and 1.18 pp on micro SLU-F1
  is larger than most gains this study has reported on this carrier.
* **Nothing about Earnings or Audio2Tool.** Neither was contacted, and neither inherits these
  margins.

---

## 11. Named next steps

1. **Re-read every open SLURP claim against the table in section 4.** The KV slot-knowledge-view
   family (KV-0 first), KU-S3, KU-S4 and the logprob judge probe all currently read against an
   imported bar that is 1.3x to 2.1x too narrow. KV-0's own preregistration section 6.4 is
   superseded by section 4 above and must be restated before that cell flies.
2. **Restate the per-scenario harm bound, or drop it as a gate.** Clause 3 as written is failed by a
   null. Either it becomes a bound relative to the per-stratum noise this cell measured, or it stops
   carrying admission weight on this carrier.
3. **A SLURP effect now needs to be big or the roster needs to be bigger.** An intent margin of
   0.92 pp on DEV-1000 means a mechanism must move roughly 2 pp before its interval can be disjoint
   from this null. The cells in the ladder are aiming at less than that; more rows, or a paired
   design with more replicates, is the honest answer.
4. **Audio2Tool still has no measured null.** This is now the second carrier of three where the
   imported margin was demonstrably wrong. There is no reason to expect it is right on the third.

---

## 12. Receipt

`docs/checks/speech-aware-evidence-acquisition/2026-09-09-slurp-own-null-replicate-v1/`, with
`MANIFEST.sha256` over every file:

| path | what |
|---|---|
| `falsifier.py` | the archived copy of the section 2 request-side falsifier, run on 1,000 rows **before any score file was opened**. Zero contacts |
| `read.py` | the archived copy of the single registered read: the score batch, the identity gate, both interval families, both estimands, both weightings, the secondary, the flip ladder and the margins. Scoring-side only, zero contacts |
| `build_result_summary.py` | the assembler; reads nothing but `verdict/read.json` and `flight-1000/falsifier.json` |
| `flight-1000/dry-run.json` | the zero-contact preflight that checked the identity anchor before the flight |
| `flight-1000/falsifier.json` | the 1,000-row falsifier result, including the `{0: 1000}` prompt-token delta histogram |
| `flight-1000/flight-receipt.json` | the flight: preflight, preprocess, serve (attached), `run_phases`, seal, score |
| `flight-1000/monitor-contact-window.json` | the monitor summary over the flight's own contact window |
| `verdict/read.json` | the full read — every aggregate, every interval, every half-width, the per-scenario and per-cluster tables, both weightings, the secondary |
| `verdict/result-summary.json` | the machine form of this document |
| `verdict/null-table.md` | the null table, micro and per row, both families, with the secondary beside it |
| `verdict/per-scenario-table.md` | all 18 gold scenarios with intent, SLU-F1 and flip rates |
| `verdict/per-cluster-table.md` | all 124 speaker clusters |
| `verdict/batch-summary.json` | the verified `core.scoring_batch` record: one job per manifest, `include_per_sample`, never sharded |

Exposure row `SAEA-SLURP-DEV1000-NULL-REPLICATE-V1`, registered and committed before the first
contact and closed COMPLETED with hashes. Sealed artifacts under
`SPEECHRL_DATA_DIR/runs/SAEA-SLURP-DEV1000-NULL-REPLICATE-V1/attempt-20260909T043847Z-f4306e/`:
run manifest `e229d1d3…82b1`, outputs `e34e18b2…1a87`, trace `6d1103ef…b970`, trace manifest
`c9bf9650…640f`, scores `9d87942f…5dcb`. None of them enter Git.
