# K1 OFFLINE GATE — hybrid dense+lexical ranking RAISES recall@5 by +1.8 pp,
# and the gain does NOT survive the rest of the mechanism. **DO NOT FLY.**

Date: 2026-08-25. Status: **ITERATION-TIER DESIGN INPUT — computed, zero contacts, every
fidelity gate passed.** Row `SAEA-SN-MF-K1-HYBRID-RANKING-GATE` (registered `437015d6`, BEFORE any
computation). Module `src/speech_aware_evidence_acquisition/analysis/k1_hybrid_ranking_gate.py`.
Receipt `docs/checks/speech-aware-evidence-acquisition/2026-08-25-k1-hybrid-ranking-gate/gate-report.json`
(sha256 `252d53f3…5556f`). Authority: the key-construction agenda plan §3 item K1 under the
baseline-lock verdict §5.

**Spend: 0 frozen-core contacts, 0 embedding-tool contacts, 0 tokenizer contacts, 0 audio seconds,
0.0 GPU hours, 0 new dependencies. Offline guard armed before the first input was opened and
recorded 0 outbound connection attempts against zero targets. Wall 278.9 s.**

---

## 1. The one-line answer

The pre-registered falsifier — *"if hybrid ranking does not raise recall@5, key representation is
not the lever either, and the residual is task-intrinsic"* — **does NOT fire**. Recall@5 rises on
the primary population, from **0.744 to 0.762 (+1.8 pp, +9 of 500)** under reciprocal-rank fusion.

And the recommendation is still **do not fly**, for three reasons the falsifier did not name and
this gate measured anyway:

1. **The same rule costs recall@1**: 0.636 → 0.590 (−4.6 pp, −23 of 500). Every hybrid rule that
   helps at k=5 hurts at k=1, on every population, under both query normalizations.
2. **The measured conversion anchors price that trade badly.** Gold at the fused top-1 converts at
   **98.2%**; gold at fused rank 2–3 at **69.6%**. The hybrid moves probability mass *down* the
   fused list, which is the wrong direction through the only channel that reaches the core.
3. **At the supply level — the only channel that can change an answer — the activated second
   dimension newly supplies gold on 12 currently-wrong trajectories and REMOVES gold supply from
   40 currently-correct ones** (unexposed 500, Q-RAW; 12 vs 29 under Q-VAL). The central
   conversion projection is **negative on all four populations under both normalizations**.

So the honest verdict is not the falsifier's binary. It is: *the key plane is not saturated —
lexical evidence genuinely reaches keys the dense channel misses — but the frozen cell's
`top_l = 3` / 98.2%-at-top-1 conversion profile converts precision, not recall, and a rule that
buys recall@5 with recall@1 is a net loss in this cell.*

---

## 2. What was computed, and what proves it

### 2.1 The fidelity gate — PASSED, count for count

Before any hybrid number was believed, this module recomputed the gold-facet recall@k that the
two sealed one-shot reads published, from its own code path, and matched every cell:

| population | k=1 | 2 | 3 | 5 | 8 | 10 | 16 | 32 | 64 | 128 | gold absent |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **DEV-1000 unexposed 500** recomputed | 318 | 352 | 362 | **372** | 389 | 396 | 408 | 433 | 443 | 470 | 0 |
| published (lock read) | 318 | 352 | 362 | **372** | 389 | 396 | 408 | 433 | 443 | 470 | 0 |
| **DEV-500 NEW400** recomputed | 235 | 266 | 272 | **286** | 297 | 305 | 314 | 337 | 353 | 372 | 0 |
| published (DEV-500 read) | 235 | 266 | 272 | **286** | 297 | 305 | 314 | 337 | 353 | 372 | 0 |

0.636 / 0.704 / 0.724 / **0.744** / 0.778 / 0.792 / 0.816 / 0.866 / 0.886 / 0.940 on the unexposed
500 — the lock read's numbers, reproduced.

### 2.2 The other gates, all of which had to pass before a number was reported

