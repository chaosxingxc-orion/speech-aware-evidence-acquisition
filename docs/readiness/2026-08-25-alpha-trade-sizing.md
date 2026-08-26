# ALPHA TRADE SIZING — the shape of the open decision, not an answer to it

**Row:** `SAEA-SN-MF-ALPHA-TRADE-SIZING` (`model-free-check`), registered BEFORE any input was
opened. Readable at commit `9ea74f6b`; row sha256
`c0d6200cfe100d94ecde7e6e7b97467c9c0dd2c659fa6e38298ef3e4b0398062`.
**Module:** `src/speech_aware_evidence_acquisition/analysis/alpha_trade_sizing.py`.
**Receipt:** `docs/checks/speech-aware-evidence-acquisition/2026-08-25-alpha-trade-sizing/alpha-trade-sizing-report.json`
(sha256 `4df34154a86fc7bb2f683b6f2a692819c0e4283228ccdc0bf1c796081812e2ab`).
**Spend:** 0 frozen-core contacts, 0 tool contacts, 0 tokenizer contacts, 0 audio seconds,
0.0 GPU-hours, 0 new dependencies. The in-process offline guard
(`analysis.dev100_reviewer_audit.arm_offline_guard`) was armed before the first input was opened and
recorded **0 outbound connection attempts against 0 targets**. The resident llama-server (pid 38623,
port 8090) was treated as cold and never touched. Wall 471.6 s.

---

## HARD STOP — read this before the tables

**This document recommends no value of `alpha`, proposes no change, takes no decision and authorizes
none.** It sizes a decision the owner has open. `alpha` stays **0.45** in the frozen cell. No knob was
changed, no line under `rails/`, `core/` or `configs/` was written, nothing hash-pinned moved, no
receipt was displaced and no arm was re-flown. The only new code is under `analysis/`.

**A changed dispatch decision does not tell us what the frozen core would have answered.** There is no
sealed decode for a trajectory that did not dispatch. Reach, composition and supply quality below are
FACTS ABOUT THE MACHINERY, computed through the registered functions over sealed records. Every
outcome number is a **PROJECTION** and is labelled one. No expected-accuracy headline is produced.

**Everything computed on the SLURP UNEXPOSED 500 is a SECONDARY READING** on the locked baseline's own
population. It MUST NOT be used to revise, re-tune or restate **THE LOCK**, which stands exactly as
landed at `d9fef537`.

---

## 0. The one-paragraph shape

`alpha` is **not a dial. It is a switch.** Across the registered grid the reach curve has exactly one
step, at `alpha = 0.50`, and nothing moves above it: 0.50, 0.55, 0.60 and 0.65 select the *identical*
set on every population. The step buys **+24 trajectories on the SLURP unexposed 500**, **+27 on the
exposed 500**, and **+2 on Audio2Tool**. On both SLURP halves the step is dominated by trajectories
that are **already right**, and *not one of them* would receive a supply containing its own answer. On
Audio2Tool the step is the opposite: both additions are currently wrong and both would receive a
supply naming gold first. The two carriers point in opposite directions, which is the generality cost
made arithmetic.

---

## 1. The registered grid, and why it straddles 0.5

| `alpha` | role | guaranteed margin `1 − 2α` | fused-mass gap a rival must clear, `(1−α)/α` | attainable? |
|---|---|---|---|---|
| 0.40 | sweep point | +0.20 | 1.5000 | no (`Σ fused ≤ 1`) |
| **0.45** | **CONTROL — the locked, frozen value** | **+0.10** | 1.2222 | no |
| 0.50 | sweep point | 0.00 | 1.0000 | only as an exact TIE |
| 0.55 | sweep point | −0.10 | 0.8182 | yes |
| 0.60 | sweep point | −0.20 | 0.6667 | yes |
| 0.65 | sweep point | −0.30 | 0.5385 | yes |

`kb_policy._blend_scores` gives the direct label `α·f(direct) + (1−α)` and every rival `α·f(rival)`,
with `f ∈ [0,1]` and `Σf ∈ {0,1}` by construction. A rival therefore wins exactly when
`f(rival) − f(direct) ≥ (1−α)/α`, with equality producing a tie that `_argmax_labels` returns as a
multi-label best set — and `KbAlphaBlendController._advance_after_direct` **dispatches** a tie, because
retain-primary needs the direct label to be the *unique* argmax. The whole decision is a threshold on
one scalar.

