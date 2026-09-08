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
