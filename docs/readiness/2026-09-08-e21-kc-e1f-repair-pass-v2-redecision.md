# KC-E1f, re-decided — the v2 rule, fixed before any number is recomputed

**This file is opened with its rule and nothing else.** The verdict, the guard table and every
number arrive in a later commit; at the moment this section is written, not one figure of the v2
read exists, and the commit order is the proof. The rule below is therefore not a retrofit: it is
the thing the recomputation will be measured against.

Decides, for the second time and under a different rule, exposure row
`SAEA-E21-KC-E1F-REPAIR-44-V1` and its form twin `SAEA-E21-KU-E1FC-PLACEBO-REPAIR-44-V1` against
the sealed comparator `SAEA-E21-FULL44-DIRECT-BASELINE-V2`. This re-decision's own row is
`SAEA-E21-KC-E1F-VERDICT-V2` (`model-free-check`), registered and committed before the first
number was recomputed; **zero model, GPU, tool, embedder, tokenizer, network, audio-decode and
paid-API contacts**. No arm is re-flown; not one byte of any arm's output is new.

**The v1 verdict stays on record.** `docs/readiness/2026-09-08-e21-kc-e1f-repair-pass-v1-verdict.md`
decided these same sealed bytes **REJECTED** — the preregistration's own word, HARMFUL — and
nothing here withdraws, amends or supersedes it. v2 sits beside v1, under a rule the owner changed
after v1 named the rule as the defect.

---

## 1. Why there is a v2 at all

Section 13 of the v1 verdict named one next step and refused to take it:

> **The guard specification is what rejected this cell, and no successor in this family can be
> admitted until it is fixed.** […] The successor preregistration must state a margin `δ` for each
> such guard (`UB <= +δ`, `LB >= −δ`) and must derive `δ` from a source that **predates this
> contrast** […]. **A margin chosen after seeing this result would be a retrofit, and this note
> does not choose one.** Whether the same sealed pair may then be re-decided under the new rule, or
> whether a re-decision requires a fresh flight, is an owner's sequencing call and not an
> analyst's; it needs its own owner GO and its own row.

Two things then happened, in this order, and both before this file existed.

1. **The margin source was measured, not chosen.** `SAEA-E21-FULL44-NULL-REPLICATE-V1` flew the
   sealed comparator's own configuration a second time — identical prompt bytes, identical audio
   bytes, identical 1,935,965 prompt tokens, 1,593 of 1,593 emitted slices byte-identical — and
   published this carrier's own call-clustered CI90 half-width per metric
   (`docs/readiness/2026-09-08-e21-own-null-replicate-v1-verdict.md` §3). That cell has no factor,
   admits nothing, and its numbers were sealed and committed **before** this re-decision was
   authorized. It is the source v1 §13 demanded: it predates this contrast, and it could not have
   been tuned to it, because it never saw it.
2. **The owner made the sequencing call.** Decision 9 of 2026-09-08, item 1: re-decide this sealed
   pair under non-inferiority guards whose margins come from the Earnings-21 own-null replicate,
   with the v1 verdict left standing beside it. Item 3 of the same decision makes it a family rule:
   **every "not worse" guard is a non-inferiority test with a margin fixed from the carrier's own
   null.**

So the v2 rule is not this analyst's choice of `δ`. Each `δ` is a number another cell measured, on
this carrier, under a null in which nothing was changed.

## 2. The v2 rule, in force from 2026-09-08 and fixed before any recomputation

**Nothing about the estimand, the roster, the pairing, the estimator, the seed, the draws or the
weightings changes.** The reported roster stays all 44 discovery calls; the pairing unit stays the
fixed 90-second window (1,593); the bootstrap cluster stays the call (44); the estimator stays the
pooled ratio `sum(numerator) / sum(denominator)` through
`analysis.paired.resampled_statistic(cluster_of=analysis.e21_window_pairing.call_of)` at seed
**20260903**, **10,000** replicates, **CI90**, reported under **both weightings** (natural mixture
and equal stratum). **Only the guard wording and the source of each margin change.**

### 2.1 The primary — unchanged, word for word

> **ADMITTED** iff, on the reported roster, the **call-clustered CI90 lower bound** on the PERSON
> entity-WER **reduction** — pooled `(S + D) / tagged reference words`, comparator minus KC-E1f, so
> a positive value means fewer errors — is **> 0 against the sealed comparator** AND **> 0 against
> KU-E1fc**, and every gating guard below holds.
>
> **NULL** if either lower bound includes 0.
>
> **REJECTED** if any gating guard fails, with the failing guard named and the per-class table
> published either way.

