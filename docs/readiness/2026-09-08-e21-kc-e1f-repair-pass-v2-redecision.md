# ADMITTED — KC-E1f, re-decided under margins this carrier measured for itself

**ADMITTED**, provisionally and with a replication obligation fixed in §3 before the verdict was
known. The primary is met on both legs and met comfortably; all three gating guards pass; and the
two guards that rejected this cell in v1 pass by margins that another cell measured before this one
was authorized. **Not one number moved.** The re-decision changed the guards' wording and the source
of each margin, and nothing else: the same sealed bytes, the same rows — byte-identical to v1's,
SHA-256 for SHA-256 — the same estimator, the same seed, the same draws.

The honest shape of the result is narrower than "admitted" sounds, and §8 says so: **PERSON entity
WER is the only metric in this cell whose effect is larger than this carrier's own replicate noise.**
The corpus-WER improvement, the ORG improvement and the numeric-accuracy improvement that v1's table
reported are all inside the null band and are not demonstrated effects.

Decides, for the second time and under a different rule, exposure row
`SAEA-E21-KC-E1F-REPAIR-44-V1` and its form twin `SAEA-E21-KU-E1FC-PLACEBO-REPAIR-44-V1` against the
sealed comparator `SAEA-E21-FULL44-DIRECT-BASELINE-V2`. This re-decision's own row is
`SAEA-E21-KC-E1F-VERDICT-V2` (`model-free-check`), registered and committed before the first number
was recomputed; **zero model, GPU, tool, embedder, tokenizer, network, audio-decode and paid-API
contacts**. No arm is re-flown and not one byte of any arm's output is new. Receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-kc-e1f-verdict-v2/`.

**The v1 verdict stays on record.** `docs/readiness/2026-09-08-e21-kc-e1f-repair-pass-v1-verdict.md`
decided these same sealed bytes **REJECTED** — the preregistration's own word, HARMFUL — and nothing
here withdraws, amends or supersedes it. v2 sits beside v1, under a rule the owner changed after v1
named the rule as the defect.

**The commit order is the audit trail.** §1–§3 below — the whole rule — were written and committed
in `8808fe94` (with its `scripts/e21_kc_e1f_v2_redecision.py`), before the recomputation was run even
once. §4 onward arrived afterwards. The rule text below is unchanged from that commit.

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

---

*Everything above was committed in `8808fe94`, before the recomputation ran. Everything below was
written after it.*

---

## 4. The over-generation margin, computed and anchored before it is applied

`δ_ins` is the one number the v2 rule needed and the null cell's published table does not carry, so
it is computed here from that cell's own per-window rows, through the same instrument. **The same
request, flown twice with nothing changed, inserts 31 more words.**

| | comparator | null replicate | delta |
|---|---:|---:|---:|
| insertions | 10,700 | **10,731** | **+31** |
| reference words | 359,765 | 359,765 | 0 |
| insertions per 100 reference words | 2.974150 | 2.982767 | **+0.008617** |
| call-clustered CI90 | | | **[−0.013565, +0.030791]** |
| **half-width — the margin `δ_ins`** | | | **0.022178** |

**The band is anchored before it is used.** The rule's own refusal is that the two row files must
first reproduce the null cell's **own published** corpus-WER interval to the digit through this
instrument, or the band computed from them is not that cell's band and may not serve as a margin.
They do, on every field:

| field | published by the null cell | reproduced here |
|---|---:|---:|
| point | −0.0200130640834999 | −0.0200130640834999 |
| ci_low | −0.08501511398883133 | −0.08501511398883133 |
| ci_high | +0.030845200652504484 | +0.030845200652504484 |
| sigma_hat | 0.03590926385732335 | 0.03590926385732335 |
| half-width | 0.057930157320667905 | 0.057930157320667905 |

The pairing gate behind it: 1,593 windows on both sides, **44 of 44 calls carrying an identical
reference-word total**, 359,765 reference words on both sides. Sixty-eight of the 1,593 windows
attribute their reference words differently — the alignment moves when the hypothesis moves — which
is a property of the window unit, not of the pairing, and is why the gate is set at the call, which
is also the bootstrap cluster.

## 5. The verdict, applied line by line

Call-clustered CI90, natural mixture, 44 clusters, seed 20260903, 10,000 replicates. Percentage
points. The v1 column is the identical measured interval, decided under the identical draws.

