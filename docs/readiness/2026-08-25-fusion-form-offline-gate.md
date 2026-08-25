# THE FUSION-FORM OFFLINE GATE — the three-kinds-in-one-sum critique is CORRECT and
# INERT. Every principled repair is an exact identity on the decision surface, and the
# one that is not is harmful. **NO FLIGHT IS PROPOSED.**

Date: 2026-08-25. Status: **ITERATION-TIER DESIGN INPUT — computed, zero contacts, every fidelity
gate passed, every candidate form REFUSED.** Row `SAEA-SN-MF-FUSION-FORM-OFFLINE-GATE` (registered
`f5cef94c`, BEFORE any computation). Module
`src/speech_aware_evidence_acquisition/analysis/fusion_form_offline_gate.py`. Receipt
`docs/checks/speech-aware-evidence-acquisition/2026-08-25-fusion-form-gate/gate-report.json`
(sha256 `568a78ee…7a69647`). Unit tests for the module's data-free arithmetic:
`tests/unit/test_fusion_form_offline_gate.py` (18 tests).

**Spend exactly as registered: 0 frozen-core contacts, 0 pinned-tool embedding contacts, 0
tokenizer contacts, 0 HTTP or socket requests, 0 audio seconds, 0.0 GPU hours, 0 new dependencies,
0 package installations.** `analysis.dev100_reviewer_audit.arm_offline_guard()` was armed before the
first input was opened and recorded **0 outbound connection attempts against zero targets**. The
resident llama-server (pid 38623, port 8090) was not started, stopped, probed, reconfigured or
contacted. Wall 322.4 s.

**No knob changed. Nothing under `rails/`, `core/` or `configs/` was written. Nothing hash-pinned
moved: no snapshot was rebuilt, no receipt was displaced, no arm was re-flown, no new sample was
touched and no new gold surface was opened.** The two deliverables named in the registration, plus
one unit-test file, are the only files this row adds. The full suite was re-run on the clean
committed tree: **4,232 passed, 9 skipped, 0 failed**.

> **EVERY NUMBER ON THE SLURP UNEXPOSED 500 IS A SECONDARY READING ON THE LOCKED BASELINE'S OWN
> POPULATION.** It must not be used to revise, re-tune or restate **THE LOCK**, which stands
> exactly as landed at `d9fef537`.

> **EVERY DOWNSTREAM ACCURACY AND EXTRACTION NUMBER IS A PROJECTION.** These are offline replays
> over SEALED decodes. A changed supply does not tell us what the frozen core would have answered.
> Small-*n* strata below are mechanism readings, never effect sizes.

---

## 1. The pre-registered falsifier, quoted verbatim from the ledger row at `f5cef94c`

> "A candidate scoring form is REFUSED unless ALL FIVE clauses hold. (F1) MUST IMPROVE - the form
> must strictly raise at least one of: the number of samples whose first gold-bearing facet lies at
> rank 5 or better in the ranker's own candidate list, or the number of dispatched trajectories
> whose supplied task_target set contains the gold target. A form that is an EXACT IDENTITY on every
> measured quantity is NOT LICENSED FOR FLIGHT: it is refused as NO MEASURABLE GAIN, which is a
> different verdict from HARMFUL and must be reported as such. (F2) MUST NOT DEGRADE, MATCHING AXIS
> - the number of samples whose first gold-bearing facet is at rank 1 in the ranker's own candidate
> list must not fall, and the count of dispatched trajectories that LOSE gold-bearing supply must
> not exceed the count that GAIN it. This clause exists because the K1 gate's falsifier was
> ONE-SIDED and would have licensed a flight that loses: RRF-60 raised recall-at-5 while lowering
> recall-at-1, and under the measured, steeply rank-dependent conversion anchors 23 demotions
> against 9 promotions does not close. (F3) MUST NOT DEGRADE, EXTRACTION AXIS - supply is delivered
> ONLY to dispatched trajectories, and the measured extraction gain is conditioned on dispatch
> (unexposed-500 dispatched n = 163: macro slot-F1 +9.4391 pts CI90 [+4.3558, +14.5194], official
> SLU-F1 +13.7570 pts CI90 [+8.8840, +18.6695]). A form must not reduce the number of dispatched
> trajectories that receive a non-empty supply, and must not reduce the aggregate number of distinct
> supplied task_targets or the aggregate number of supplied values on the dispatched set. (F4) MUST
> NOT DEGRADE, DISPATCH RATE - the projected dispatch rate must not fall below 90 percent of the
> flown rate on ANY population (SLURP unexposed flown-v2 163/500 = 32.60 percent, locked-v1
> reachable 160/500 = 32.00 percent; SLURP exposed 177/500 = 35.40 percent; A2T 15/104 = 14.42
> percent). A form projecting a relative dispatch-rate fall greater than 10 percent is an OFF-SWITCH
> and is refused on that ground alone, exactly as E-C and K3 were refused - K3 projected 15/104 down
> to 3/104, a fall of 80 percent. (F5) MUST NOT MOVE THE LOCKED CELL BLINDLY - the number of the 500
> UNEXPOSED SLURP decisions the form changes is reported explicitly for every form; any form
> changing one or more of them cannot be recommended for flight on offline evidence alone and
> requires its own registered flight, because a changed supply does not tell us what the frozen core
> would have answered."