| gate | result |
|---|---|
| flown retain/dispatch decision reproduced per sample | r4 100/100, r5 100/100, NEW400 400/400, **NEW500 497/500** |
| the 3 NEW500 deviations | **all three are exactly the v2 δ-override fires** (`002303`, `002955`, `014737`), 0 unexplained — the arm flew v2, the locked cell is v1 |
| flown SUPPLY reproduced exactly on dispatched samples | 37/37, 33/33, 130/130, **163/163** |
| committed report anchor (retain-primary count, correct count) | r4 63/63 and 72/72, r5 67/67 and 72/72 |
| **the query text this gate tokenizes is byte-identical to the text the flight embedded** | **1,100 / 1,100** — every direct-decode text re-hashes to the `text_sha256` its own landed query-vector record carries |
| this module's own baseline arm reproduces the imported replay's supply | 1,100 / 1,100 |
| the single-dimension degeneracy the plan asserts | **confirmed on all 1,100**: `dims_total = 3`, every facet carries exactly one dimension |
| vectorised cosine vs `kb_policy._cosine` | 9,900 probes, all agreed to 1e-9 |

### 2.3 The lexical channel, exactly as registered

- **Tokenizer**: lowercase, then every maximal run of `[a-z0-9]`. No stemming, no stoplist, no
  language resource. The same function tokenizes both sides.
- **Corpus**: the 11,514 content-facet texts (the TRAIN utterances), sha256
  `4b971c1a…3da1`. 5,219 terms, 78,402 postings, mean document length 6.945 tokens.
- **BM25**: Okapi, `k1 = 1.2`, `b = 0.75`, Robertson/Lucene non-negative IDF
  `ln(1 + (N − df + 0.5)/(df + 0.5))`; each DISTINCT query term contributes once (no
  query-term-frequency saturation), which makes every per-document weight query-independent and
  precomputable.
- **Bounded similarity** (Part B only): `bm25 / max_d bm25`, per query, order-preserving, `[0,1]` —
  needed because percept admission and the ranker's `max_cosine` both compare against a
  cosine-scaled threshold.
- **Two query normalizations**, both registered in advance: **Q-RAW** = the direct-decode text
  verbatim (literally what the flight embedded; mean 9.3 tokens) and **Q-VAL** = the same text
  minus the five constant JSON schema key tokens `{scenario, action, entities, type, filler}`,
  which every query emits and which therefore carry no per-sample information (mean 4.6 tokens).
- **Fusion grid**: `LIN-w` = `(1−w)·z(cos) + w·z(lex)` with each channel z-normalized per query over
  the full 11,514-facet population, `w ∈ {0.25, 0.50, 0.75}`; `RRF-60` = `1/(60+rank_dense) +
  1/(60+rank_lex)`; `TIEBREAK` = cosine order, exact float ties broken by lexical score.

**The lexical channel is real, not vestigial.** It touches ~586 facets per query on average, and
on its own — with no dense signal at all — its top-1 facet bears the gold intent on **154 / 500**
(Q-RAW) and **200 / 500** (Q-VAL) of the unexposed samples.

---

## 3. Part A — the per-rule recall table (the falsifier quantity)

Gold-facet position in the FULL ordering of all 11,514 content facets. Deterministic arithmetic
over the sealed query vectors: these numbers carry **no decode variance at all**.

### 3.1 DEV-1000 unexposed 500 — the primary population, the one the lock statistic used

| rule | Q-RAW @1 | @3 | **@5** | @8 | Q-VAL @1 | @3 | **@5** | @8 |
|---|---|---|---|---|---|---|---|---|
| **DENSE-ONLY** (flown) | **0.636** | 0.724 | **0.744** | 0.778 | 0.636 | 0.724 | 0.744 | 0.778 |
| LIN-0.25 | 0.568 | 0.676 | 0.746 | **0.780** | 0.572 | 0.684 | 0.740 | **0.784** |
| LIN-0.50 | 0.448 | 0.582 | 0.674 | 0.754 | 0.448 | 0.634 | 0.706 | 0.778 |
| LIN-0.75 | 0.384 | 0.526 | 0.594 | 0.672 | 0.424 | 0.546 | 0.684 | 0.762 |
| **RRF-60** | 0.590 | 0.718 | **0.762** | 0.776 | 0.590 | 0.700 | **0.758** | 0.770 |
| TIEBREAK | 0.636 | 0.724 | 0.744 | 0.778 | 0.636 | 0.724 | 0.744 | 0.778 |