| test | required (v2) | measured | v1 | **v2** |
|---|---|---|---|---|
| **primary**, PERSON reduction vs comparator | LB > 0 | **+3.737** [+2.653, +4.855] | MET | **MET** |
| **primary**, PERSON reduction vs KU-E1fc | LB > 0 | **+3.840** [+2.752, +4.958] | MET | **MET** |
| guard 1, delivery integrity | construction; aborts the read | 1,593 / 1,593 windows, **0 violations**, both arms; the §5.1 attribution closed | PASS | **PASS** |
| guard 2, corpus WER (KC-E1f − comparator) | UB <= **+0.05793** | **−0.02936** (UB), point −0.04503 | PASS | **PASS** |
| guard 3, numeric accuracy call-pooled (KC-E1f − comparator) | LB >= **−0.15651** | **−0.02122** (LB), point +0.01027 | **FAIL** | **PASS** |
| guard 4, insertions per reference word (KC-E1f − comparator) | UB <= **+0.02218** | **+0.00255** (UB), point +0.00028 | **FAIL** | **PASS** |
| guard 5, negation-critical rate | advisory; gates nothing | 0.0278 % → **0.0275 %** (100 → 99 HIGH reference words), point −0.00028 | ADVISORY | **ADVISORY** |

**The primary is met, every gating guard holds, and the verdict is ADMITTED.**

### 5.1 The two guards that flipped, and by how much

Neither flipped because a number changed. Each flipped because the bar moved from "significantly
better" to "not worse than this carrier's own noise", and each now clears the new bar with room:

| guard | harmful bound | margin | **slack** | bound as a share of the margin |
|---|---:|---:|---:|---:|
| numeric-value accuracy (call-pooled), LB | −0.02122 | −0.15651 | **0.13528** | 13.6 % |
| over-generation, UB | +0.00255 | +0.02218 | **0.01963** | 11.5 % |

And the plainest statement of the same fact, in counts rather than intervals:

| | KC-E1f vs the comparator | **the null replicate vs the comparator** |
|---|---:|---:|
| insertions moved | **+1** (10,700 → 10,701) | **+31** (10,700 → 10,731) |
| matched numeric values moved | **+1** (8,832 → 8,833) | **−3** (8,832 → 8,829) |

**The same request, flown twice with nothing changed, moved 31 insertions where KC-E1f moved one,
and moved three numeric values where KC-E1f moved one.** The v1 guards asked this arm to prove it
had not caused a movement thirty times smaller than the movement the runtime makes on its own. That
is what the family rule of Decision 9 item 3 exists to stop, and it is why the v1 note called the
guard, not the arm, the thing that had to change.

### 5.2 Both weightings, and the guards under each

The primary is defined on the natural mixture; the equal-stratum reading is carried because §5 of
the preregistration asks for it. **Every gating guard passes under both, and both primary legs are
met under both.**

| | natural mixture | equal stratum (per call) |
|---|---|---|
| primary, PERSON vs comparator | **+3.737** [+2.653, +4.855] | **+3.700** [+2.501, +4.925] |
| primary, PERSON vs KU-E1fc | **+3.840** [+2.752, +4.958] | **+3.781** [+2.576, +5.008] |
| guard 2, corpus WER UB (margin +0.05793) | −0.02936 **PASS** | −0.02768 **PASS** |
| guard 3, numeric call-pooled LB (margin −0.15651) | −0.02122 **PASS** | −0.01696 **PASS** |
| guard 4, insertions UB (margin +0.02218) | +0.00255 **PASS** | +0.00245 **PASS** |

## 6. What changed between v1 and v2, and what did not

**What changed: the wording of three guards and the source of three margins. That is the complete
list.**

| | v1 | v2 |
|---|---|---|
| primary | LB > 0 vs comparator AND vs twin | **identical**, plus a reported comparison to the PERSON null half-width |
| corpus WER guard | `UB <= 0` — a superiority test | `UB <= +0.05793` — non-inferiority at the measured margin |
| numeric guard | `LB >= 0` — a superiority test | `LB >= −0.15651` — non-inferiority at the measured margin |
| over-generation guard | `UB <= 0` — a superiority test | `UB <= +0.02218` — non-inferiority at the measured margin |
| semantic guard | advisory | advisory, and now for a measured reason (§2.3) |
| roster, unit, cluster, estimator, seed, replicates, CI level, weightings | — | **all unchanged** |
| the sealed bytes | — | **unchanged; no arm re-flown** |