Every number below is produced by importing and calling `kb_policy._fused_label_scores`,
`kb_policy._blend_scores` and `kb_policy._argmax_labels` themselves. Nothing is reimplemented.
`alpha` enters only at the blend head, strictly after recall / rank / fuse, so **the supply is
alpha-invariant**: the sweep replays recall→rank→fuse once per sample through the registered path and
evaluates the registered blend head six times.

### Fail-closed gates, all passed before any grid point was read

- The control replay reproduces the **published reach** on all three populations: **160/500**
  (unexposed), **166/500** (exposed), **15/104** (A2T).
- The SLURP loader's flight-replay gate reproduced the flown supply exactly, and every
  retain/dispatch mismatch against the flight is an accounted v2 `δ`-override fire.
- The A2T loader's cross-carrier fidelity gate reproduced the flown supply, dispatch and label
  recovery on 104 of 104.
- The full-KB gold-facet recall@k gate reproduced the sealed one-shot read.
- **Structural self-gate:** reach at 0.40 equals reach at 0.45 on every population, as the veto
  theorem requires. A discrepancy would have aborted the run.

---

## 2. THE SWEEP TABLE — reach and risk in the same table, never apart

`new` = trajectories entering the dispatching set relative to the `α = 0.45` control.
`gold-bearing` = of those, how many would receive a supply whose ordered `task_target` set contains
the gold target. **`AT RISK`** = of those, how many are **correct under the locked cell today** and
would therefore have their answer replaced by an evidence decode of unknown outcome.

### 2.1 SLURP — DEV-1000-NEW500 (500 UNEXPOSED) — *SECONDARY READING*

| `α` | reach | rate | new | gold-bearing (rank 1) | gold-absent | **AT RISK** | risk / new | risk / pop |
|---|---|---|---|---|---|---|---|---|
| 0.40 | 160 | 32.00 % | 0 | 0 | 0 | **0** | — | 0.00 % |
| **0.45** | **160** | **32.00 %** | **0** | 0 | 0 | **0** | — | **0.00 %** |
| 0.50 | 184 | 36.80 % | 24 | 3 (3) | 21 | **20** | 83.33 % | **4.00 %** |
| 0.55 | 184 | 36.80 % | 24 | 3 (3) | 21 | **20** | 83.33 % | **4.00 %** |
| 0.60 | 184 | 36.80 % | 24 | 3 (3) | 21 | **20** | 83.33 % | **4.00 %** |
| 0.65 | 184 | 36.80 % | 24 | 3 (3) | 21 | **20** | 83.33 % | **4.00 %** |

**Of the 20 currently-correct trajectories put at risk, 0 would receive a gold-bearing supply. All 20
would receive a supply that does not contain their answer.** The measured anchor for that case is
**0 of 67** — across every sealed population the frozen core has *never* recovered gold from a supply
that did not carry it.

### 2.2 SLURP — DEV-500 (500 PRIOR-EXPOSED)

| `α` | reach | rate | new | gold-bearing (rank 1) | gold-absent | **AT RISK** | risk / new | risk / pop |
|---|---|---|---|---|---|---|---|---|
| 0.40 | 166 | 33.20 % | 0 | 0 | 0 | **0** | — | 0.00 % |
| **0.45** | **166** | **33.20 %** | **0** | 0 | 0 | **0** | — | **0.00 %** |
| 0.50 | 193 | 38.60 % | 27 | 9 (9) | 18 | **18** | 66.67 % | **3.60 %** |
| 0.55 | 193 | 38.60 % | 27 | 9 (9) | 18 | **18** | 66.67 % | **3.60 %** |
| 0.60 | 193 | 38.60 % | 27 | 9 (9) | 18 | **18** | 66.67 % | **3.60 %** |
| 0.65 | 193 | 38.60 % | 27 | 9 (9) | 18 | **18** | 66.67 % | **3.60 %** |

Again **0 of the 18 at-risk trajectories would receive a gold-bearing supply.**

### 2.3 Audio2Tool — A2T-G1-104 (104 EXPOSED)

