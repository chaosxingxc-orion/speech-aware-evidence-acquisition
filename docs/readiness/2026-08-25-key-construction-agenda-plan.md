# Priority-2 plan — the key-construction agenda (reviewer-grade design)

Date: 2026-08-25. Status: **PLAN — not registered; nothing flies until the owner approves and
each item lands its own registration.** Authority: the baseline-lock verdict §5 (DEV-tier work
above the locked cell is authorized) and the iterate-before-concluding rulings §7.

## 1. Why this is the only remaining lever, and how we know

Four independent measurements at the DEV tier converge on one conclusion:

| lever | evidence | outcome |
|---|---|---|
| retrieval width (k, m) | K-WIDEN K1 FLOWN + offline width-5 replay | supply changed on 32/100 trajectories, **0 width-attributable flips**; 71/100 (Δ−1) |
| supply budget (c, top_l) | projection over 600 sealed trajectories, incl. unlimited budget | **0 newly gold-supplied errors at any variant**; the real cap is `min(c·top_l, k)` and this KB associates ~one value per content facet |
| α / τ / rank weights | DEV-100 rounds 1–2 + counterfactual replays | inert (τ), structurally degenerate (single-dimension facets make `agreement` a constant), or exhausted (α) |
| control-plane dispatch (δ bar) | A4 FLOWN, then the DEV-1000 unexposed read | in-sample 11/11, **out-of-sample 0/3 with 3 damaged** — a hand-fit rule that does not generalize |

Meanwhile the residual is **68–73% recall-limited**: the gold facet exists in the KB but sits
at rank 6–2,023. Reachability at the locked k=5 is 0.744 on the unexposed 500, rising to 0.866
at k=32 and 0.940 at k=128 — headroom exists, but K-WIDEN proved **width cannot collect it**,
because widening only permutes an unsaturated supply. The remaining explanation is that the
**ranking function itself is too weak to bring the right key into the top few** — i.e. the KEY
REPRESENTATION, not the plumbing around it.

## 2. Two named defects in the current key plane (both measured, neither yet fixed)

### 2.1 The multi-dimensional K design is not actually realized

Every facet carries exactly ONE dimension. Consequently `agreement = dims_hit/dims_total` is a
constant 1/3 for every candidate, and content facets carry `max_prior = 0.0`, so the ranker's
score collapses to the affine map `0.5·cos + 0.0667` — **the ranking is identically the cosine
ranking for any positive w_cos**. That is why the rank-weight family measured inert: there is
nothing to weight. The owner's Q-K-V design specified multi-dimensional keys; the flown form
has one dimension.

### 2.2 The dead-direct set is a vocabulary failure with a measured retrieval consequence

33–37% of samples produce a first answer naming no TRAIN intent. Their retrieval is measurably
worse (gold-in-top-5 66.2–67.6% vs 71.6–74.1% for label-recovered samples; gold-facet cosine
0.775 vs 0.828) because the query vector IS the direct answer's embedding. But the deficit is
**entirely in the out-of-vocabulary subset**: the swap-recoverable subset retrieves ABOVE the
live reference (0.869/0.855). A schema that pins field ROLES has a retrieval story; the
label-enum version does not (and was rejected — it would take evidence contacts to zero).

## 3. The agenda — three items, ordered by evidence strength

### K1. Activate a genuine second key dimension (the highest-value structural fix)

**Change**: emit content facets that carry a second, independently matchable dimension —
candidates, in order of expected value: (a) **lexical/BM25 dimension** over the same utterance
text (cheap, complementary to dense cosine, the classic hybrid-retrieval result); (b) **speaker
dimension** (built but never activated: no vectors, no runtime consumption); (c) **prior
dimension** made matchable rather than ornamental.
**Why it is not just another knob**: it changes the SHAPE of the score. `agreement` becomes a
real signal, the rank-weight family becomes non-degenerate, and — critically — a hybrid
dense+lexical ranking is the standard remedy for exactly our failure mode (the right key
present but under-ranked by a single dense signal).
**Offline gate before any flight**: recompute, over the sealed DEV-100/500/1000 records, the
gold-facet rank under the hybrid score. Fly only if it moves gold into the top-5 for a
meaningful number of currently recall-limited errors — the same reachability-ceiling logic that
K-WIDEN failed. **Falsifier: if hybrid ranking does not raise recall@5, key representation is
not the lever either, and the residual is task-intrinsic.**

### K2. Inject the v5 pair-boundary material as discriminative key text

**Change**: the 117 pair-boundary relations already built and validated (leave-one-out balanced
accuracy 0.807) enter the KB as **discriminative content**, not as a separate boundary stage —
i.e. the facet text for confusable siblings carries what distinguishes them.
**Why now**: this is an already-paid asset; the M-line's information audit measured 0.55 bits of
residual conditional entropy that only pair-specific lexical evidence can remove; and the
confusable-sibling class is small but precisely the class where generic exemplars fail.
**Offline gate**: measure whether boundary-augmented facet text changes the gold-facet rank for
the confusable errors specifically (15/111 on NEW400) — small class, so this is a NEW400-tier
experiment at minimum, never a DEV-100 round.

### K3. Field-role-constrained contact-0 (the salvaged part of the rejected E-C)