### 3.2 DEV-500 NEW400

| rule | Q-RAW @1 | @3 | **@5** | @8 | Q-VAL @1 | @3 | **@5** | @8 |
|---|---|---|---|---|---|---|---|---|
| **DENSE-ONLY** | **0.5875** | 0.680 | **0.715** | 0.7425 | 0.5875 | 0.680 | 0.715 | 0.7425 |
| LIN-0.25 | 0.5650 | 0.675 | 0.715 | 0.7650 | 0.5575 | 0.660 | 0.725 | 0.7700 |
| LIN-0.50 | 0.4725 | 0.580 | 0.6575 | 0.7300 | 0.4600 | 0.630 | 0.680 | 0.7625 |
| LIN-0.75 | 0.4100 | 0.5575 | 0.605 | 0.6700 | 0.4275 | 0.5625 | 0.6725 | 0.7625 |
| **RRF-60** | 0.6125 | 0.685 | **0.735** | 0.7650 | 0.6150 | 0.670 | **0.735** | 0.7625 |
| TIEBREAK | 0.5875 | 0.680 | 0.715 | 0.7425 | 0.5875 | 0.680 | 0.715 | 0.7425 |

### 3.3 DEV-100 r4 / r5 (the same 100 samples flown twice)

| rule | r4 Q-RAW @1 / @5 | r5 Q-RAW @1 / @5 |
|---|---|---|
| **DENSE-ONLY** | 0.62 / **0.71** | 0.63 / **0.70** |
| LIN-0.25 | 0.57 / 0.71 | 0.58 / 0.71 |
| LIN-0.50 | 0.46 / 0.64 | 0.47 / 0.64 |
| LIN-0.75 | 0.39 / 0.56 | 0.40 / 0.56 |
| RRF-60 | 0.63 / 0.70 | 0.64 / 0.71 |
| TIEBREAK | 0.62 / 0.71 | 0.63 / 0.70 |

### 3.4 Three structural readings

- **`TIEBREAK` is an exact no-op, everywhere.** Its numbers are bit-identical to `DENSE-ONLY` on
  every population. This is not a defect of the implementation: dense cosines over 1,024-dimensional
  float64 embeddings are essentially never exactly equal at the top of the list, so a rule that only
  acts inside an exact tie never acts. Reported so the grid is not read as three live rules and one
  that "failed".
- **Rank fusion beats score fusion here.** `RRF-60` is the only rule that raises recall@5 on the
  primary population, and it is the only rule whose recall@8 stays essentially level rather than
  being bought with the head of the list. The z-normalized linear rules degrade monotonically in
  `w`: at `w = 0.75` recall@1 falls from 0.636 to 0.384. The lexical score distribution is far more
  skewed than the cosine distribution, so z-normalization does not put the two channels on
  comparable footing, which is exactly why RRF exists.
- **Q-VAL helps the weak rules and does not help the good one.** Stripping the constant schema keys
  roughly halves the query length and lifts `LIN-0.50` (0.674 → 0.706) and `LIN-0.75`
  (0.594 → 0.684) — i.e. it removes noise the heavy-lexical rules were drowning in — but it slightly
  *lowers* `RRF-60` (0.762 → 0.758) and `LIN-0.25` (0.746 → 0.740). The schema tokens are noise;
  removing noise matters only where the noise was dominant.

---

## 4. The decision quantity — newly reachable, and what it costs