**What did not change: any number.** Proved twice, mechanically:

1. **The rows are byte-identical.** The three arms' per-window rows were regenerated from the sealed
   traces by `scripts/e21_window_pairing_read.py` for this read, and each file's SHA-256 equals the
   one v1's own identity anchor recorded — `98d431f2…` for the comparator, and likewise for KC-E1f
   and KU-E1fc. All three anchors are **30/30 PASS**, and the class anchor is **87/87 PASS**.
2. **The decision block is identical field by field.** `scripts/e21_kc_e1f_v2_redecision.py` compares
   every numeric leaf of the committed v1 decision block against the freshly recomputed one — **28
   numeric fields, 0 moved** — and refuses to decide if a single digit differs. It did not have to
   refuse. Serialized whole and sorted, the two decision blocks are the same string.

And the recomputed read, run under the v1 rule it was written for, returned **`VERDICT HARMFUL
(REJECTED)`** on its own console line, naming the same two failing guards. The v1 verdict is not
merely left on record — it was reproduced from the sealed bytes in this very read, and then the
v2 rule was applied on top of it.

**Two readings of the same evidence, both on record.** v1 applied a rule that had no margin and
returned REJECTED; v2 applies a rule whose margins this carrier measured for itself and returns
ADMITTED. Neither note found a mistake in the other's arithmetic. The disagreement is entirely about
what "not worse" means, and it was settled by measuring the noise rather than by arguing.

## 7. The primary, against this carrier's own noise

| leg | reduction, CI90 | PERSON null half-width | LB in null half-widths | disjoint from the PERSON null interval? |
|---|---|---:|---:|---|
| vs the sealed comparator | **+3.737 [+2.653, +4.855]** | 0.25009 | **10.61** | **YES** — gap 2.41 points |
| vs the token-matched twin | **+3.840 [+2.752, +4.958]** | 0.25009 | **11.00** | **YES** |

The PERSON null interval is `[−0.24338, +0.25680]` and the primary's whole interval sits above it
with 2.41 points to spare. **This is not a claim the null could have manufactured**: the null moved
PERSON by exactly 0.00000 points, and even its 44-cluster churn only reaches a quarter of a point.

The reported comparison is a comparison, not a threshold: the primary's bar is unchanged at zero,
and the multiple is published so no reader has to divide.

## 8. The correction v2 owes v1 — three improvements that do not survive the null

The measured null cuts both ways, and it cuts against this cell as well as for it. v1's §2 and §6
reported three movements as improvements with intervals that exclude zero. **Against the null's own
measured intervals, only PERSON survives.**

| metric | KC-E1f improvement, CI90 | null interval for the same metric | disjoint? | reading |
|---|---|---|---|---|
| **PERSON entity WER** | **+3.737 [+2.653, +4.855]** | [−0.24338, +0.25680] | **YES** | **a demonstrated effect** |
| corpus WER | +0.045 [+0.029, +0.061] | [−0.08502, +0.03085] | **no** | inside replicate noise |
| ORG entity WER | +0.711 [+0.068, +1.475] | [−0.44313, +0.26904] | **no** | inside replicate noise |
| non-entity WER | +0.002 [−0.003, +0.007] | [−0.11375, +0.01575] | no | inside replicate noise |
| numeric accuracy (call-pooled) | +0.010 [−0.021, +0.051] | [−0.18758, +0.12543] | no | inside replicate noise |

**So the corpus-WER improvement is not a finding.** v1 wrote that "the guard that rejected KC-E1 now
passes in this cell's favour: corpus WER *improves* by 0.045 pp with a CI90 that excludes zero", and
that sentence was true against zero and is not true against this carrier's own null. What survives is
the weaker and sufficient statement the guard actually asks for: **corpus WER is not worse.** The
same correction retires the ORG improvement.

This is the same correction the null verdict made to the silence-tail cell's PERSON regression, in
the opposite direction, and it is the reason the family rule is worth its cost: a measured null
demotes weak claims as reliably as it rescues weak guards.

## 9. The admission entry

The design note's §8 admission gate (`docs/readiness/2026-09-08-agent-system-episode-and-core-pressure-v1.md`)
listed this module as *"substitution-only repair (Reviewer + constrained Solve) | Earnings-21 |
primary gain; guards pending the v2 re-decision | KC-E1f"*. The guards are no longer pending.

