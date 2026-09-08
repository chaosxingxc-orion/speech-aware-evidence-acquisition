# Where OBS-E1 lost the names — the model-free decomposition of its PERSON harm

`SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1` was **REJECTED as HARM**: the speaker-turn transport unit
bought **+1.0487** points of corpus WER and sold **2.0912** points of ConEC-mirror PERSON entity WER
(`docs/readiness/2026-09-08-e21-obs-speaker-turn-units-v1-verdict.md`, receipt
`docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-obs-e1-flight-v1/`). That verdict names
the sign and the size. **This note names the sixty-one errors.**

Exposure row `SAEA-E21-MF-OBS-E1-HARM-DECOMPOSITION-V1` (`model-free-check`), registered and
committed before the first sealed artifact was opened. **Zero frozen-core, GPU, server, tokenizer,
tool, embedder, network, audio-decode and paid-API contacts.** Receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-obs-e1-person-harm-decomposition/`.

**Nothing here is a decision, a preregistration or a GO.** OBS-E1 stays REJECTED, no successor cell is
registered, no knob is tuned, and §5's hypothesis table is a **design with prices attached** that
licenses no contact.

---

## 0. The instrument, and the two anchors it had to clear first

The read pairs **every PERSON reference word** in both arms. Its unit of account is the
`(reference word, entity ID)` pair, because fstalign's `RecordTagWer` — which
`reproduction.conec_entity_scoring` mirrors — visits the stitch once per tag, so a word carrying two
PERSON IDs is two PERSON reference words. Each word carries, in each arm, the alignment operation
that consumed it and the transport span it was charged to, both taken from that arm's own sealed
alignment through the registered instruments (`analysis.e21_window_pairing`,
`reproduction.conec_entity_scoring`). New code: `analysis.e21_person_harm` (with
`tests/unit/test_e21_person_harm.py`) and `scripts/e21_obs_e1_person_harm_read.py`.

**Anchor 1 — the pooled rows reproduce both sealed buckets exactly, and the read refuses to write if
they do not.**

| arm | measured PERSON WER | sealed | S | D | reference words |
|---|---:|---:|---:|---:|---:|
| comparator `SAEA-E21-FULL44-DIRECT-BASELINE-V2` | **22.48886** | 22.48886 | 573 | 83 | 2,917 |
| cell `SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1` | **24.58005** | 24.58005 | 619 | 98 | 2,917 |

**Anchor 2 — the paired statistic reproduces the verdict's own.** Through
`build_e21_tail2s_verdict.bootstrap_delta` at seed 20260903 / 10,000 replicates / CI90, clustered by
call: improvement **−2.0911896**, CI90 **[−3.1701, −1.0978]** — the verdict's figure to five
decimals — and saves / harms / ties **10 / 27 / 7**, the verdict's counts exactly.

**Two conventions this note repeats wherever it uses them.**

1. **An insertion can never reach an entity bucket.** fstalign attributes no insertion to a tag (an
   insertion stitch carries no NLP row), so every PERSON number here is `(S + D) / tagged reference
   words` and the whole harm is a substitution/deletion story by construction.
2. **Position in reference words is exact; position in seconds is DERIVED.** The Earnings-21
   reference layer ships **no word timestamps** — its `.nlp` files declare `ts` and `endTs` columns
   and all **362,747** cells on the 44 discovery calls are empty, checked. So a word's distance from
   a transport boundary is measured exactly in reference words, from the arm's own charged
   alignment, and converted to seconds by the **containing span's own local rate** (span seconds ÷
   span reference words). The resolution is that rate: median **0.388 s** per reference word in the
   cell (p05 0.287, p95 0.619) and **0.381 s** in the comparator, so the "0–1 s" bin is about the
   two or three reference words nearest an edge. It is an attribution, never a timestamped
   alignment.

---

## 1. The split: the harm is 46 misheard names and 15 dropped ones

| | comparator | cell | change |
|---|---:|---:|---:|
| **substitutions** | 573 | **619** | **+46** |
| **deletions** | 83 | **98** | **+15** |
| errors (S + D) | 656 | **717** | **+61** |
| reference words | 2,917 | 2,917 | 0 |
| PERSON entity WER | 22.48886 | **24.58005** | **−2.0912** |

**Three quarters of the harm is substitution — misheard names, not dropped ones.** 46 of the 61
excess errors (**75.4 %**) are substitutions and 15 (**24.6 %**) are deletions. Both halves are
separated from zero at the paired grain:

| component | comparator | cell | improvement (positive = cell better) | CI90, 44 clusters |
|---|---:|---:|---:|---|
| **substitution rate** | 19.6435 | **21.2204** | **−1.5770** | **[−2.5868, −0.6684]** |
| **deletion rate** | 2.8454 | **3.3596** | **−0.5142** | **[−1.0247, −0.0304]** |
| error rate | 22.4889 | 24.5800 | −2.0912 | [−3.1701, −1.0978] |

The substitution component carries **75.4 %** of the point estimate and its interval is four times as
far from zero as the deletion component's; the deletion interval clears zero only just
(upper bound −0.0304).

**Per call, both components move the same way and neither is carried by an outlier.** Substitutions
rose on **23** calls, fell on **9** and tied on 12; deletions rose on **18**, fell on **11** and tied
on 15. The worst call is `4344338` at **+9** errors (+7 S, +2 D) over 109 PERSON reference words; the
best four are −3 each. No single call accounts for more than 15 % of the 61.

**Why this matters for what comes next.** A deletion story would point at the transport unit
truncating speech — the tail cell's own mechanism, where an insertion collapse was paid for in
deletions. A substitution story points at something else: the model still emits a word in the name's
place and gets it wrong, which is a **conditioning** failure rather than a **truncation** failure.
Sections 2 to 4 locate it; section 5 prices the four repairs against it.

**One correction to the brief this read was opened with.** It quotes the comparator's PERSON split as
`S 597 / D 83`. The measured split is **`S 573 / D 83`**: 573 + 83 = 656 = 22.48886 % × 2,917, which
is the sealed figure, and 597 + 83 = 680 is not. The deletion figure 83 is right and is the same one
the KC-E1f verdict quotes as its reachable PERSON floor (`83 / 2917 = 2.846 %`).

---

## 2. Position: the harm sits at the unit edge, and 93.4 % of it is within three seconds of one

Every PERSON reference word is binned by its distance to the **nearest boundary of the span it was
charged to** — nearest rather than "from the end", because the instrument charges a deletion to the
span its hypothesis cursor stands in, so a name dropped at the end of unit *k* surfaces at the start
of unit *k+1*; the nearest-boundary distance is invariant to that side. Distances from the start and
from the end are reported separately in §4 so the asymmetry stays visible.

**Binned on the CELL's own unit boundaries. This is the table.**

| distance to the nearest unit boundary | PERSON words | comparator | cell | improvement | excess errors | share of the 61 |
|---|---:|---:|---:|---:|---:|---:|
| **0–1 s** | 592 | 23.649 | **29.223** | **−5.574** | **+33** | **54.1 %** |
| **1–3 s** | 785 | 22.675 | **25.732** | **−3.057** | **+24** | **39.3 %** |
| 3–10 s | 887 | 22.999 | 23.563 | −0.564 | +5 | 8.2 % |
| **> 10 s** | 653 | 20.521 | **20.368** | **+0.153** | **−1** | **−1.6 %** |

**93.4 % of the harm is within three seconds of a unit boundary, and beyond ten seconds there is no
harm at all** — the cell is, if anything, one error better there. The gradient is monotone across all
four bins.

**The control is in the same table, in the comparator column.** Across those four bins the
comparator's own PERSON WER is nearly flat — 23.649 / 22.675 / 22.999 / 20.521, a 3.1-point spread —
so the words the cell puts near a boundary are **not intrinsically harder words**. The cell's spread
over the same words is 29.223 → 20.368, **8.9 points**. The extra spread is what the transport unit
added.

**And the comparator's own boundaries carry none of it.** Binning the same 2,917 words by distance to
the nearest **90-second window** boundary instead:

| distance to the nearest window boundary | PERSON words | comparator | cell | improvement | excess errors | share |
|---|---:|---:|---:|---:|---:|---:|
| 0–1 s | 96 | 33.333 | 36.458 | −3.125 | +3 | 4.9 % |
| 1–3 s | 138 | 26.087 | 26.087 | +0.000 | 0 | 0.0 % |
| 3–10 s | 376 | 22.074 | 21.011 | +1.064 | −4 | −6.6 % |
| **> 10 s** | **2,307** | 21.890 | 24.577 | −2.687 | **+62** | **101.6 %** |

Read this pair carefully, because it says two different things. **First**, a boundary is intrinsically
a hard place for a name *in both arms*: the comparator's own PERSON WER at its own window edges is
**33.3 %** against **21.9 %** in mid-window. **Second**, the cell's harm does not live at the
comparator's edges — 101.6 % of the excess lands in the bin that is more than ten seconds from any
90-second boundary. The harm is attached to the **cell's** boundaries, not to boundaries in general
and not to the words themselves.

### 2.1 The cut essentially never goes through a name

A boundary that fell inside a multi-word name would be the most direct mechanism available, and it is
measured exactly — a mention is SPLIT in an arm when its reference words fall in more than one of
that arm's spans, which needs no timing at all.

| | PERSON mentions | multi-word mentions | split across spans | words in split mentions | errors there |
|---|---:|---:|---:|---:|---:|
| comparator (1,593 windows) | 2,212 | 656 | **4** | 9 | 5 |
| **cell (5,122 units)** | 2,212 | 656 | **1** | 2 | 1 |

**One multi-word PERSON mention out of 656 is cut by a unit boundary** — fewer than the comparator's
four, because a speaker-turn cut lands in a pause by construction. So the harm is **beside** the
name, not **through** it. Whatever the unit boundary does to a name, it does it without touching the
name's own audio.

### 2.2 The gradient is a SHORT-UNIT effect wearing a boundary's clothes

A short unit puts every one of its words near a boundary, so the pooled gradient above cannot by
itself separate "near a boundary" from "in a short unit". Holding the unit's duration class fixed
separates them, and the answer is unambiguous.

| unit duration class | 0–1 s | 1–3 s | 3–10 s | > 10 s |
|---|---|---|---|---|
| **< 10 s** (680 words) | 237 w, **−10.127**, +24 | 307 w, **−7.818**, +24 | 136 w, +0.000, 0 | — |
| **10–60 s** (1,424 words) | 241 w, −3.734, +9 | 370 w, −0.270, +1 | 560 w, −0.893, +5 | 253 w, −1.976, +5 |
| **≥ 60 s** (813 words) | 114 w, **+0.000**, **0** | 108 w, +0.926, −1 | 191 w, +0.000, 0 | 400 w, +1.500, −6 |

**Inside a unit of sixty seconds or more, a PERSON word within one second of the boundary costs
exactly nothing** — 114 words, zero excess errors, at the distance where the pooled table shows
−5.574. **Inside a unit under ten seconds, the same distance costs −10.127.** The boundary is not the
agent. The short unit is, and §3 measures it directly.

---

## 3. Unit properties: it is duration, and the verdict's call-level reading inverts at the unit grain

Every PERSON reference word carries the properties of the plan-v2 unit it fell in, taken from the
committed unit plan (`docs/receipts/obs/e21-speaker-turn-units-v2.json`) and cross-checked against
the flown span to 1e-6 s on all 5,122 units before any table was built.

### 3.1 Duration — the whole story

| unit duration | PERSON words | comparator | cell | improvement | excess errors | share of the 61 |
|---|---:|---:|---:|---:|---:|---:|
| **< 10 s** | 680 | 25.735 | **32.794** | **−7.059** | **+48** | **78.7 %** |
| 10–60 s | 1,424 | 21.910 | 23.315 | −1.404 | +20 | 32.8 % |
| **≥ 60 s** | 813 | 20.787 | **19.926** | **+0.861** | **−7** | **−11.5 %** |

**Units under ten seconds hold 23.3 % of the PERSON words and 78.7 % of the harm. Units of sixty
seconds or more are BETTER in the cell than in the comparator, by seven errors.** The finer ladder is
monotone in duration with no exception:

| unit duration | PERSON words | comparator | cell | improvement | excess errors | share |
|---|---:|---:|---:|---:|---:|---:|
| **< 3 s** | 110 | 24.545 | **39.091** | **−14.545** | **+16** | 26.2 % |
| 3–5 s | 128 | 27.344 | 32.812 | −5.469 | +7 | 11.5 % |
| 5–10 s | 442 | 25.566 | 31.222 | −5.656 | +25 | 41.0 % |
| 10–30 s | 669 | 22.571 | 25.112 | −2.541 | +17 | 27.9 % |
| 30–60 s | 755 | 21.325 | 21.722 | −0.397 | +3 | 4.9 % |
| ≥ 60 s | 813 | 20.787 | 19.926 | **+0.861** | **−7** | −11.5 % |

**PERSON words are four times over-represented in short units.** Units of 1–10 s are 39.2 % of the
5,122 units and carry only 5.8 % of the corpus reference words, but **23.3 %** of the PERSON
reference words. That is what a turn-taking moment is made of — an introduction, a hand-over, "thank
you, next question from" — and it is exactly the material the speaker-turn cut isolates into its own
short contact.

### 3.2 End cut, and ending mid-speech

| unit end cut | PERSON words | comparator | cell | improvement | excess errors | share |
|---|---:|---:|---:|---:|---:|---:|
| pause | 2,668 | 22.639 | 24.175 | −1.537 | +41 | 67.2 % |
| **turn-boundary** (no admissible pause) | 229 | 20.961 | **29.694** | **−8.734** | **+20** | **32.8 %** |
| forced-cap-split | 17 | 23.529 | 23.529 | +0.000 | 0 | 0.0 % |
| call-end | 3 | 0.000 | 0.000 | +0.000 | 0 | 0.0 % |

| does the unit end on an active frame? | PERSON words | comparator | cell | improvement | excess | share |
|---|---:|---:|---:|---:|---:|---:|
| **ends mid-speech** | 192 | 22.396 | **32.812** | **−10.417** | **+20** | 32.8 % |
| ends in a pause | 2,725 | 22.495 | 24.000 | −1.505 | +41 | 67.2 % |

**A unit that ends mid-speech costs seven times as much per word as one that ends in a pause**
(−10.417 against −1.505). Only 564 of the 5,122 units (11.0 %) end mid-speech and they carry 6.6 % of
the PERSON words, yet they account for a third of the harm. This is the one property that is not a
restatement of duration: it is the plan's own rule 2 failing to find a pause.

### 3.3 The two properties the verdict named — and both invert at the unit grain

The OBS-E1 verdict's §4 reported, from **call-level tertiles**, that "the purer the call's units, the
larger the PERSON loss" and that "longer units help corpus WER more and hurt PERSON more". At the
**unit** grain, on the same sealed data:

| property | verdict's call-level reading | measured at the unit grain |
|---|---|---|
| **speaker purity** | purer hurts PERSON more | **flat.** 1 speaker: 2,421 w, −2.065. 2 speakers: 479 w, −2.296. Share = 1.00: 2,431 w, −2.057. Share 0.80–1.00: 417 w, −0.959. **No gradient in either direction.** |
| **unit length** | longer hurts PERSON more | **the opposite, decisively.** −14.545 under 3 s rising monotonically to **+0.861** at ≥ 60 s. |

**Neither call-level statement is wrong and neither is a mechanism.** A call whose units are long on
average is a call with few speaker changes, and its PERSON words still sit in the short units it does
have; the tertile is a property of the call, not of the unit the name was transported in. This note
does not amend the verdict — its tables are correct at the grain they declare — but any successor
design must be built on the unit-grain table, because that is the grain a transport rule acts at.

### 3.4 The two remaining properties

| property | PERSON words | comparator | cell | improvement | excess | share |
|---|---:|---:|---:|---:|---:|---:|
| **speaker changed from the previous unit** | 1,936 | 22.056 | 24.793 | **−2.738** | **+53** | **86.9 %** |
| same speaker as the previous unit (or first) | 981 | 23.344 | 24.159 | −0.815 | +8 | 13.1 % |
| absorbed ≥ 1 v2 sliver | 101 | 19.802 | 23.762 | −3.960 | +4 | 6.6 % |
| absorbed none | 2,816 | 22.585 | 24.609 | −2.024 | +57 | 93.4 % |

**A unit that opens after a speaker change carries 86.9 % of the harm on 66.4 % of the words**, at
more than three times the per-word rate of a unit continuing the same speaker. That is the same
finding as §3.1 seen from another side: a speaker change is what creates a short unit, and it is
where the names are.

**The v2 sliver merges are not implicated.** Only 101 PERSON words sit in a unit that absorbed a
sliver, and they carry 4 of the 61 excess errors. Plan v2's one change from v1 is neither the cause
of the harm nor a defence against it.

---

## 4. Tail or boundary? Neither count — the per-tail cost is not a constant

The question is whether the PERSON loss scales with the number of **tails** (one 2.0-second silence
per contact, a decoding effect) or with the number of transport **boundaries** (a segmentation
effect). The family carries exactly one measurement that separates them.

| cell | contacts | tails | transport boundaries added | PERSON improvement | points per tail |
|---|---:|---:|---:|---:|---:|
| comparator | 1,593 | 0 | 0 | — | — |
| **`SAEA-E21-FULL44-TAIL2S-V1`** | 1,593 | **1,593** | **0** | **−0.6856** [−1.3467, −0.1314] | **−0.00043038** |
| **OBS-E1** | 5,122 | **5,122** | **+3,529** | **−2.0912** [−3.1701, −1.0978] | **−0.00040828** |

**The tail cell is the discriminating point: it added 1,593 tails and zero boundaries, and it lost
PERSON anyway.** Scaling its per-tail cost to OBS-E1's 5,122 tails predicts **−2.2044** against an
observed **−2.0912** — the tail-proportional model **explains 105.4 %** of the harm, leaving a
residual of **+0.113 points** for the 3,529 extra boundaries. On the pooled arithmetic there is no
room for a boundary term at all.

**And the pooled arithmetic is misleading, which is the actual finding.** Every unit carries exactly
one tail, so "per tail" and "per unit" are the same column — and that column is not flat:

| unit duration class | units = tails | share of tails | PERSON words | excess errors | **excess errors per tail** |
|---|---:|---:|---:|---:|---:|
| **< 10 s** | 2,006 | 39.2 % | 680 | **+48** | **+0.02393** |
| 10–60 s | 2,284 | 44.6 % | 1,424 | +20 | +0.00876 |
| **≥ 60 s** | 832 | 16.2 % | 813 | **−7** | **−0.00841** |

**A tail on a short unit costs 2.7 times what a tail on a medium unit costs, and a tail on a unit of
sixty seconds or more has a NEGATIVE cost.** A per-tail constant is refused by the cell's own data;
the aggregate agreement with the tail-proportional prediction is an accident of mixture, not a law.
The same refusal applies to the boundary count from the other direction: the 832 boundaries of the
long units carry **−7** excess errors between them.

### 4.1 The in-cell positional test, and what it says about "closing the segment early"

The hypothesis behind the tail is that the model, told by two seconds of silence that the segment is
over, closes early and drops the trailing names. That predicts an **end-side** concentration.

| position within the unit | PERSON words | comparator | cell | improvement | excess | share |
|---|---:|---:|---:|---:|---:|---:|
| **within 2.0 s of the unit END** | 450 | 25.111 | **30.444** | **−5.333** | **+24** | 39.3 % |
| elsewhere (end measure) | 2,467 | 22.011 | 23.510 | −1.500 | +37 | 60.7 % |
| **within 2.0 s of the unit START** | 667 | 23.088 | **27.436** | **−4.348** | **+29** | 47.5 % |
| elsewhere (start measure) | 2,250 | 22.311 | 23.733 | −1.422 | +32 | 52.5 % |
| within 2.0 s of the 90-second WINDOW end (comparator's own) | 72 | 26.389 | 26.389 | +0.000 | **0** | 0.0 % |

**Both edges are damaged, and the end only slightly more than the start.** Per word, the last two
seconds carry 0.0533 excess errors and the first two seconds 0.0435, against 0.0150 in the interior —
the end is 1.2 times the start, not five times. A pure "closes early and drops the trailing name"
mechanism cannot produce a start-side effect of that size. What both edges share is not the tail; it
is **missing context**: at the start of a unit the model has no preceding speech to condition on, and
at the end it has no following speech.

### 4.2 The deleted names, counted where they fell

| | words | at a span edge | share | base rate over all PERSON words |
|---|---:|---:|---:|---:|
| **cell PERSON deletions**, first or last reference word of the unit | 98 | **17** | **17.3 %** | 9.4 %, so **1.85 times** |
| cell PERSON deletions, within 2 reference words of a unit edge | 98 | 33 | 33.7 % | — |
| cell PERSON deletions, within 2.0 derived s of the unit END | 98 | 22 | 22.4 % | 15.4 %, so **1.46 times** |
| **comparator PERSON deletions**, first or last word of the window | 83 | **1** | **1.2 %** | 1.3 %, so **0.95 times** |
| comparator PERSON deletions, within 2.0 derived s of the window END | 83 | **0** | 0.0 % | — |

**A deleted PERSON word in the cell is 1.85 times over-represented at a unit edge; in the comparator
it is exactly at base rate.** So the cell does drop trailing and leading names more often than chance
— that part of the tail story survives — but it accounts for **17 of 98** deletions, and deletions are
only **15 of the 61** excess errors. Attributing the end-of-unit excess proportionally, the
"closes early" mechanism can carry at most about **5 of the 61** excess errors, roughly 8 % of the
harm.

### 4.3 The answer

**Neither count. The driver is the short unit, and both the tail count and the boundary count are
proxies for it.**

* The **tail count** predicts the pooled number almost exactly (105.4 %) and is refused by the cell's
  own stratification: the per-tail cost varies 2.8 times across duration classes and **changes sign**.
* The **boundary count** is refused outright: the 3,529 extra boundaries leave a residual of +0.113
  points, and the long units' 832 boundaries carry −7 excess errors.
* The **short unit** explains it directly: 78.7 % of the harm on 23.3 % of the PERSON words, monotone
  in duration from −14.545 under 3 s to +0.861 at 60 s or more, with the damage on both edges of the
  unit and only 1.2 times worse on the tail side.
* The **tail is still not innocent**: `SAEA-E21-FULL44-TAIL2S-V1` lost 0.6856 PERSON points with the
  boundaries held fixed, so a tail costs PERSON on its own. Its cost is simply not a constant per
  tail, and on this transport unit it is dominated by the duration effect.

---

## 5. The OBS-E1b hypothesis table — design only, priced, with each candidate's addressable share

**Nothing in this section is registered, preregistered or authorized.** OBS-E1 stays REJECTED, one
experiment stays in flight, and every figure below is a projection under a stated model, never a
measurement. The GPU model is the OBS-E1 verdict's own §7 finding — on this carrier and geometry the
cost tracks **encoded seconds, not requests**, its realized 1.0657 GPU-h landing 2 % above the
audio-proportional floor while the contact-proportional ceiling over-predicted by 2.9× — so every
projection here brackets from the audio side.

**"Addressable share" means the share of the measured 61 excess PERSON errors that sits in the
stratum the candidate acts on.** It is a **ceiling**, not a prediction: a mechanism that reaches a
stratum still has to work there, and none of these has been measured on this transport unit.

| candidate | contacts | delivered audio | GPU-h (proj.) | wall (proj.) | prompt tokens (proj.) | **addressable share of the 61** | what the measurement says |
|---|---:|---:|---:|---:|---:|---:|---|
| **OBS-E1 as flown** | 5,122 | 151,590 s | 1.0657 | 99.4 min | 2,255,812 | — | −2.0912 PERSON, +1.0487 corpus WER |
| **(a) context margin +3 s** | 5,122 | 166,956 s | **1.174** | 109 min | 2,455,570 | **≤ 93.4 %** | the 0–3 s excess (57 of 61) |
| **(a) context margin +5 s** | 5,122 | 177,200 s | **1.246** | 116 min | 2,588,742 | **≤ 93.4 %** | worst request 1,323 of a 6,144 slot (4.6×) |
| **(a) context margin +10 s** | 5,122 | 202,810 s | **1.426** | 133 min | 2,921,672 | **≤ 93.4 %** | worst request 1,388 (4.4×) |
| **(b) tail only on mid-speech ends** | 5,122 | 142,474 s | **1.002** | 93 min | ~2,196,000 | **≤ 67.2 %** | removes 4,558 of 5,122 tails |
| **(c) minimum unit 3 s** | 4,395 | 150,136 s | **1.056** | 98 min | ~2,220,000 | **≤ 26.2 %** | absorbs the 110 words under 3 s |
| **(c) minimum unit 5 s** | 3,854 | 149,054 s | **1.048** | 98 min | ~2,205,000 | **≤ 37.7 %** | absorbs everything under 5 s |
| **(c) minimum unit 10 s** | 3,154 | 147,654 s | **1.038** | 97 min | ~2,190,000 | **≤ 78.7 %** | absorbs everything under 10 s |
| **(d) KC-E1f repair on the units** | **10,244** | 303,180 s | **2.131** | 199 min | **9,703,492** | **≤ 75.4 %** | the substitution half only |
| *(control) fixed 27.60-s windows* | 5,145 | 151,636 s | 1.066 | 99 min | ~2,256,000 | *not a repair* | the preregistration's own OBS-E1b |

### (a) Units with a context margin — deliver +N s of preceding audio, discard its text

**Addressable: ≤ 93.4 %** (57 of the 61 excess errors sit within three seconds of a unit boundary),
and §4.1 says why the mechanism matches the failure: **both edges are damaged, not just the tail
side**, which is what a missing-context failure looks like and not what a truncate-at-the-tail failure
looks like. A margin restores the conditioning the short unit removed, and §2.1 confirms it does not
have to protect the name's own audio — the cut goes through a name once in 656.

**Price: the most expensive of the three cheap options** — +10 % to +34 % delivered audio for a
margin of 3 to 10 seconds, 1.17 to 1.43 GPU-h, 109 to 133 minutes. Contacts are unchanged at 5,122
and the slot is never at risk (the worst request grows from 1,258 to 1,388 tokens against 6,144, a
4.4× margin), so no re-certification is needed.

**The unpriced half is the mechanism, and it is the real cost.** Discarding the margin's text is not
free: the model transcribes what it hears, so the pass must identify and drop the prefix. W2's
re-listen makes the *audio* cheap; it does not make the *text discard* automatic. Options are a
prompt instruction (unverified, and this repository has no measurement of instruction compliance on
this core for a partial-transcription task), an overlap-and-merge alignment (a new mechanism with its
own failure modes), or delivering the margin and accepting the duplication into the stitch (which
would move corpus WER and break the one metric this cell actually won). **A cell for (a) needs its
own model-free wire check on the discard rule before it needs a GPU.**

### (b) No tail except where the unit ends mid-speech

**Addressable: ≤ 67.2 %** — the 41 excess errors on the 2,725 PERSON words in pause-ended units, the
only units that would lose their tail. **But this is the worst-targeted candidate of the four**: those
units carry the harm at **−1.505 per word**, the lowest density in the table, while the 564 units that
would *keep* their tail carry it at **−10.417 per word**. The candidate removes the tail from exactly
the places it is doing the least damage.

**Price: the cheapest thing on the list, and it saves money** — 1.002 GPU-h against the cell's 1.0657
(−6 %), 93 minutes against 99, contacts unchanged, cut audio unchanged. 4,558 tails removed, 564 kept.

**Read it against §4.** A per-tail constant would make this candidate worth 4,558 × 0.00043 = 1.96
points, 94 % of the harm. The cell's own stratification refuses that constant, and the density figures
above are why. **(b) is cheap enough to be worth flying as a diagnostic — it is the clean test of
whether the tail matters at all on this transport unit — but it should not be sold as the repair.**

### (c) Minimum unit duration raised

**Addressable: 26.2 % at 3 s, 37.7 % at 5 s, 78.7 % at 10 s** — the cumulative excess in the duration
ladder of §3.1, which is monotone, so the share is a direct read of the threshold. At 10 s the
candidate absorbs the entire stratum that carries the harm.

**Price: it is free, and slightly cheaper than the cell** — merging every unit under 10 s into its
longer neighbour (plan v2's own rule 4, re-run at the larger threshold) leaves **3,154 units** of the
5,122, 1.038 GPU-h and 97 minutes; at 5 s, 3,854 units and 1.048 GPU-h; at 3 s, 4,395 units and 1.056.
The cut total is invariant by construction — only the tail count moves — so nothing about the media
identity changes.

**Two costs the price table cannot show.** First, this candidate **gives back the thing OBS-E1 bought**:
at a 10-second minimum the mean unit is 44.8 s, halfway back to the 88.7-second window, and the
corpus-WER gain that was worth +1.0487 points is not measured at that mixture. Second, merging past
a diarized speaker change is what rule 4 already permits, and at a 10-second threshold it would do so
1,968 times, which dissolves the owner's thesis — cut by speaker first — on exactly the turn-taking
moments the thesis is about. **A 3-to-5-second threshold keeps the thesis and buys a quarter to a
third of the harm; a 10-second threshold buys four fifths and is a different experiment.**

### (d) The repair pass (KC-E1f) on top of the units

**Addressable: ≤ 75.4 %** — the 46 excess **substitutions**. `reproduction.repair_loop` delivers a
substitution-only splice by construction, so it **cannot** touch the 15 excess deletions; the reachable
PERSON floor on this transport unit is the cell's own deletion rate, `98 / 2917 = 3.360 %`, against
the comparator's `83 / 2917 = 2.846 %`. §1's finding — that three quarters of the harm is
substitution — is what makes this candidate plausible at all, and §1 is also what caps it.

**Its measured effect on the 90-second windows is larger than the harm it would repair**: KC-E1f took
PERSON from 22.489 to **18.752**, an improvement of **+3.737 [+2.653, +4.855]**, against a harm of
2.091. That is a reason to price it, not a reason to expect it: the brief was measured on 1,593
90-second windows and has never been consumed at a 27.6-second unit.

**Price: by far the most expensive, and the cost is superlinear in the transport unit** — **10,244
contacts** (two passes), 2.131 GPU-h, 199 minutes, and **9.7 million prompt tokens against the cell's
2.26 million**. The reason is structural and worth stating plainly: **the brief is a per-contact cost.**
KC-E1f spent about 1,014 tokens of brief per window on 1,593 windows; the same brief on 5,122 units
costs 3.2× that, and it now dominates the request — a unit's own audio is only about 440 prompt
tokens. A finer transport unit makes knowledge supply proportionally more expensive, and that is a
general property of this architecture, not a detail of this cell.

**And KC-E1f is itself REJECTED** (`docs/readiness/2026-09-08-e21-kc-e1f-repair-pass-v1-verdict.md`,
on two guards that failed on one matched value in 9,734 and one insertion in 10,700). A rejected cell
contributes no admitted effect; its PERSON reduction is quoted here as a **price input**, never as an
effect this table claims.

### 5.1 What the four candidates do NOT include, and the honest ranking

**The measurement points at a fifth thing none of the four does: stop making short units.** §3.1 and
§4.3 agree that the harm is the sub-10-second unit, and the two candidates that act on it directly are
(c) — by removing short units — and (a) — by giving them back the context their shortness removed.
(b) acts on the tail, which §4 shows is real but not the driver. (d) acts on the output, after the
damage, and pays three times the cell's cost to do it.

**Ranked by addressable share per GPU-hour, on this measurement alone:**

| | addressable | GPU-h | share per GPU-h | note |
|---|---:|---:|---:|---|
| **(c) minimum 10 s** | 78.7 % | 1.038 | **75.8** | but gives back the corpus-WER gain and the speaker thesis |
| **(a) margin +3 s** | ≤ 93.4 % | 1.174 | **79.6** | the discard rule is unbuilt and unpriced |
| **(b) no tail on pause ends** | ≤ 67.2 % | 1.002 | 67.1 | targets the lowest-density stratum; a clean diagnostic |
| **(c) minimum 5 s** | 37.7 % | 1.048 | 36.0 | keeps the speaker thesis |
| **(d) repair pass** | ≤ 75.4 % | 2.131 | 35.4 | substitutions only; the brief is a per-contact cost |

**The ranking is not a recommendation.** Three things would change it and none is measured: whether
(a)'s discard rule can be built at all, whether (c) at 10 s keeps the corpus-WER gain, and whether the
brief transfers to a 27.6-second unit. What this decomposition licenses is a **model-free** next step —
a wire check on (a)'s discard rule, and a rebuild of the plan at a 3-to-5-second minimum to see what
the mixture does to the unit-grain table — neither of which needs a contact.

---

## 6. What this note cannot conclude

* **Nothing about OBS-E1's status.** It stays REJECTED under its own preregistered rule. This note
  re-reads the sealed data; it amends no verdict and reverses no decision.
* **Nothing paper-facing, in either direction.** n = 44 clusters, below the program's `n >= 400`
  rule; the strata below the top level are thin (the smallest carries 16 PERSON words) and carry no
  intervals of their own. Every stratum table here is a **descriptive decomposition of a measured
  61-error difference**, not an effect estimate.
* **No causal claim about the mechanism inside the core.** The read locates the harm in a stratum; it
  cannot say what the model did, and no instrument here reads a decode's reason.
* **Nothing about ORG, GPE or any other class.** The instrument is class-parametric and was run on
  PERSON only, because PERSON is the class the cell was aimed at.
* **The seconds columns are derived, everywhere.** The reference layer has no timestamps (§0); the
  reference-word columns are the exact ones and the seconds columns are an attribution at a median
  0.388-second resolution. Any reading that needs finer than one reference word is not supported.
* **The successor prices are projections**, under the audio-proportional model the OBS-E1 verdict
  established for this carrier and geometry, and would need their own preregistration, their own
  exposure row and the owner's GO before any of them flies.