**"How many currently-WRONG dispatched trajectories would newly have gold within the top-5?"** —
reported with its loss side, because a rule that promotes five errors and demotes five correct
answers has changed nothing.

### 4.1 Rank level (gold facet crosses the k=5 boundary)

DEV-1000 unexposed 500: **163 dispatched**, of which **51 are wrong with gold outside the top-5**
(the eligible pool) and **100 are correct with gold inside the top-5** (the at-risk pool).

| rule | Q-RAW gained | lost | net | Q-VAL gained | lost | net |
|---|---|---|---|---|---|---|
| LIN-0.25 | **11** | 5 | **+6** | 10 | 4 | **+6** |
| LIN-0.50 | 12 | 13 | −1 | 11 | 9 | +2 |
| LIN-0.75 | 12 | 20 | **−8** | 11 | 14 | −3 |
| **RRF-60** | 6 | 2 | **+4** | 6 | 2 | **+4** |
| TIEBREAK | 0 | 0 | 0 | 0 | 0 | 0 |

DEV-500 NEW400 (130 dispatched; 44 eligible, 81 at risk): LIN-0.25 **+9/−8 = +1** (Q-RAW),
**+8/−4 = +4** (Q-VAL); RRF-60 **+5/−4 = +1** (Q-RAW), **+5/−2 = +3** (Q-VAL).

DEV-100 r4 (37 dispatched; 12 eligible, 23 at risk): LIN-0.25 +1/−1 = 0; RRF-60 +1/−2 = −1.
DEV-100 r5 (33 dispatched; 11 eligible, 20 at risk): identical shape.

**Reading**: at best the rank-level net is **+6 of 500** — and that is a raw rank-crossing count,
before admission, before the target budget, and before conversion.

### 4.2 Supply level (the second dimension actually ACTIVATED inside the frozen policy)

This is the honest decision quantity: `recall_scores` carries a `content_lex` dimension beside
`content`, the REAL `kb_policy` ranker and fuser run on it at the frozen `τ = 0.65 / m = 5 / c = 2 /
top_l = 3`, and the α-blend head re-decides retain-versus-dispatch.

| population | supply changed | **newly gold-supplied (currently wrong)** | **gold supply LOST (currently correct)** | facets admitted by the lexical dimension alone |
|---|---|---|---|---|
| NEW500 Q-RAW | 488 / 500 | **12** | **40** | 1,417 |
| NEW500 Q-VAL | 472 / 500 | **12** | **29** | 1,235 |
| NEW400 Q-RAW | 376 / 400 | 11 | 21 | 1,116 |
| NEW400 Q-VAL | 361 / 400 | 9 | 13 | 951 |
| DEV-100 r4 Q-RAW | 97 / 100 | 3 | 7 | 285 |
| DEV-100 r5 Q-RAW | 96 / 100 | 3 | 7 | 282 |

**The loss side exceeds the gain side on every population under both normalizations, by a factor
between 1.4 and 3.3.** That is the finding.

Two disclosures on this table. (i) The 3 dispatch-decision flips the NEW500 replay shows against
the flown record are **exactly the three v2 δ-override samples** (`002303`, `002955`, `014737`) —
the arm flew v2, this replay is v1, and the lock verdict already removed that override from the
locked cell; they are not a hybrid effect. (ii) "supply changed" is near-total (488/500) because a
second recall dimension changes the candidate UNION on almost every trajectory; most of those
changes never reach the core, because 340 of the 500 retain their direct answer and never dispatch.

---

## 5. FALSIFIER VERDICT

> **Pre-registered (agenda plan §3, K1):** *"if hybrid ranking does not raise recall@5, key
> representation is not the lever either, and the residual is task-intrinsic."*

**VERDICT: NOT FIRED. Recall@5 IS raised.**

