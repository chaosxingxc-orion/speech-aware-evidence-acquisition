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
"closes early" mechanism can carry at most about **5 of the 61** excess errors, under 8 % of the harm.

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