| `α` | reach | rate | new | gold-bearing (rank 1) | gold-absent | **AT RISK** | risk / new | risk / pop |
|---|---|---|---|---|---|---|---|---|
| 0.40 | 15 | 14.42 % | 0 | 0 | 0 | **0** | — | 0.00 % |
| **0.45** | **15** | **14.42 %** | **0** | 0 | 0 | **0** | — | **0.00 %** |
| 0.50 | 17 | 16.35 % | 2 | 2 (2) | 0 | **0** | 0.00 % | **0.00 %** |
| 0.55 | 17 | 16.35 % | 2 | 2 (2) | 0 | **0** | 0.00 % | **0.00 %** |
| 0.60 | 17 | 16.35 % | 2 | 2 (2) | 0 | **0** | 0.00 % | **0.00 %** |
| 0.65 | 17 | 16.35 % | 2 | 2 (2) | 0 | **0** | 0.00 % | **0.00 %** |

Both additions (`tier2_parametric:003923`, `tier6_correction:002430`) are **currently wrong** and both
would receive a supply naming gold **first**. `tier2_parametric:003923` is the very trajectory the
cross-carrier verdict identified as attaining the structural floor exactly — its observed blend margin
was `0.10000000000000003`, the theorem's `1 − 2α` and nothing more.

### 2.4 The perfect separation, on all three populations

On every population the supply's own gold coverage separates upside from downside **exactly**:

- every newly-dispatched trajectory that would receive a **gold-bearing** supply is currently **wrong**;
- every newly-dispatched trajectory that is currently **right** would receive a **gold-absent** supply.

The separation is clean. The **sizes** are not: on the unexposed 500 the downside set is **20** against
an upside set of **3**; on the exposed 500, **18** against **9**; on Audio2Tool, **0** against **2**.

---

## 3. The dispatch branch decomposition

`KbAlphaBlendController._advance_after_direct` has exactly five outcomes. Counts are the whole
population; the partition sums to `n` on every row.

| population | `α` | retain: supply-empty | retain: α-veto | dispatch: dead-direct | dispatch: tie | dispatch: outvoted |
|---|---|---|---|---|---|---|
| unexposed 500 | 0.40 / **0.45** | 2 | 338 | 160 | 0 | 0 |
| unexposed 500 | 0.50 | 2 | 314 | 160 | **24** | 0 |
| unexposed 500 | 0.55 / 0.60 / 0.65 | 2 | 314 | 160 | 0 | **24** |
| exposed 500 | 0.40 / **0.45** | 1 | 333 | 166 | 0 | 0 |
| exposed 500 | 0.50 | 1 | 306 | 166 | **27** | 0 |
| exposed 500 | 0.55 / 0.60 / 0.65 | 1 | 306 | 166 | 0 | **27** |
| A2T-104 | 0.40 / **0.45** | 0 | 89 | 15 | 0 | 0 |
| A2T-104 | 0.50 | 0 | 87 | 15 | **2** | 0 |
| A2T-104 | 0.55 / 0.60 / 0.65 | 0 | 87 | 15 | 0 | **2** |

Two structural readings fall straight out:

1. **The `dispatch: dead-direct` column never moves.** The label-free set is reached at every `α`, and
   it is the entire reachable set below 0.5 — the alpha-veto identity, confirmed rather than assumed.
2. **The `retain: supply-empty` column never moves either.** 2 trajectories on the unexposed half and
   1 on the exposed half retain because the fuser selected nothing at all; no value of `α` can reach
   them, because no blend is ever formed. That is a floor on reach that `α` cannot buy through.

**No trajectory ever leaves the dispatching set** as `α` rises, on any population, at any grid point.
Reported, not assumed.

---

## 4. Who newly dispatches

### 4.1 The M0 comparison

| population | new | M0-correct | M0-wrong | correct under the locked cell | carries a recovered direct label |
|---|---|---|---|---|---|
| unexposed 500 | 24 | **18** | 6 | **20** | 24 / 24 |
| exposed 500 | 27 | **18** | 9 | **18** | 27 / 27 |
| A2T-104 | 2 | 0 | 2 | **0** | 2 / 2 |

On both SLURP halves the widening reaches a set that the *knowledge-free* baseline already answers
correctly 18 times out of 24 and 18 times out of 27. This is not a set the method is failing on. On
Audio2Tool the widening reaches a set M0 gets wrong 2 for 2.

Every newly-dispatching trajectory carries a recovered direct label on every population — reported
rather than assumed, and expected, since the label-free set already dispatches at the control.

### 4.2 Query-vector diversity — does widening reach informative queries?

Ratios are distinct query vectors per trajectory, through the landed
`query_key_degeneracy_cross_carrier.vector_digest` key identity. Higher = more diverse.