It was evaluated **exactly as written**, on the primary unexposed 500 with the exposed 500 and
A2T-G1-104 as corroborating populations. No clause was re-worded, narrowed or extended. No arm was
added or dropped and no reported quantity was changed after the fact.

---

## 2. THE C0 FIDELITY GATE, FIRST AND FAIL-CLOSED — PASSED, count for count

Nothing below C0 was read until C0 reproduced the flown decisions.

| gate | result |
|---|---|
| SLURP DEV-1000 flown retain/dispatch decision reproduced per sample | **986 / 1,000** |
| the 14 deviations | **all 14 are exactly the v2 δ≥0.14 retain-override fires**, 0 unexplained (3 in the unexposed half, 11 in the exposed half) — the arm flew v2, the locked cell is v1 |
| SLURP flown SUPPLY reproduced value-id for value-id on dispatched samples | **340 / 340** |
| vectorised cosine agrees with `kb_policy._cosine` | **9,000 / 9,000** probes |
| vectorised recall agrees with `kb_policy.multidim_recall` | **8 / 8** probes |
| **full-KB gold-facet recall@k reproduces the SEALED lock read**, all ten *k* | **PASSED**: 318 / 352 / 362 / **372** / 389 / 396 / 408 / 433 / 443 / 470, gold absent 0 — the lock read's own published numbers |
| A2T attempt-4 flown supply reproduced | **104 / 104** |
| A2T flown dispatch decision reproduced | **104 / 104** |
| A2T flown direct-label recovery reproduced | **104 / 104** |
| **this module's own C0 path reproduces `dev100_damage_channel_analysis.replay_supply`** | **1,104 / 1,104** (500 + 500 + 104), value ids and admitted facets |

Pinned inputs, all sha256-verified before use: SLURP TRAIN snapshot
`e27b2745…3a51b57` (11,514 content facets), its landed content-facet NPZ `0bcb955a…0221c72`,
the DEV-1000 BLEND arm's committed mechanical report and its sealed outputs and per-sample
mechanical records, the A2T snapshot `ec2f9ec4…3baf9fb2`, and the three committed split receipts.
**TRAIN VALUE vectors were never opened.**

---

## 3. The per-form table

Read every variant row against **C0's own row**, not against zero. Populations: SLURP
DEV-1000-NEW500 (**UNEXPOSED — SECONDARY READING ON THE LOCKED CELL**), SLURP DEV-500 (prior-exposed
half of the same arm), Audio2Tool G1-104 (exposed).

Full-KB content-facet gold recall — a pure cosine ordering that **no scoring form touches**, so it
is identical for every arm and is the anchor the candidate-list column is read against:

| population | @1 | @5 | gold absent from KB |
|---|---|---|---|
| SLURP unexposed 500 | 318 (0.636) | 372 (0.744) | 0 |
| SLURP exposed 500 | 310 (0.620) | 368 (0.736) | 0 |
| A2T G1-104 | 55 (0.529) | 68 (0.654) | 0 |