| population | dense recall@5 | best hybrid recall@5 | rule | Δ |
|---|---|---|---|---|
| **DEV-1000 unexposed 500 (primary)** | **0.744** | **0.762** | RRF-60 / Q-RAW | **+1.8 pp (+9 of 500)** |
| DEV-1000 unexposed 500 | 0.744 | 0.758 | RRF-60 / Q-VAL | +1.4 pp (+7 of 500) |
| DEV-500 NEW400 | 0.715 | 0.735 | RRF-60 / both | +2.0 pp (+8 of 400) |
| DEV-100 r4 | 0.71 | 0.71 | LIN-0.25 / TIEBREAK | **0.0 pp** |
| DEV-100 r5 | 0.70 | 0.71 | LIN-0.25, RRF-60 | +1.0 pp (+1 of 100) |

The falsifier's antecedent is not met, so its conclusion (*"key representation is not the lever
either, and the residual is task-intrinsic"*) is **not licensed by this gate**. The key plane is
not saturated: a channel that has never been used reaches gold facets the dense channel misses,
and it does so consistently across two disjoint held-out populations at both the 400 and 500
tier.

**What the falsifier did not ask, and what decides the flight.** The falsifier was written as a
single-sided recall test, and a single-sided recall test cannot see the two facts that dominate
this cell:

1. **Recall@1 falls under every rule that raises recall@5.** On the primary population RRF-60
   trades **−23 samples at k=1** for **+9 samples at k=5**.
2. **The conversion anchors are steeply rank-dependent.** 98.2% at fused top-1, 69.6% at fused
   rank 2–3, 0.0% absent. Demoting one gold from rank 1 to rank 2–3 costs 0.286 expected correct
   answers; promoting one gold from absent to rank 2–3 buys 0.696. At 23 demotions against 9
   promotions that arithmetic does not close.

This is recorded as a **defect in the falsifier's construction, not a licence to reinterpret its
result**: a future item's falsifier on this cell must be two-sided (recall@1 AND recall@5, or the
conversion-weighted quantity directly), because in a cell whose top-1 conversion is 98.2% the head
of the list is worth more than its tail.

---

## 6. Conversion projection, and the band

Construction, identical to the supply-budget projection §7 and stated so a reviewer can audit the
split between arithmetic and pricing:

- a trajectory that **RETAINS** under the hybrid answers with its own direct decode, whose score
  against gold is **computed exactly** — the dispatch anchors, measured only on dispatched
  trajectories, are never applied to it (340 of 500 on NEW500);
- a dispatched trajectory whose supplied set is **byte-identical** to the flown one receives a
  byte-identical evidence prompt and carries its **sealed outcome exactly**;
- **only** a dispatched trajectory whose supply CHANGED is priced, at the measured anchor for
  wherever gold sits under the hybrid, **symmetrically** for currently-correct and currently-wrong
  trajectories. Pessimistic prices every changed trajectory one rank-band worse; optimistic
  assumes no currently-correct trajectory is disturbed and every gold-supplied error converts at
  the top-1 rate.

| population | sealed baseline | priced trajectories | **pessimistic** | **central** | **optimistic** |
|---|---|---|---|---|---|
| **NEW500 Q-RAW** | 379 / 500 = 75.8% | 157 | 347.9 (**−6.21 pp**) | 365.5 (**−2.70 pp**) | 396.7 (**+3.55 pp**) |
| **NEW500 Q-VAL** | 379 / 500 | 145 | 356.4 (−4.53 pp) | 375.2 (**−0.75 pp**) | 399.7 (+4.13 pp) |
| NEW400 Q-RAW | 289 / 400 = 72.25% | 121 | 264.9 (−6.02 pp) | 281.7 (**−1.82 pp**) | 298.8 (+2.45 pp) |
| NEW400 Q-VAL | 289 / 400 | 108 | 268.8 (−5.06 pp) | 285.9 (**−0.77 pp**) | 295.9 (+1.72 pp) |
| DEV-100 r4 Q-RAW | 72 / 100 | 35 | 64.5 (−7.51 pp) | 70.2 (**−1.83 pp**) | 74.9 (+2.95 pp) |
| DEV-100 r5 Q-RAW | 72 / 100 | 31 | 65.4 (−6.59 pp) | 70.5 (**−1.49 pp**) | 74.9 (+2.95 pp) |