`docs/receipts/harness-admission.json`, created by this note:

| module | carrier | status | row | evidence | date |
|---|---|---|---|---|---|
| substitution-only repair with the ConEC brief | Earnings-21 | **ADMITTED** (provisional; replication required) | `SAEA-E21-KC-E1F-VERDICT-V2` | `SAEA-E21-KC-E1F-REPAIR-44-V1` vs `SAEA-E21-FULL44-DIRECT-BASELINE-V2` and `SAEA-E21-KU-E1FC-PLACEBO-REPAIR-44-V1`; PERSON +3.737 [+2.653, +4.855]; margins from `SAEA-E21-FULL44-NULL-REPLICATE-V1` | 2026-09-08 |

The status is ADMITTED rather than NEUTRAL because the module carries a **gain** on the carrier's
primary metric — the §8 gate's preferred outcome — and that gain is disjoint from the carrier's own
null. It is marked provisional because §3's replication has not run. **The default plan may not
contain this module until it has.**

## 10. The citable sentence, and what may not be said

Exactly one sentence may be cited from this note, and this is it:

> On the 44 Earnings-21 discovery calls, a second, substitution-only repair pass over the frozen
> core's own sealed transcript, supplied with a 12-entry ConEC pre-meeting brief, reduces PERSON
> entity WER from 22.489 % to 18.752 % — a call-clustered CI90 reduction of **+3.737 points
> [+2.653, +4.855]** against the sealed comparator and **+3.840 [+2.752, +4.958]** against a
> token-matched placebo twin, an effect disjoint from this carrier's own same-request replicate null
> — with every guard holding at the non-inferiority margins that null measured; the result is
> training-free, zero-parameter-update, discovery-split, single-carrier and **provisional until
> replicated on the same roster**.

**What may not be said**, and each of these was checked rather than assumed:

1. **Not that corpus WER improved.** §8. It is not worse; that is all.
2. **Not that ORG improved.** §8.
3. **No evaluation-split claim.** 34 of the 44 calls are the kb-construction half; the evaluation ten
   carry 342 paired windows, below the program's `n >= 400` rule, and v1 §10 reports them apart and
   descriptively. **This verdict quotes no interval on them.**
4. **No superiority and no generality.** One carrier, one frozen core at Q4_K_M on build `04ccc72a`,
   one 90-second OBS tiling, greedy, 44 discovery calls, one replicate's margins.
5. **Nothing about KC-E1, and nothing about the whole brief.** v1 §12 items 9 and 10 stand unchanged.
6. **Not that the mechanism repaired a deletion.** It cannot, by construction; the PERSON deletion
   move 83 → 80 is a normalization re-seating attributed in v1 §4, and the reachable floor stays
   `83 / 2917 = 2.846 %`.
7. **No candidate freeze may cite this.** §3 item 3.
8. **No Stage-3 claim.** `paper-scale-confirmatory` is neither available to this repository nor
   requested.

## 11. The core-pressure covariates of the pair

Published with the admission because a gain bought with core pressure is a different thing from a
gain bought with a better prompt, and the difference has to be visible.

| | KC-E1f | KU-E1fc | comparator |
|---|---:|---:|---:|
| **core calls charged per window, this cell** | **1** | **1** | 1 |
| core calls per window including the pass 1 it edits | 2 | 2 | 1 |
| prompt tokens per window — min / median / max | **683 / 2,260 / 2,480** | 690 / 2,267 / 2,487 | — / — / — |
| prompt tokens, total | **3,550,695** (+83.4 % over the comparator) | 3,561,846 | 1,935,965 |
| completion tokens, total | **434,219** (−1.2 %) | 439,049 | 439,532 |
| worst realized request / slot | 3,504 / 9,216 (margin 2.630) | 3,511 / 9,216 (margin 2.625) | — |

**The system's own decision share** — the part of the outcome the control plane decided rather than
the core:

