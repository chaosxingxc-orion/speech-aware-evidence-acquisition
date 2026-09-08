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