**No trajectory anywhere in this table was priced at the unanchored rank-4+ extrapolation** — the
frozen `top_l = 3` keeps every priced sample inside the measured anchor set, which is the one place
this projection is stronger than the supply-budget one.

**The central estimate is NEGATIVE on every population under both query normalizations.** The band
straddles zero only because the optimistic edge assumes, by construction, that not one of the 40
currently-correct trajectories that lose gold supply is actually damaged — an assumption this
gate's own supply table contradicts.

### 6.1 Which tier could evaluate it

The registered variance channel is **±2 per 100 at 8-slot decode**. Against it:

| tier | central projected effect | variance width | resolvable? |
|---|---|---|---|
| DEV-100 (100) | −1.8 samples | ±2 | **no** — the plan's §4 statistical-honesty clause, confirmed |
| DEV-500 NEW400 (400) | −7.3 samples | ±8 | **no** — inside one variance width |
| DEV-1000 NEW500 (500) | −13.5 samples | ±10 | **marginal at best** |

The plan said "NEW400-tier or larger". **Verified against this gate's own numbers, that is too
generous: NEW400 cannot resolve an effect of this size, and even the 500-sample unexposed tier sits
at roughly one variance width.** A flight that could actually decide this question is ≥1,000
samples — and the sign of the central estimate says the question is not worth 1,000 samples of
decode.

Note the asymmetry in what carries variance: the **retrieval** numbers in §3 and §4 are exact
arithmetic over sealed query vectors and carry no decode variance whatever; only the **projected
accuracy** in this section does.

---

## 7. The `agreement` finding — the STRUCTURAL claim, independent of accuracy

The plan's §2.1 defect is confirmed on all 1,100 samples before it is repaired: `dims_total = 3`,
every facet carries exactly one dimension, `agreement` is the constant 1/3, and the ranker's score
is the affine map `0.5·cos + 0.0667`.

With the lexical dimension active, that is no longer true:

| quantity | NEW500 Q-RAW | NEW500 Q-VAL | NEW400 Q-RAW | NEW400 Q-VAL |
|---|---|---|---|---|
| `dims_total` observed | **4** | 3 or 4 | **4** | 3 or 4 |
| candidate facets with `dims_hit = 2` | 293 / 9,707 = **3.02%** | 338 / 9,584 = **3.53%** | 242 / 7,758 = 3.12% | 286 / 7,633 = 3.75% |
| **top-m (m=5) candidates with `dims_hit = 2`** | 293 / 2,500 = **11.7%** | 338 / 2,500 = **13.5%** | 242 / 2,000 = 12.1% | 286 / 2,000 = 14.3% |
| samples with at least one two-dimension candidate | **181 / 500** | **217 / 500** | 154 / 400 | 186 / 400 |

**`agreement` now takes two distinct values, 1/4 and 2/4, instead of one.** At the frozen
`w_agree = 0.2` that is a score separation of **0.05** between a two-dimension and a
one-dimension candidate at equal maximum signal — equivalent to a **+0.10 cosine bonus**, which is
large relative to the cosine spread at the top of these lists. **The rank-weight family is
therefore structurally non-degenerate for the first time**, and `w_cos` / `w_prior` / `w_agree` are
no longer three knobs two of which multiply constants.

Three qualifications, all measured rather than assumed:

- The `dims_total = 3` rows under Q-VAL are samples whose lexical channel recalled **nothing**
  (1 sample on NEW500, 2 on NEW400): after schema-key removal the query has no token that appears
  anywhere in the 11,514-utterance corpus. Under Q-RAW this never happens.
- **1,417 facets on NEW500 (Q-RAW) were percept-admitted by the lexical dimension ALONE** — their
  dense cosine is below `τ = 0.65` and only the bounded lexical similarity cleared the bar. That is
  the second dimension doing exactly what a second dimension is for, and it is also a large part of
  why 40 currently-correct trajectories lose their gold supply: admitting more also crowds the
  `top_l = 3` target budget.