| | KC-E1f | KU-E1fc |
|---|---:|---:|
| windows | 1,593 | 1,593 |
| windows changed (≥ 1 accepted substitution) | 1,064 | 1,023 |
| **windows delivered unchanged without a refusal** | **447** | 498 |
| **windows refused** | **82** | 72 |
| — `anchor_ratio_below_floor` | 75 | 67 |
| — `empty_response` | 3 | 2 |
| — `substituted_fraction_above_ceiling` | 4 | 3 |
| — `empty_predecessor` | 0 | 0 |
| accepted substitutions | 2,427 | 2,125 |
| substituted tokens applied | 2,545 | 2,154 |
| would-be tokens never applied (ceiling refusals) | 91 | 6 |
| **rejected opcodes, total** | **1,093** | 1,123 |
| — `unbalanced_replace` | 654 | 658 |
| — `deletion` | 331 | 337 |
| — `insertion` | 104 | 125 |
| — `oversized_replace` | 4 | 3 |

**One core call per window, and on a third of them the control plane delivered the predecessor
anyway.** 529 of 1,593 windows (**33.2 %**) ended with the sealed pass-1 text unchanged: 447 with no
accepted substitution and no refusal recorded, and 82 refused outright. Across the whole cell
**1,093 proposed opcodes were rejected by class before delivery** — 654 unbalanced replacements, 331
deletions, 104 insertions and 4 oversized replacements — and the deletion and insertion classes are
exactly the channel KC-E1's 2,692 extra deletions came through. The gain is bought at one contact per
window; the *safety* of the gain is bought by the control plane's rejections, and both numbers belong
beside the effect.

Cost, unchanged from v1 and re-stated because an admission should carry it: 1,593 charged calls per
arm, 141,345.8527 metered speech seconds per arm, **1.1093 GPU-h (KC-E1f) and 1.1656 (KU-E1fc)** by
the manifest sampler against a registered 1.2 each, paid API spend **0**. Both arms attached to a
resident session; neither started nor stopped a server.

## 12. What this re-decision cannot conclude

1. **It is not a new measurement.** The same sealed bytes, decided a second time. Every limit v1 §12
   listed still applies, word for word, and this note repeats none of them by way of softening.
2. **It cannot replicate itself.** §3's obligation is unmet by construction: a re-decision produces
   no second sample.
3. **The margins are one replicate's.** 44 clusters, one pass. A second replicate would produce a
   different interval, and every margin here names the cell that measured it. If the geometry, the
   build or the population changes, the margins must be re-measured before they are reused.
4. **Four of the six agentic metrics still cannot resolve a half-point effect at 44 clusters** (null
   verdict §4). PERSON at ±0.25 and ORG at ±0.36 are the reason this note claims PERSON and nothing
   else.
5. **A small share of every difference is decode noise**, and the null is exactly the measurement of
   how large that share is. That is now priced into the guards; it is not priced out of the primary,
   which clears it by 10.6 half-widths.
6. **Nothing about the other two carriers.** SLURP and Audio2Tool still have no measured null of
   their own, and none of these margins travels to them.

## 13. Files

| file | what it holds |
|---|---|
| `docs/checks/…/2026-09-08-e21-kc-e1f-verdict-v2/result-summary.json` | the v2 decision: the rule, every margin with its source, the over-generation band and its anchor, the guard table, the primary with its null-half-width comparison, and the no-number-moved proof |
| `…/guard-table.md` | the guard table alone, as one page |
| `…/recomputed/result-summary.json` | the freshly recomputed v1-form read this decision sits on: identity anchors, class anchor, §5.1 attribution, all three contrasts under three interval readings and two weightings, the sensitivities, the per-call block, the E5 halves, the mechanism ledgers and the token covariate |
| `…/recomputed/per-call-table.md`, `…/recomputed/token-throughput-covariate.json` | as v1's, regenerated |
| `…/reaggregation/{comparator,kc-e1f,ku-e1fc}/reaggregation.json` | each arm's identity anchor, 30/30 PASS, with its rows file's SHA-256 |
| `…/attribution/{kc-e1f,ku-e1fc}/attribution.json` | the §5.1 receipt, regenerated |
| `…/MANIFEST.sha256` | the receipt directory's byte manifest |
| `scripts/e21_kc_e1f_v2_redecision.py` | the v2 rule in executable form, committed before it was run |
| `docs/receipts/harness-admission.json` | the living admission table, created here |

Per-window rows and span tables live under `$SPEECHRL_DATA_DIR/runs/SAEA-E21-MF-WINDOW-PAIRING-V1/`
and never in Git — per-request derivatives of sealed model outputs. Their SHA-256 values are pinned
in each arm's anchor and re-checked before a contrast is computed.