### 3.1 SLURP UNEXPOSED 500 — **SECONDARY READING**

| form | cand @1 | cand @5 | gold absent | dispatched | non-empty supply | distinct targets | supplied values | gold-bearing supply | admitted facets | **decisions changed vs C0** |
|---|---|---|---|---|---|---|---|---|---|---|
| **C0** control | 318 | 372 | 128 | 160 (32.00 %) | 160 | 280 | 458 | 112 | 2,473 | — |
| **C1** cosine-only | 318 | 372 | 128 | 160 (32.00 %) | 160 | 280 | 458 | 112 | 2,473 | **0** |
| **C2** multiplicative label prior | 318 | 372 | 128 | 160 (32.00 %) | 160 | 280 | 458 | 112 | 2,473 | **0** |
| **C2B** λ = 0.10 / 0.25 / 0.50 | 318 | 372 | 128 | 160 (32.00 %) | 160 | 280 | 458 | 112 | 2,473 | **0** |
| **C3** RRF-60 across dimensions | 318 | **352** | 128 | 160 (32.00 %) | 160 | **205** | **320** | **106** | **992** | **199** |

### 3.2 SLURP EXPOSED 500

| form | cand @1 | cand @5 | gold absent | dispatched | non-empty supply | distinct targets | supplied values | gold-bearing supply | admitted facets | decisions changed vs C0 |
|---|---|---|---|---|---|---|---|---|---|---|
| **C0** control | 310 | 368 | 132 | 166 (33.20 %) | 166 | 286 | 476 | 116 | 2,489 | — |
| **C1 / C2 / C2B ×3** | 310 | 368 | 132 | 166 (33.20 %) | 166 | 286 | 476 | 116 | 2,489 | **0** |
| **C3** RRF-60 | 310 | **342** | 132 | 166 (33.20 %) | 166 | **210** | **331** | **108** | **997** | **215** |

### 3.3 AUDIO2TOOL G1-104

| form | cand @1 | cand @5 | gold absent | dispatched | non-empty supply | distinct targets | supplied values | gold-bearing supply | admitted facets | decisions changed vs C0 |
|---|---|---|---|---|---|---|---|---|---|---|
| **C0** control | 55 | 68 | 36 | 15 (14.42 %) | 15 | 43 | 47 | 4 | 520 | — |
| **C1 / C2 / C2B ×3** | 55 | 68 | 36 | 15 (14.42 %) | 15 | 43 | 47 | 4 | 520 | **0** |
| **C3** RRF-60 | 55 | **64** | 36 | 15 (14.42 %) | 15 | **28** | **30** | 4 | **208** | **69** |

### 3.4 The two-axis scoreboard, both axes PROJECTED

The **matching axis** is intent exact-match correctness — the axis the lock's +20.20 pp stands on.
The **extraction axis** is macro slot-F1 / official SLU-F1, whose only measured value is conditioned
on dispatch.

C0's own matching row is **not zero**, and that is a property of the comparison rather than an
effect: the control is the **locked v1** cell while the sealed outcomes come from the **flown v2**
arm, and the gap is exactly the 14 override fires (+0.6000 pp on the unexposed half = +3/500,
−2.2000 pp on the exposed half = −11/500, 0.0000 on A2T). Every variant is therefore read as
*variant minus C0*:

| form | unexposed 500 central (band) | exposed 500 central (band) | A2T central (band) | trajectories priced |
|---|---|---|---|---|
| C1 / C2 / C2B ×3 | **+0.0000 pp** (0, 0) | **+0.0000 pp** (0, 0) | **+0.0000 pp** (0, 0) | **0** |
| C3 | +0.2003 pp (−1.5739, +1.5709) | **−0.9004 pp** (−2.6174, +0.7855) | +0.3588 pp (+0.0836, +1.8881) | 87 / 95 / 14 |

C1, C2 and C2B price **zero** trajectories because none of their supplies differ from C0's: their
matching projection is an exact arithmetic zero, not a small estimate. C3's central projection does
not replicate across the two halves of the same arm (+0.20 pp against −0.90 pp) and its band spans
zero on two of three populations.

Extraction axis for C3, under three linear carriers that **disagree, which is the point** — a form
can keep every dispatched trajectory while thinning what each one carries:

| population | by dispatched trajectories | by distinct supplied targets | by supplied values | projected macro slot-F1 under the value carrier |
|---|---|---|---|---|
| unexposed 500 | 1.0000 | 0.7321 | **0.6987** | 9.4391 → **6.5950** pts |
| exposed 500 | 1.0000 | 0.7343 | **0.6954** | 9.4391 → **6.5637** pts |
| A2T G1-104 | 1.0000 | 0.6512 | **0.6383** | 9.4391 → **6.0250** pts |

None of the three is measured. The measured quantity is a single conditioned-on-dispatch gain at
the **landed** supply; no sealed decode says what a 30 %-thinner supply would have produced.

---

## 4. The falsifier verdict, per form

| form | F1 improve | F2 matching | F3 extraction | F4 dispatch | F5 locked cell | **verdict** |
|---|---|---|---|---|---|---|
| **C0** (control) | — | ✓ | ✓ | ✓ | ✓ (0) | **CONTROL** — the baseline, not a candidate |

C0's own per-population line in the receipt reads "REFUSED — NO MEASURABLE GAIN" because the control
is trivially an identity with itself; that row is definitional and is not a finding. The receipt's
`verdict_by_form` block labels it `CONTROL` for exactly that reason.
| **C1** cosine-only | ✗ | ✓ | ✓ | ✓ | ✓ (0) | **REFUSED — NO MEASURABLE GAIN** (an exact identity on every measured quantity on every population; expressly **NOT** the same verdict as HARMFUL) |
| **C2** multiplicative label prior | ✗ | ✓ | ✓ | ✓ | ✓ (0) | **REFUSED — NO MEASURABLE GAIN** |
| **C2B-0.10 / 0.25 / 0.50** | ✗ | ✓ | ✓ | ✓ | ✓ (0) | **REFUSED — NO MEASURABLE GAIN** (comparator; also introduces a knob absent from the frozen table) |
| **C3** RRF-60 across dimensions | ✗ | ✗ on SLURP, ✓ on A2T | ✗ | ✓ | ✗ (199) | **REFUSED on EVERY population — HARMFUL** |

**F4 holds for every form on every population**, including C3: the projected dispatch rate is
*unchanged* (unexposed 0.3200 = the locked-v1 rate exactly; exposed 0.3320; A2T 0.1442). **C3 is
not an off-switch in this cell**, and saying so is part of reporting it honestly — it is refused on
the supply it delivers, not on the trajectories it silences.

One property of F4's own anchors is worth a reader's attention: the exposed-500 anchor is the
**flown v2** rate 177/500, while the **locked v1** control only reaches 166/500. The control itself
therefore sits at 93.79 % of that anchor — above the 90 % bar, but the anchor and the control are
not the same cell. The unexposed population is the one where the registration supplies both anchors,
and against the locked-v1 anchor every form sits at exactly 100 %.

C3's F2 failure on SLURP is the specific two-sidedness this clause was written for: candidate-list
recall@1 does **not** fall (318 → 318 unexposed, 310 → 310 exposed), but **6 dispatched trajectories
LOSE gold-bearing supply against 0 that gain** on the unexposed half, and **8 against 0** on the
exposed half.

---

## 5. WHY C1, C2 AND C2B ARE IDENTITIES — two structural reasons, both measured

This is the substantive result of the gate, and it is not a null. **The incommensurability critique
is correct as a matter of form and inert as a matter of consequence**, for two independent reasons
that the locked cell already contains.

### 5.1 The ranker repair already made the prior term unable to displace an admissible content facet

`kb_policy._dimension_scales`' own proof states it: under the locked knob table the supremum of the
prior contribution is `w_prior × 1.0 = 0.300`, strictly below `w_cos × tau = 0.325`, so every
percept-admissible content facet outranks every prior-mass facet **by construction**. The gate
measured the premise on the pinned SLURP snapshot — prior supremum over the 60-label vocabulary
**exactly 1.0**, per-scenario sums **exactly 1.0**, total 18.0 across 18 scenarios — and then
measured the consequence:

| what C1 moves, per sample | unexposed 500 | exposed 500 | A2T 104 |
|---|---|---|---|
| gold **content**-facet candidate rank | **0** | **0** | **0** |
| admitted facet set | **0** | **0** | **0** |
| selected value ids | **0** | **0** | **0** |
| supplied task targets | **0** | **0** | **0** |
| dispatch decision | **0** | **0** | **0** |
| top-*m* window composition | 1 | 0 | 0 |
| gold **prior-mass**-facet candidate rank (rank > 5 throughout) | 46 | 42 | 2 |

C1 demotes prior-mass facets exactly as intended. On one sample of 1,104 that even changes which
facets occupy the top-*m* window — and **it changes which of them are admitted on none of them**,
because the facets it evicts were never admissible. The registration predicted this in advance and
wrote F1 so that the prediction, if it held, would be a refusal rather than a success. It held.

### 5.2 The alpha veto already makes the label-prior layer unable to reach a decision

`_fused_label_scores` feeds only the blend head, and at `alpha = 0.45 < 0.5` a **recovered** direct
label is the strict unique argmax of the blend for **every possible supply** (the fused scores are
non-negative and sum to at most 1, so the direct label's floor `1 − α = 0.55` exceeds any rival's
ceiling `α = 0.45`). Dispatch is therefore a function of direct-label recovery and supply emptiness
alone. Measured on all three populations, exactly:

| population | direct label recovered | dispatched | n − recovered | **dispatched trajectories with a recovered direct label** |
|---|---|---|---|---|
| SLURP unexposed 500 | 340 | 160 | 160 | **0** |
| SLURP exposed 500 | 334 | 166 | 166 | **0** |
| A2T G1-104 | 89 | 15 | 15 | **0** |

The reachable set *is* the label-free set, exactly. And so the kNN-LM / Bayes layer does real work
that reaches nothing:

| form | blend argmax moved (unexposed / exposed / A2T) | **retain–dispatch decision moved** |
|---|---|---|
| C2 multiplicative | 53 / 54 / 3 | **0 / 0 / 0** |
| C2B λ = 0.10 | 8 / 13 / 0 | **0 / 0 / 0** |
| C2B λ = 0.25 | 13 / 19 / 2 | **0 / 0 / 0** |
| C2B λ = 0.50 | 38 / 47 / 3 | **0 / 0 / 0** |

**C2 changes the blend's winning label on 53 of the unexposed 500 and changes the answer on 0 of
them.** That is the sharpest single fact this gate produced: the layer the candidate change moves
the prior *into* is structurally inert at the locked cell. This is a description of the current
policy form, not a proposal to change it.

---

## 6. Why C3 is refused, and what it shares with K3 and E-C

C3 is the literature's third answer and the one `_dimension_scales`' docstring had already rejected
on argument. The gate measured the mechanism: rank fusion gives every dimension's rank-1 facet the
identical score `1/61`, so the five prior-mass facets tie with the best content facets and the
`m = 5` window admits at most two content facets instead of up to five. Admitted facets fall
**2,473 → 992** on the unexposed half (−59.9 %), **2,489 → 997** on the exposed half, **520 → 208**
on A2T; the top-*m* window changes on **500 / 500 / 104** samples.

Carried beside it, as the registration requires: **K1 already measured RRF-60 raising gold-facet
recall@5 from 0.744 to 0.762 while LOWERING recall@1 from 0.636 to 0.590, and refused it for flight
on exactly that basis.** This gate's C3 is a different construction — RRF *across dimensions* rather
than across a dense and a lexical channel — and it does not reproduce K1's recall@1 loss. It fails
for a different reason: it thins the supply by roughly 30 % while keeping every dispatched
trajectory.

And the off-switch prior applies in the negative, which is the honest direction: **a form that
quietly suppresses dispatch is an off-switch in disguise; E-C and K3 were both refused on that
ground, K3 projecting 15/104 → 3/104, a fall of 80 %.** C3 does **not** do that. It is refused for
what it takes out of the envelope, not for closing the envelope.

---

## 7. F5 — exactly how many of the 500 UNEXPOSED SLURP decisions each form changes

A DECISION is the pair `(dispatched, sorted selected_value_ids)` — exactly what the flight recorded
and exactly what a re-flight would have to re-decide.