| population | whole population | control dispatching set | **newly dispatching** | largest identical-key cluster (newly) |
|---|---|---|---|---|
| unexposed 500 | 369/500 = **0.738** | 136/160 = **0.850** | 16/24 = **0.667** | 6 of 24 |
| exposed 500 | 361/500 = **0.722** | 122/166 = **0.735** | 17/27 = **0.630** | 9 of 27 |
| A2T-104 | 89/104 = **0.856** | 5/15 = **0.333** | 2/2 = **1.000** | 1 of 2 |

The control-dispatching-set ratios (0.850, 0.735, 0.333) and cluster sizes (13, 19, 11) reproduce the
landed cross-carrier degeneracy read **exactly** — an unregistered but welcome fidelity signal.

**The answer to the owner's question differs by carrier, and it differs in the unhelpful direction.**
On SLURP, widening reaches trajectories that are **more** key-degenerate than both the population and
the set already being dispatched — on the exposed half nearly a third of the additions (9 of 27) share
a single retrieval key. On Audio2Tool, widening reaches the **two most distinct** keys available,
against a reachable set whose ratio is 0.333 and whose largest cluster covers 11 of 15.

---

## 5. Supply quality among the newly dispatched

| population | new | non-empty supply | gold-bearing | fused rank 1 | ranks 2–3 | rank ≥ 4 | gold absent | supplied values | distinct targets |
|---|---|---|---|---|---|---|---|---|---|
| unexposed 500 | 24 | 24 | **3** | 3 | 0 | 0 | **21** | 45 | 24 |
| exposed 500 | 27 | 27 | **9** | 9 | 0 | 0 | **18** | 54 | 27 |
| A2T-104 | 2 | 2 | **2** | 2 | 0 | 0 | **0** | 4 | 2 |

Gold-side accounting is the gold-absence diagnosis' own, through the imported
`fusion_form_offline_gate._ordered_supplied_targets`: a supply *carries gold* when its ordered
`task_target` set contains the gold target, and the fused target rank is that target's position in the
fuser's own ordering, by the score of its best **admitted** supporting facet.

Note the shape: gold is either at **rank 1 or absent entirely**. There is no middle. That is what the
frozen `top_l = 3` target budget plus a one-hot fused label distribution produces, and it means the
supply on this set is not "roughly right" — it is either correct at the top or it does not contain the
answer at all.

---

## 6. The projections — LABELLED PROJECTIONS

Construction: four branches, **three of them exact**. (1) A retained trajectory carries its own
contact-0 direct decode exactly. (2) A trajectory whose dispatch is unchanged carries its sealed
outcome exactly — `α` does not touch the supply, so the evidence prompt is byte-identical. (3) A newly
dispatched trajectory that the **flight itself dispatched** at the same supply carries its **sealed
evidence decode** exactly — measured, not projected. (4) Only a newly dispatched trajectory with no
sealed decode at all is priced, at the campaign's measured anchors.

Anchors (`k1_hybrid_ranking_gate._anchor_rate`, source
`docs/readiness/2026-08-25-ec-and-retain-override-projections.md` §3): fused top-1 **108/110 =
0.9818**, fused ranks 2–3 **16/23 = 0.6957**, gold absent **0/67 = 0.0000**; the rank-4-or-worse point
is a labelled extrapolation and was **not used** — 0 trajectories were priced at it on any population.

| population | locked-cell baseline | `α` | exact retained | exact carried | **MEASURED sealed** | priced | Δ pessimistic | **Δ central** | Δ optimistic |
|---|---|---|---|---|---|---|---|---|---|
| unexposed 500 | 382/500 | 0.40 / **0.45** | 340 | 160 | 0 | 0 | 0.00 pp | **0.00 pp** | 0.00 pp |
| unexposed 500 | 382/500 | ≥ 0.50 | 316 | 160 | **3** | 21 | **−3.58 pp** | **−3.41 pp** | **−0.01 pp** |
| exposed 500 | 367/500 | 0.40 / **0.45** | 334 | 166 | 0 | 0 | 0.00 pp | **0.00 pp** | 0.00 pp |
| exposed 500 | 367/500 | ≥ 0.50 | 307 | 166 | **6** | 21 | −1.98 pp | **−1.81 pp** | +1.79 pp |
| A2T-104 | 63/104 | 0.40 / **0.45** | 89 | 15 | 0 | 0 | 0.00 pp | **0.00 pp** | 0.00 pp |
| A2T-104 | 63/104 | ≥ 0.50 | 87 | 15 | 0 | 2 | +1.34 pp | **+1.89 pp** | +1.89 pp |