**Change**: constrain the first answer's FIELD ROLES (scenario/action slots present and typed),
NOT the label vocabulary. The rejected E-C variant forced label recovery on every sample and
thereby took evidence contacts to zero (projected 54–67/100 vs 72 — an off-switch). The
role-constrained version leaves out-of-vocabulary answers out-of-vocabulary (so dispatch is
preserved) while improving the query text that feeds retrieval.
**Offline gate**: the swap-recoverable subset's measured retrieval advantage (0.869 vs 0.828)
is the evidence this could work; project the dispatch-rate change first — **if projected
dispatch drops materially, the change is an off-switch in disguise and is rejected like E-C.**

## 4. Reviewer framing — what this agenda is, and what it is not

- It is **not** hyperparameter search. Every knob-family lever is closed by measurement, and
  each item here changes the representation or the query, not a threshold.
- Each item carries a **pre-registered falsifier** (§3), and each is gated on an offline
  reachability computation before spending contacts — the discipline that has already saved
  three flights (E-C, E-A on DEV-100, K-WIDEN K2).
- The honest prior is modest: reachability at k=32 is 0.866, so even perfect ranking within a
  32-deep window leaves ~13% unreachable; and the DEV-1000 error profile shows a hard core
  (`general_quirky` — SLURP's catch-all — is the single largest confusion for BLEND). A
  reviewer should expect **single-digit pp**, not another +20.
- **Statistical honesty**: every item's effect is smaller than the locked cell's, so DEV-100
  cannot evaluate any of them (its ±2/100 variance channel swallows anything under ~3 samples).
  All three are **NEW400-tier or larger experiments**, read once, with the ablation and
  replication rails the DEV-500 campaign established.

## 5. Sequencing and interaction with priority 1

Priority 1 (Audio2Tool) and this agenda are **independent** and can interleave: A2T's GPU stages
alternate with this agenda's offline gates. If K1's offline gate passes, the hybrid-ranking
change should be tested on SLURP first (where the residual is characterized sample-by-sample)
and only then carried to A2T — otherwise a positive A2T result becomes uninterpretable across
two simultaneous changes.

**Engineering note carried into both plans**: `multidim_recall` costs a measured 1.147 s per
call over 11,514 facets and runs twice per trajectory, i.e. +19 minutes of pure CPU per 1,000
trajectories. Any second dimension multiplies that. Vectorization / pre-indexing of the facet
matrix is a prerequisite for K1 at 1,000-sample scale, and is pure engineering — no scientific
registration needed, but it must land before K1's flight.

## 6. K1 gate outcome (2026-08-25) — the falsifier was mis-constructed, and what it cost

The K1 offline gate ran (row `SAEA-SN-MF-K1-HYBRID-RANKING-GATE`, commits `437015d6` /
`ac8dc317` / `1b3cb855`; zero contacts; fidelity gate reproduced both sealed one-shot reads
count-for-count on all ten k values, plus 497/500 flown dispatch decisions whose 3 deviations
are exactly the v2 delta-override fires).

**Falsifier verdict: NOT FIRED.** RRF-60 raises gold-facet recall@5 on the DEV-1000 unexposed
500 from 0.744 to 0.762 (+9/500). So the pre-registered consequent — "key representation is not
the lever and the residual is task-intrinsic" — is NOT licensed. The key plane is not saturated.

**And the flight is still refused**, on three quantities the falsifier failed to name:
recall@1 FALLS 0.636 -> 0.590 (-23/500) under the same rule; the measured conversion anchors are
steeply rank-dependent (98.2% at top-1 versus 69.6% at ranks 2-3), so 23 demotions against 9
promotions does not close; and at supply level the loss side dominates (newly gold-supplied
among currently-wrong 12, gold-supply LOST among currently-correct 29-40). Central conversion
projections are negative on all four populations (-0.75 to -2.70 pp).

**Methodological correction, recorded so it is not repeated: the falsifier was ONE-SIDED.**
A key-plane falsifier on this cell must be two-sided (a rule must raise recall@5 AND not lower
recall@1) or must be stated directly on the conversion-weighted objective. Every future
key-plane gate in this agenda inherits that requirement.

**Two durable assets survive the negative projection:**
1. **Multi-dimensional K is now demonstrably realizable.** With the lexical dimension live,
   `dims_total` goes 3 -> 4, `agreement` takes 1/4 and 2/4, `dims_hit=2` occurs on 11.7-14.3%
   of top-m candidates, 181-217 of 500 samples carry a two-dimension candidate, and 1,417
   facets are admitted by the lexical dimension alone. The rank-weight family is
   **non-degenerate for the first time** — section 2.1's defect is fixable, and this is
   independent of whether this particular fusion buys accuracy.
2. **The cost note in section 5 was WRONG and is corrected here.** The lexical channel is
   effectively free: index build 0.054 s over all 11,514 texts, per-query scoring 0.096 ms
   (0.096 s per 1,000 trajectories). The 1.147 s/call figure belongs to the EXISTING scalar
   sweep, whose vectorised equivalent measures 0.98 ms (about 1,170x, fidelity proved by 9,900
   cosine probes at 1e-9). **Vectorisation is therefore not a K1 prerequisite** — it is an
   independent ~19 min CPU per 1,000 trajectories win, and a second dimension does not multiply
   the old cost.

**Consequence for the agenda order:** K1 as a same-text lexical fusion is closed for flight.
The next key-plane item is **K2 (v5 pair-boundary material as discriminative key text)**, which
targets exactly K1's weakness — it aims at top-1 discrimination between confusable siblings
rather than at widening the top-5 window. K3 (field-role-constrained contact-0) is unchanged.
Any K1 successor must present a fusion form that improves recall@1, not merely recall@5, and
must be gated on the two-sided falsifier above.