| form | decisions changed, of 500 | dispatch flips | supply-set changes |
|---|---|---|---|
| C0 (control) | — | — | — |
| **C1** | **0** | 0 | 0 |
| **C2** | **0** | 0 | 0 |
| **C2B-0.10 / 0.25 / 0.50** | **0** | 0 | 0 |
| **C3** | **199** | **0** | 199 |

C1, C2 and C2B move the locked cell on **zero** of its 500 decisions. C3 moves **199 of 500** and is
refused under F5 on that ground alone, quite apart from F1, F2 and F3: a changed supply does not
tell us what the frozen core would have answered.

For completeness, against the **FLOWN v2 record** rather than the v1 control, C0 itself differs on
3 of the unexposed 500 and 11 of the exposed 500 — the override fires, and nothing else.

---

## 8. DECLARED DEVIATIONS AND INTERPRETATIONS

Nothing in the registration was altered. The following are declared because a reader is entitled to
them.

**D1 — "first gold-bearing facet" was read two ways and both are published.** The registration pairs
"the ranker's OWN candidate list" with "the full-KB CONTENT-FACET ordering" in one sentence, and only
a facet carrying a cosine dimension can ever be percept-admitted, so the **content-facet** reading is
primary. The wider reading — any facet whose `task_target` is the gold target, prior-mass facets
included — was evaluated in parallel. **The two readings agree on every F1 and F2 verdict on every
population**; they differ only in C3's recall@5 column (352 vs 358 unexposed, 342 vs 349 exposed,
64 vs 65 A2T), and C3 falls under both.

**D2 — F5 was read two ways and the strict reading gates the recommendation.** The clause states a
reporting duty and a consequence. The duty is discharged for every form. The strict reading — the
clause holds only when the count is zero — is what gates a flight recommendation, because a nonzero
count is precisely the condition the clause says offline evidence cannot settle.

**D3 — C2 was implemented by post-multiplying the registered `_fused_label_scores` output and
renormalizing.** That is algebraically identical to multiplying the raw label scores before
normalization, because normalization is one positive scaling shared by every label:
`(raw_i/T · p_i) / Σ_j(raw_j/T · p_j) = (raw_i p_i) / Σ_j(raw_j p_j)`. The identity is asserted by a
unit test. The alternative — a second copy of `_fused_label_scores` — would have broken the
registration's "the REAL `_fused_label_scores` imported" requirement.

**D4 — C2's label prior is read over the WHOLE snapshot, not over `multidim_recall`'s top-5
truncation of the prior dimension.** The prior dimension recalls only 5 of 60 SLURP label facets;
a prior over 5 of 60 labels is not a prior over the label vocabulary. `kb_policy._facet_prior_mass`
— the registered function — is applied to every label facet instead. It is query-independent and so
a per-snapshot constant.

**D5 — the pinned snapshots are the HISTORICAL artifacts, and their priors were measured rather than
assumed.** The prior-score semantics repair built a corrected Audio2Tool snapshot **at a new path
that nothing consumes**; the pinned artifacts are what actually flew and are what this row reads.
Measured here: the pinned **SLURP** snapshot's `prior_score` is a genuine within-scenario
conditional probability — supremum exactly **1.0**, per-scenario sums exactly **1.0**, total 18.0
over 60 labels — so it is a probability but **not a label marginal**, and C2's use of it as a label
prior is correct only up to the unmodelled cell marginal. That is the registration's own second
honest prior, now measured. The pinned **Audio2Tool** snapshot's `prior_score` has supremum **4.1**
with 193 of 12,601 values outside [0, 1] and totals 45.88 over 151 labels: on that carrier the C2
prior is a relative frequency and not a probability at all. `_dimension_scales` divides it to the
common scale before the ranker sees it, and C2's own normalization is invariant to its overall
scale, but the limitation is reported rather than hidden.

**D6 — `dev100_damage_channel_analysis.replay_blend` is exercised inside the C0 fidelity gate but is
not the arms' blend path.** It hardcodes `kb_policy._fused_label_scores`, so an arm that changes that
layer cannot route through it. The arms call the registered `_fused_label_scores`, `_blend_scores`
and `_argmax_labels` individually, in that order — the same three functions the controller itself
calls.