Variance prior, as registered: DEV-100 round-5 replication, ±2 per 100 at 8-slot decode. The A2T band
(+1.34 to +1.89 pp on n = 104, i.e. 1.4 to 2.0 samples) is **inside** that channel and is a mechanism
reading, not an effect size.

**These are decision-sizing arithmetic, not forecasts. No single number here may be quoted as an
expected accuracy.**

The unexposed-500 baseline recomputed here, **382/500**, is the locked-v1 counterfactual the lock
verdict states independently (`+20.80 pp with the override removed`). It agrees.

---

## 7. The only MEASURED evidence about widening dispatch — and it inverts across the split

The v2 `δ ≥ 0.14` retain-override is the only dispatch-widening rule this study has ever **flown**. Its
fires are the only trajectories on these populations that were actually dispatched outside the
control's dispatching set, so their answers are **sealed and measured, not projected**.

| population | `δ` fires outside the control set | also reached by `α ≥ 0.5` | **not** reached | of those reached: correct BEFORE evidence | of those reached: correct AFTER the sealed evidence contact |
|---|---|---|---|---|---|
| **unexposed 500 (held out)** | 3 | **3** | 0 | **3** | **0** |
| exposed 500 (previously seen) | 11 | **6** | 5 | 0 | **6** |
| A2T-104 | 0 | — | — | — | — |

Read the two rows together.

- On the **previously-exposed** half, the 6 trajectories that both rules reach were **all wrong**
  before evidence and **all 6 became right** after it. Widening looks free.
- On the **held-out** half, the 3 trajectories that both rules reach were **all right** before evidence
  and **all 3 became wrong** after it. Widening cost 3 samples.

This is the identical in-sample / out-of-sample inversion that falsified the `δ` bar, now measured on
the subset `α ≥ 0.5` would specifically reach. It is 3 samples, and 3 samples is not a result — but it
is the *only* real decode evidence that exists on this question, and it points the wrong way on the
only population that was held out.

Note also that the two rules are **overlapping but not nested**: 5 of the 11 exposed-half `δ` fires are
*not* reached by any `α` on the registered grid. Neither rule's reached set contains the other's, so
the `δ` result is direct evidence about part of what `α` would reach and silent about the rest.

---

## 8. THE ADVERSE PRIOR, carried beside the risk column and never apart from it

> The `δ ≥ 0.14` retain-override was a hand-fit dispatch-widening rule whose registered property was
> *zero loss by construction*. It held on every exposed population and in the A4 flight. Out of sample
> it **recovered 0 of 3 and damaged 3 of 3** (net −3 samples, −0.60 pp), while the 11 fires in the
> previously-exposed half recovered **11 of 11**. Two of the three failures sat at `δ = 0.140362`,
> `0.000362` above the hand-fit bar. It was removed from the locked cell at `d9fef537`.

**`alpha` is a structural parameter, not a hand-fit rule, so this prior does not transfer
mechanically.** `alpha` was not fit to any population; it is a term in the policy form with a closed
derivation, and moving it is a change of form rather than a threshold tuned to data.

But the *failure mode* the prior names — **widening dispatch damages trajectories that were already
right** — is exactly the quantity §2's risk column measures, and §7 shows the `δ` override's own
out-of-sample damage set is a **subset** of what `α ≥ 0.5` reaches on the unexposed half. The prior is
not evidence about `alpha`. The measurement in §7 is.

---

## 9. What changing `alpha` costs beyond accuracy — stated as a TRADE, not a verdict

**The byte-identical transfer.** The locked cell `configs/policy/kb-policy-v1-dev100.json` (sha256
`d68afd2c…a919`, `knobs` block byte-unchanged across the lock commit) ran a **second carrier with no
knob edited at all**. That is not an accuracy property; it is a scientific asset, and arguably the
single strongest sentence the second carrier has produced. **Changing `alpha` breaks it.**

**A per-carrier `alpha` costs more.** §2 shows the two carriers pointing in opposite directions: the
same step that projects **+1.89 pp** on Audio2Tool projects **−3.41 pp** on the SLURP held-out half,
and puts **20** currently-correct trajectories at risk there against **0** on Audio2Tool. A value
chosen to serve one carrier will not serve the other. Choosing per carrier converts "one cell, two
carriers" into "one method, tuned per carrier" — a materially weaker claim.