To that, and **reported rather than gating**, v2 adds one line the null makes available: state
whether the PERSON effect exceeds this carrier's own PERSON null half-width, **0.25009 points**.
The primary's own threshold is unchanged at zero; if its lower bound clears 0.25009 the effect is
also larger than a same-request replicate of this carrier can produce, and the note must say so
explicitly rather than leave a reader to divide.

### 2.2 The guards — every "not worse" clause becomes a non-inferiority test

For each guard, the rule is: **the CI90 bound on the HARMFUL side must not exceed that metric's
margin, where the margin is the half-width of the Earnings-21 own-null replicate's own
call-clustered CI90 on the same metric.** Units are percentage points throughout, matching the
null table's own convention.

| # | guard | v1 form | **v2 form** | **margin `δ`** | where `δ` comes from |
|---|---|---|---|---:|---|
| 1 | **delivery integrity** | construction check; **aborts the read** rather than producing a number | **UNCHANGED.** A construction guarantee has no margin — it holds on every window or the read stops | — | — |
| 2 | corpus WER non-inferiority | `UB(KC-E1f − comparator) <= 0` | **`UB(KC-E1f − comparator) <= +0.05793`** | **0.05793** | null verdict §3, `corpus WER / ConEC overall` |
| 3 | numeric-value accuracy not worse (**call-pooled**) | `LB(KC-E1f − comparator) >= 0` | **`LB(KC-E1f − comparator) >= −0.15651`** | **0.15651** | null verdict §3, `numeric-value accuracy` |
| 4 | over-generation not worse | `UB(KC-E1f − comparator)` insertions per reference word `<= 0` | **`UB(KC-E1f − comparator) <= +δ_ins`**, where `δ_ins` is the half-width of the **null replicate's own** call-clustered CI90 on **the same quantity v1 used** — pooled `insertions / reference words`, ×100 — **computed from the null replicate's per-window rows through the same instrument**, and stated in §4 before it is applied | **computed** | the null replicate's per-window rows |
| 5 | negation-critical / semantic high-impact rate | advisory point estimate; gates nothing | **STAYS ADVISORY, now for a measured reason** | — | see §2.3 |

Guards 2, 3 and 4 gate. Guard 1 gates by construction. Guard 5 does not gate.

**A margin is one-sided and is applied only on the harmful side.** It never widens the interval, it
never moves a point estimate, and it never turns a harm into a benefit: it says how much of a
movement this carrier's own noise can manufacture with nothing changed, and refuses to call a
movement smaller than that a harm.

### 2.3 Why the semantic guard cannot be given a margin

The null replicate's own interval on `semantic-high-impact-error-rate-v1` is
**+0.00222 [+0.00080, +0.00377]** — an interval that **excludes zero under a null in which nothing
was changed**, because the metric counts roughly a hundred high-impact reference words out of
359,765. A metric whose same-request null excludes zero cannot answer "does not rise" in either
direction, at any margin. Giving it a margin would dress an unanswerable clause as an answerable
one. It stays advisory, its point estimate is published, and the null verdict's own §10 item 2
already names the real fix (widen the taxonomy until the metric has mass, or stop letting it carry
admission clauses on this carrier).

### 2.4 What a v2 verdict may and may not mean

* **A re-decision is not a new measurement.** The same sealed bytes decided a second time carry
  exactly the evidence they carried the first time. If the v2 verdict is ADMITTED, the admission is
  an admission *of a rule change applied to fixed evidence*, and it must be reported that way.
* **A margin is not a licence.** Each `δ` is measured from **one** replicate at 44 clusters. The
  intervals are themselves uncertain; they are better margins than an imported one, not exact ones,
  and every use must name the cell that measured them.
* **An ADMITTED verdict here obliges a replication before any freeze.** Fixed in advance, in §3.

## 3. The replication requirement, fixed in advance

If and only if the v2 verdict is ADMITTED, the admission is admitted **provisionally** and carries
this obligation, written here before the verdict is known:

1. **The same roster, flown again.** All 44 discovery calls, the same 1,593 fixed 90-second
   windows, the same configuration, as a second independent pass of the KC-E1f arm.
2. **A second pass through the null band.** The replicate's PERSON effect and every gating guard
   must be re-read against the null's measured intervals, and the PERSON effect must again be
   disjoint from `[−0.24338, +0.25680]`.
3. **No freeze before both hold.** No candidate freeze, no citation of this effect as an admitted
   effect and no promotion of the module may precede that replication. The 2026-09-03 owner rule is
   explicit — a new mechanism is admitted only after its predecessor is replicated or root-caused
   to a named component — and a re-decision of sealed bytes replicates nothing by itself.

## 4. The over-generation margin

*Reserved. `δ_ins` is computed in the next commit, from the null replicate's own per-window rows,
through the same instrument, and is stated here before it is applied.*

## 5. The verdict

*Reserved for the next commit. No number of the v2 read exists at the time this file is first
committed.*