**D7 — the SLURP content-dimension recall is the vectorised equivalent of
`kb_policy.multidim_recall`, gated against the real function rather than assumed** (8 recall probes,
9,000 per-facet cosine probes, then the whole supply replay gated against the flown SUPPLY channel).
On Audio2Tool the recall is the real `kb_policy.multidim_recall` itself, called for all 104
trajectories.

**D8 — the module was executed four times and three runs were discarded, for defects in MY OWN
measurement code and never in an arm or a clause.** (a) The content-facet gold reading was silently
matching prior-mass facets, because `contrast_fewshot_preanalysis`'s `content_facet_target` is keyed
by **every** facet a target-bearing value is associated with, not only its content facet. (b) The
comparison against the flown record compared a replayed supply against a **retained** trajectory's
null record, which the flight never writes. (c) The identity flag keyed on per-sample internals
rather than on the reported quantities, so F1's own named verdict — NO MEASURABLE GAIN — was not
being emitted for forms that are identities on every published number. **No arm definition, no
reported quantity and no falsifier clause was altered, and no OUTCOME changed across the three
repairs**: C1, C2 and C2B were refused for want of a gain and C3 was refused in every run. Repair (c)
changed the refusal's *name* to the one the registration demands.

---

## 9. RECOMMENDATION — **no flight is proposed, and that is the right outcome at zero cost**

**Refused, all four candidate forms, on all three populations.**

1. **C1, C2 and C2B are refused as NO MEASURABLE GAIN — not as harmful.** They are exact identities
   on every measured quantity, on the unexposed 500, the exposed 500 and A2T-G1-104, and they change
   **0 of the 500 locked decisions**. Proposing a flight for a change with a provable zero effect
   would spend a contact cell to measure nothing.
2. **C3 is refused as HARMFUL.** It cuts admitted facets by ~60 %, distinct supplied targets by
   ~27 % and supplied values by ~30 %, loses gold-bearing supply on 6 dispatched trajectories against
   0 gained (8 against 0 on the exposed half), and moves 199 of the 500 locked decisions. Its
   matching projection does not replicate across the two halves of the same arm.
3. **The critique that opened this row is CORRECT and the repair is INERT.** Three summands of three
   different kinds is a real defect of form. It is also, at the locked cell, unable to affect
   anything: the ranker repair already guarantees no prior-mass facet displaces an admissible content
   facet, and the alpha veto already guarantees no label-layer distribution reaches a dispatch
   decision. **The lever is not here.** A refusal at zero cost is a good outcome and is not dressed
   up as a disappointment.
4. **Nothing here authorizes anything.** A survival would at most have made a flight proposal worth
   writing; there was no survival, and any flight would in any case need the owner's contact-cell
   decision, which is pending.

**What would change the answer, stated so it is not re-derived later.** Both of §5's mechanisms are
knob-conditional, and neither knob is touched here. C2 and C2B could only ever matter in a cell with
`alpha ≥ 0.5`, where a supply can outvote a recovered direct label; C1 could only ever matter in a
cell where `w_prior × sup(prior) > w_cos × tau`, which the current table forbids by 0.300 < 0.325.
Both are knob changes, both belong to their own registered step, and neither is proposed here.

---

## 10. HARD STOP — what this document does NOT authorize

- **It does NOT revise, re-tune or restate THE DEV-1000 LOCK.** Every unexposed-500 number here is a
  SECONDARY reading on the locked baseline's own population and is descriptive only. The lock stands
  exactly as landed at `d9fef537`.
- **No knob change, no re-tune, no re-flight, no new arm, no threshold move, no alpha move.** In
  particular §5.2's alpha-veto measurement is a *description of the current policy*, not a proposal
  to raise alpha, and §5.1's identity result is not a licence to re-weight the ranker.
- **No claim.** No generality claim, no superiority claim, no cross-carrier transfer claim. The A2T
  column is *n* = 104 with 15 dispatched and 4 gold-bearing supplies: a mechanism reading, never an
  effect size.
- **No model contact, no tool contact, no test contact, no FINAL60 contact, no new population, no G2
  opening**, and no Stage-3 activity.