**This is stated as a trade and not a verdict.** It is an owner decision: buy reach on one carrier,
sell the strongest generality statement the study has. No implementer may make that trade, and this
document does not make it.

---

## 10. POST-HOC DIAGNOSTIC — why the table is flat above 0.5

Declared as post-hoc: this block was added **after** the registered quantities were computed, to
explain the shape of the registered reach table. It introduces no outcome measure and carries no
verdict.

The decision is a threshold on one scalar, `gap = max_rival f(rival) − f(direct)`. Its distribution is
not spread across the unit interval — it is piled at the two ends.

| population | label-recovered, non-empty supply | `gap ≤ 0` (direct holds the top fused score) | `0 < gap < 1` | **`gap = 1`** (all fused mass on one rival) | median gap | fused distribution one-hot |
|---|---|---|---|---|---|---|
| unexposed 500 | 338 | 249 | 65 | **24** | **−1.000** | 226 |
| exposed 500 | 333 | 234 | 72 | **27** | **−1.000** | 213 |
| A2T-104 | 89 | 56 | 31 | **2** | −0.012 | 34 |

Bar-clearing counts, by `α`:

| population | 0.40 (bar 1.5000) | 0.45 (1.2222) | 0.50 (1.0000) | 0.55 (0.8182) | 0.60 (0.6667) | 0.65 (0.5385) |
|---|---|---|---|---|---|---|
| unexposed 500 | 0 | 0 | **24** | 24 | 24 | 24 |
| exposed 500 | 0 | 0 | **27** | 27 | 27 | 27 |
| A2T-104 | 0 | 0 | **2** | 2 | 2 | 2 |

Three consequences the owner should have in hand:

1. **`alpha` is a switch, not a dial.** Every `α ∈ [0.50, 1.00)` selects the same set on every
   population. There is no operating point between "veto on" and "veto off".
2. **The registered grid's top is already saturated.** Not one of the 65 / 72 / 31 middle-bucket
   trajectories clears even the `α = 0.65` bar of 0.5385, so reaching a 25th unexposed trajectory
   would require an `alpha` **above the registered grid**. This row does not compute that, and does
   not propose it.
3. **On SLURP the supply usually agrees with the direct answer already.** The median gap is **−1.000**
   on both halves: for at least half the label-recovered trajectories the fused label distribution
   places *all* of its mass on the direct label itself. The veto is not overriding a disagreeing
   supply in those cases; there is no disagreement to override. Audio2Tool sits in a different regime
   (median −0.012).

---

## 11. Provenance, and what could not be verified

Pinned inputs, all sha256-verified at load and re-published in the receipt: SLURP TRAIN snapshot
`e27b2745…a51b57` (60-intent label vocabulary); Audio2Tool snapshot `ec2f9ec4…3baf9fb2` (151-entry
tool vocabulary); the sealed `SAEA-DEV1000-BASELINE-LOCK` M0 and BLEND arm outputs and per-sample
mechanical records; the sealed `SAEA-A2T-G1` attempt-4 arm. TRAIN **value** vectors were never opened.

**Carried limitation.** The pinned Audio2Tool snapshot is historical evidence and carries the
pre-repair `prior_score` defect (193 of 12,601 values outside `[0,1]`, supremum 4.1). The repair built
a corrected snapshot at a new path that nothing consumes. `kb_policy._dimension_scales` divides the
prior to the common scale before the ranker sees it and `_fused_label_scores` normalises, so the
defect does not propagate into the blend arithmetic reported here — but it is stated rather than
hidden.

**Registration provenance.** The row was written to `docs/exposure-ledger.md` before this module's
first input was opened, and was committed at `9ea74f6b` — a **concurrent session's** ledger commit
(`ledger(scoreboard-v5)`) which swept the already-present row in alongside its own. The row text is
byte-unchanged and its sha256 is published above, so the registration is verifiable independently of
which commit message carries it.

**Not verified, and out of scope.** What the frozen core would actually answer on any of the 24 / 27 /
2 newly-dispatched trajectories that the flight did not itself dispatch. Only a registered flight can
answer that, and this row does not request one.

---

## HARD STOP (restated)

**No value of `alpha` is recommended. No change is proposed. No change is authorized.** `alpha` remains
0.45 in the frozen cell. THE LOCK stands exactly as landed at `d9fef537`.