- **This finding is independent of §5 and §6 and survives them.** "The rank-weight family became
  non-degenerate" is a true statement about the score's shape; it is not a claim that re-weighting
  now buys accuracy. Whether it does is a separate experiment, and this gate's §6 says the obvious
  first parameterisation of it does not.

---

## 8. Cost note

Measured, not modelled:

| quantity | measured |
|---|---|
| BM25 index build, whole 11,514-document corpus, once per snapshot | **0.054 s** (5,219 terms, 78,402 postings) |
| **lexical scoring, per query, whole corpus** | **9.64 × 10⁻⁵ s = 0.096 ms** |
| lexical scoring per 1,000 trajectories | **0.096 s** |
| the plan's reference: `multidim_recall` × 2 per trajectory | 2.294 s per trajectory = **2,294 s per 1,000** |
| **lexical channel as a fraction of that reference** | **4.2 × 10⁻⁵** |
| this module's own vectorised dense cosine, per sample, whole corpus | **0.98 ms** |

**The lexical channel is free.** Under the registered scoring form every per-document BM25 weight
is query-independent, so the index is built once and a query is a gather plus a `bincount`. Adding
it costs about one ten-thousandth of what the existing content dimension already costs.

**And the plan's engineering note needs correcting in the useful direction.** It reads
"any second dimension multiplies that [1.147 s]" — it does not: the 1.147 s belongs to the
EXISTING scalar cosine sweep in `kb_policy.multidim_recall`, and this module's vectorised
equivalent measures **0.98 ms for the same 11,514-facet sweep, a ~1,170× speedup, with a
9,900-probe agreement check against `kb_policy._cosine` at 1e-9**. So:

- **Vectorisation is NOT a prerequisite blocker for K1** — it is a demonstrated ~30-line change
  whose fidelity this gate already proved, and it is worth landing on its own merits for the
  ~19 min of CPU per 1,000 trajectories it removes from every future campaign.
- The lexical channel adds no measurable cost on top of it.

---

## 9. What to do

**Do not fly K1 in this form.** The central projection is negative on all four populations, the
supply-level loss side outweighs the gain side everywhere, and no available DEV tier resolves an
effect this small.

What the gate legitimately hands the next item:

1. **The lexical signal is real and unexploited.** On its own, the lexical channel's top-1 facet
   bears the gold intent on 154–200 of 500 unexposed samples, and it admits 1,417 facets the dense
   channel would refuse. The problem is not that lexical evidence is absent; it is that
   *rank-level fusion is the wrong way to spend it in a cell whose top-1 conversion is 98.2%.*
2. **The cell's real constraint is precision at rank 1, not recall at rank 5.** Any future key-plane
   change should be evaluated on a conversion-weighted objective
   (`0.982·P(rank 1) + 0.696·P(rank 2–3)`), not on recall@k. Re-read against that objective, every
   rule in §3 is a loss.
3. **`agreement` is now a live signal** (§7) and the rank-weight family is non-degenerate. That is
   a genuine structural unlock, and it is the one durable asset this gate produced. It should be
   spent on a rule that ADDS a second dimension without perturbing the dense head order — e.g. the
   lexical dimension used only to break the target-budget contest at `top_l`, never to reorder the
   facet list — rather than on a rule that re-ranks the whole 11,514.
4. **K2 and K3 are unaffected.** This gate says nothing about pair-boundary discriminative text
   (K2) or field-role-constrained contact-0 (K3), both of which act on the CONTENT of the key text
   and the query rather than on the ranking function over a fixed corpus.

**Scope, binding.** DEV-tier iteration design input. Nothing here authorizes test contact, a
superiority claim, a generalization claim, or Stage-3 activity. FINAL60 and test remain untouched.
No knob was changed, no arm was re-flown, no new sample was touched, and no new gold surface was
opened — every sample scored here had its gold lawfully opened at an earlier registered seal.
