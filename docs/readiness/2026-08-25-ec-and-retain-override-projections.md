# E-C (A3) and retain-override (A4) — model-free projections and registered predictions

Date: 2026-08-25. Status: **DESIGN INPUT — no verdict, no knob selected, no round authorized.**
Profile: `model-free-check`. Exposure row `SAEA-SN-MF-EC-RETAIN-OVERRIDE-PROJECTIONS` (registered
before any computation; **0** frozen-core contacts, **0** embedding-tool contacts, **0** audio
seconds, **0.0** GPU hours).

This note covers the two experiments queued at
`2026-08-24-kwiden-and-next-experiments-queue.md` §4 items 2 and 3, so that each can fly against a
falsifiable prediction. It selects nothing. The result that dominates both is a mechanical one, and
it is stated first because it changes what item 2 even is.

## 1. Authority, scope, and non-contact

- Owner discipline `2026-08-23-knowledge-plane-baseline-rulings.md` §7.2 (iterate on exposed data
  before concluding); queue order from `2026-08-24-kwiden-and-next-experiments-queue.md` §3b.
- Consumed, all already landed and already scored: the sealed DEV-100 **round-4** and **round-5**
  frozen-cell attempt stores, the sealed DEV-500 confirmatory **BLEND** arm restricted to the
  unexposed-at-the-time **NEW400**, the committed round/arm reports and split receipts, the pinned
  TRAIN snapshot `e27b2745…a51b57`, and its landed content-facet NPZ `0bcb955a…21c72`. TRAIN
  **value** vectors stay SEALED and were not opened.
- Devel gold is read scoring-side only, over samples whose gold was already lawfully opened.
- **Non-contact is proven by construction, not by a service log.** The module calls
  `analysis.dev100_reviewer_audit.arm_offline_guard()` before opening a single input; measured
  **0 outbound connection attempts**. A concurrent K-WIDEN flight holds the resident decoder unit,
  so this analysis makes **no** server-log byte-identity claim and touches no file belonging to
  another campaign.
- Tool: `src/speech_aware_evidence_acquisition/analysis/dev100_next_experiment_projections.py`,
  which imports and re-runs `contrast_fewshot_preanalysis`'s own population loader and replay —
  and through it the damage-channel module's `LandedInputs` / `replay_supply` / `replay_blend`
  holders over `rails.kb_policy`'s pure functions. `rails/`, `core/`, and the launchers are
  untouched. Exactly one new per-sample quantity is added (`direct_target_evidence`).

### 1.1 Fidelity, re-asserted

| population | retain/dispatch decision vs the flown contact count | supply ids vs the flown SUPPLY channel | final answer provenance |
|---|---|---|---|
| DEV-100 round 4 | **100/100** | **37/37** exact | evidence text on **37/37** dispatched |
| DEV-100 round 5 | **100/100** | **33/33** exact | evidence text on **33/33** dispatched |
| DEV-500 NEW400 | **400/400** | **130/130** exact | evidence text on **130/130** dispatched |

The analysis refuses to run if either gate fails. The third column matters for A4: a dispatched
trajectory's scored answer **is** the evidence contact's own text, so overriding retain-primary
really does replace the answer rather than only re-labelling it.

## 2. The mechanical result — A3 and A4 are one experiment seen from two sides

`kb_policy._blend_scores` gives every label `L` the score
`alpha·fused[L] + (1−alpha)·[L == direct_label]`, and `_fused_label_scores` normalizes `fused` to
sum to 1. So whenever a direct label was recovered at all:

```
blended[direct] = alpha·fused[direct] + (1 − alpha)  ≥  1 − alpha  =  0.55
blended[other]  = alpha·fused[other]                 ≤  alpha      =  0.45
```

At the frozen `alpha = 0.45` the protect-direct constant strictly dominates, so **a recovered
direct label is always the blend's unique argmax and always retains.** Two exact consequences:

1. **The dispatched set IS the dead-direct set.** The frozen cell's dispatch rule is not a
   confidence rule at all — it is the single predicate *"the direct answer named no TRAIN intent"*.
   Confirmed measurement-side on every population: dead-direct that dispatched **37/37, 33/33,
   130/130**; live-direct that dispatched **0, 0, 0**.
2. **E-C as briefed is an off-switch for the evidence plane.** A label-enum schema that makes
   contact-0 always name a TRAIN intent makes the direct label live on 100% of samples, which by
   (1) drives the evidence-contact count to **zero**. E-C alone does not refine the frozen cell; it
   degenerates it to a one-contact direct arm.

Dispatch can only survive a live direct label if `alpha·(fused[top1] − fused[direct]) ≥ 1 − alpha`,
which needs `alpha > 0.5` even in the most favourable case. That is the A4 surface — and §6.3 shows
the alpha knob is a bad way to reach it.

## 3. The shared empirical anchor — measured, not modelled

Given a dispatched evidence contact, how often is the final answer gold, as a function of where
gold sits in the fused label set? Pooled over all three sealed populations (disjoint trajectories
of the same frozen cell):

| where gold sits in the supply | measured | rate |
|---|---|---|
| gold is the fused **top-1** | **108 / 110** | **98.2%** |
| gold at fused rank 2 or 3 | 16 / 23 | 69.6% |
| gold **absent** from the fused set | **0 / 67** | **0.0%** |

Per population, gold-at-top-1 is 21/21 (r4), 19/19 (r5), 68/70 (NEW400). The frozen core follows
the supplied evidence very strongly: when the supply names gold first it answers gold almost
always, and when the supply does not contain gold at all it never recovers it.

**Why this transfers to A4's counterfactual.** `rails.runner` builds the evidence contact from the
speech packet plus the supplied values alone — the direct answer is never placed in it. An evidence
contact on an overridden trajectory therefore sees the same *kind* of prompt as the ones already
flown, with the same supply arithmetic behind it.

**Its limitation, stated rather than hidden.** By §2, every sample that dispatched under the frozen
cell is a dead-direct sample, so the anchor is measured where the direct answer was already
off-vocabulary. A4's population instead had a fluent, legal, but wrong direct answer. The anchor is
used as-is and the residual is named in the falsifier (§6.5).

---

# EXPERIMENT A3 — E-C constrained contact-0

## 4. The dead-direct set: size, resolution, and what the fields already contain

### 4.1 Size and resolution (A3a)

| | DEV-100 r4 | DEV-100 r5 | NEW400 |
|---|---|---|---|
| dead-direct samples | **37 (37.0%)** | **33 (33.0%)** | **130 (32.5%)** |
| of which resolved by retain-primary | 0 | 0 | 0 |
| of which resolved by an evidence contact | **37** | **33** | **130** |
| correct today | 23 | 20 | 81 |
| wrong today | 14 | 13 | 49 |
| **their own direct answer scored correct** | **0** | **0** | **0** |
| live-direct samples | 63 | 67 | 270 |
| of which retained | 63 | 67 | 270 |
| live-direct correct today (= their direct answer) | 49 | 52 | 208 |

Two facts to carry: every dead-direct sample is answered today by the evidence contact, and none of
their contact-0 answers is correct as written. The 23 / 20 / 81 correct dead-direct samples are
exactly the conversion the knowledge plane is currently buying.

### 4.2 Why the normalizer failed, per sample (A3b)

| partition | r4 | r5 | NEW400 | meaning |
|---|---|---|---|---|
| **no fields at all** | 0 | 0 | 3 | no `scenario`/`action` pair parsed |
| **swap-recoverable** | 7 | 7 | 14 | a real TRAIN intent with the two fields *exchanged* |
| **parseable but out-of-vocabulary** | **30** | **26** | **113** | a pair that is not a TRAIN intent in either order |
| of the swap set, swapped identity **is gold** | 5 | 5 | 10 | a schema pinning field roles repairs these deterministically |
| of the OOV set, parsed scenario already **is gold's scenario** | 13 | 11 | 34 | the enum has a plausible path to gold |

So the dead-direct condition is overwhelmingly a **vocabulary** failure, not a formatting failure:
81% (r4) / 79% (r5) / 87% (NEW400) of it is an answer naming a pair that does not exist in the
60-way TRAIN label vocabulary in either order.

### 4.3 The blend replayed with the direct term switched on

Method: for every dead-direct sample, set `direct_label` to the label facet the model's **own**
logged `scenario`/`action` fields name — exchanged where the pair is a TRAIN intent only in the
swapped order — and re-run `kb_policy._blend_scores` / `_argmax_labels` at the frozen alpha.

**Outcome, and it is mechanical rather than statistical: retain-primary fires on 100% of them,
without exception and independently of which legal label is recovered**, because the protect-direct
constant dominates (§2). The evidence contact that today answers these samples is never dispatched,
and the scored answer becomes contact-0's own text.

Not knowable offline: which legal intent an enum-constrained decode would emit on an
out-of-vocabulary sample. The schema forces a choice from the 60-way vocabulary; the offline record
can bound that choice (§4.2's last two rows) but cannot resolve it.

## 5. The second-order effect — retrieval degradation vs the dead term (A3c)

The flown content-dimension query vector **is the embedding of the trajectory's own direct-decode
answer text** (the round launchers' `LazyQueryVector` is filled from that response). Contact-0's
output is literally the retrieval key for everything downstream of it, so the brief's second-order
concern is real and measurable.

| population slice | gold facet inside the top-5 recall window | gold is the fused top-1 | gold-facet cosine (median) |
|---|---|---|---|
| **DEV-100 r4** dead-direct (n=37) | 25 — **67.6%** | 21 — 56.8% | 0.7755 |
| DEV-100 r4 live-direct reference (n=63) | 46 — **73.0%** | 41 — 65.1% | 0.8279 |
| **DEV-100 r5** dead-direct (n=33) | 22 — 66.7% | 19 — 57.6% | 0.7755 |
| DEV-100 r5 live-direct reference (n=67) | 48 — 71.6% | 44 — 65.7% | 0.8281 |
| **NEW400** dead-direct (n=130) | 86 — **66.2%** | 70 — 53.8% | 0.7741 |
| NEW400 live-direct reference (n=270) | 200 — **74.1%** | 165 — 61.1% | 0.8361 |

Dead-direct retrieval is measurably worse: 5–8 pp fewer gold facets inside the recall window, 7–8 pp
fewer golds at fused rank 1, and a ~0.05 lower gold-facet cosine. If E-C moved the dead set onto the
live-direct profile, that would put roughly **+2.0 (r4), +1.6 (r5), +10.3 (NEW400)** additional gold
facets inside the recall window.

**But the degradation tracks the answer's CONTENT, not the legality of its label.** Splitting the
dead set:

| dead-direct sub-slice | gold in top-5 window | gold-facet cosine (median) |
|---|---|---|
| swap-recoverable (right words, wrong slots) — r4 / r5 / NEW400 | 71.4% / 71.4% / 71.4% | **0.8693 / 0.8693 / 0.8551** |
| out-of-vocabulary pair — r4 / r5 / NEW400 | 66.7% / 65.4% / 64.6% | 0.7567 / 0.7747 / 0.7645 |

The swap-recoverable subset retrieves **at or above the live-direct reference on cosine**; the
out-of-vocabulary subset carries the whole deficit. So a schema that pins the field **roles** has a
plausible retrieval story. A schema that only restricts the label **enum** does not — and by
truncating free-form answer text it could *reduce* the lexical content the content-facet retriever
keys on.

**Confound, stated:** this comparison cannot separate *"the answer text was a bad retrieval key"*
from *"the sample was intrinsically harder, which is why the answer was off-vocabulary in the first
place"*. Both produce this contrast and no offline manipulation distinguishes them.

**And the decisive point:** under E-C as briefed, the second-order retrieval gain is unharvestable,
because by §2 nothing dispatches. It becomes real only if E-C is paired with A4.

## 6a. REGISTERED PREDICTION — E-C as briefed (A3d)

**Primary prediction, cheap to falsify and needing no accuracy read at all:** an E-C arm's
**evidence-contact count is ZERO** and its total frozen-core contact count equals its sample count.
This follows from §2 and is visible in the arm's own contact ledger.

| | DEV-100 r4 | DEV-100 r5 | NEW400 |
|---|---|---|---|
| frozen-core contacts today | 137 | 133 | 530 |
| **frozen-core contacts under E-C** | **100** | **100** | **400** |
| evidence contacts today → under E-C | 37 → **0** | 33 → **0** | 130 → **0** |
| retain-primary rate under E-C | 100%, forced | 100%, forced | 100%, forced |

**Accuracy prediction.** E-C flown alone lands **below** the sealed baseline on every population,
and its whole credible band lies below it.

| band | DEV-100 r4 (sealed 72) | DEV-100 r5 (sealed 72) | NEW400 (sealed 289) |
|---|---|---|---|
| pessimistic — schema repairs only the field order | **54** | 57 | 218 |
| central — plus half the scenario-correct OOV set | **60** | 62 | 235 |
| optimistic — plus all of them | **67** | 68 | 252 |
| projected change vs sealed | **−18 … −5** | −15 … −4 | −71 … −37 |

Band construction: the pessimistic edge assumes the schema repairs exactly what is
deterministically repairable — the field-role swap — and nothing else. The optimistic edge
additionally assumes every out-of-vocabulary answer that already named gold's **scenario** resolves
to gold once the enum forces a legal action. Nothing above that is defensible: an OOV answer that
names neither of gold's fields gives the offline record no reason to expect the constrained decode
to land on gold.

**Variance-channel honesty.** The projected loss is 5 to 18 per 100 on DEV-100, i.e. **2.5× to 9×
the documented ±2 per-100 direct-decode byte-variance channel**. Unlike the E-A prediction — whose
whole band sat *inside* the channel — this one is comfortably evaluable on DEV-100, and the
contact-count prediction is evaluable on a **single sample**. The band's own width is also large
relative to the channel, so a read confirms the *direction* robustly and the *magnitude* only
loosely.

**What would falsify it.** An E-C arm that dispatches **any** evidence contact falsifies §2 and with
it this entire projection — that would mean the flown normalizer or the flown blend does not behave
as the replayed one does. An E-C arm at or above the sealed baseline falsifies the accuracy
prediction and would mean the schema-constrained contact-0 is a far better *answerer* than the
unconstrained one, not merely a better-formatted one.

**Design consequence.** E-C should not be flown as briefed. Its defensible form is **E-C plus A4**:
the schema makes the direct label live everywhere, and the A4 bar then supplies the dispatch rule
the protect-direct constant would otherwise suppress. In that pairing E-C stops being a single
variable, so an attribution round needs **A4 flown first and alone**.

---

# EXPERIMENT A4 — retain-override dispatch variant

## 6. The class, the signal, and the curve

### 6.1 The retain-override-loss set, named (A4a)

Gold **is** the fused top-1, but retain-primary fired and the evidence contact was never dispatched.
Every member disagrees with the retrieval top-1 by construction. `δ` is the retrieval-preference
margin defined in §6.2.

**DEV-100 round 4 — 5 members** (round 5 has the same 5 plus `012045`):

| sample | gold | direct | supplied targets | fused top-1 score | fused margin | cos margin | cos top-1 | cos direct | **δ** |
|---|---|---|---|---|---|---|---|---|---|
| `002814` | iot_coffee | takeaway_order | 1 | 1.0000 | 1.0000 | 1.0000 | 0.8643 | 0.6925 | **0.1718** |
| `010037` | cooking_recipe | cooking_query | 1 | 1.0000 | 1.0000 | 1.0000 | 0.8281 | 0.6679 | **0.1602** |
| `011819` | recommendation_locations | takeaway_query | 2 | 0.5229 | 0.0458 | 0.0854 | 0.8419 | 0.6932 | **0.1486** |
| `001569` | iot_coffee | takeaway_order | 1 | 1.0000 | 1.0000 | 1.0000 | 0.8242 | 0.6960 | 0.1282 |
| `014125` | qa_factoid | music_query | 3 | 0.3384 | 0.0014 | 0.0039 | 0.8345 | 0.8306 | 0.0039 |
| *r5 only* `012045` | recommendation_locations | takeaway_query | 2 | 0.5422 | 0.0844 | 0.1512 | 0.8377 | 0.6772 | **0.1605** |

**NEW400 — 12 members**, δ from 0.2319 down to 0.0016. The five with δ ≥ 0.14 are `010017`,
`009926`, `010242`, `010070`, `009999` — **all `cooking_recipe` mistaken for `cooking_query`**. The
remaining seven (`011675`, `011666`, `002520`, `004729`, `012108`, `008953`, `011928`) sit at
δ ≤ 0.115. The class is dominated by a handful of confusable pairs on which the retrieval already
got the right answer.

Note the overlap with the E-A pre-analysis's DEV-100 reachable list: `011819` — the sample the
round-3 projection named as its predicted repair-loss and which E-A also targets — is recovered
here by a dispatch-rule change alone, with no contrast render. `014125` is out of A4's reach at any
usable bar.

### 6.2 The signal: a plain confidence bar does not work; a preference margin does

The briefed knob is a "confidence/margin bar" on the fused top-1. Two of the three obvious readings
are already known-degenerate: the fused top-1 **score** and the fused top-2 **margin** are bimodal
(contrast-fewshot pre-analysis §3), and the table above shows why — six of these samples score
exactly 1.0.

The third reading, **`cos_top1` alone, also fails**, and this is a measurement not an argument: on
every population the retain-override-loss members and the correct-retain members occupy the *same*
`cos_top1` band (DEV-100 losses 0.824–0.864 against correct retains 0.690–0.901, median 0.836), so a
plain confidence bar buys recoveries and disturbances at roughly one-for-one. At `cos_top1 ≥ 0.82`
on DEV-100 r4 it recovers 5 losses and disturbs 9 correct retains — net negative under §3's anchors.

The signal that works is the **retrieval-preference margin**

```
δ  =  cos_top1  −  cos_direct
```

where `cos_top1` is the fused top-1 target's best *percept-admitted* supporting facet, and
`cos_direct` is the direct answer's own target's best facet **anywhere** in the KB. The asymmetry is
deliberate and conservative: the direct answer is credited with its strongest evidence in the whole
snapshot while the retrieval is credited only with what it actually admitted, so a large δ means the
KB prefers the retrieved target *even under a handicap*.

Runtime-legal by inspection: the direct answer's parsed identity is the model's own output, the
facets and their vectors are the frozen snapshot, and the query vector is the one the controller
already computed. No gold, no future turn, no second answering model, and **no extra tool contact** —
`multidim_recall` already sweeps every content facet's cosine before truncating to `top_k`, so
`cos_direct` is a masked maximum over a vector the controller has in hand.

The classes separate on δ where they did not on `cos_top1`:

| population | δ of the retain-override losses | δ of the correct retains that would be disturbed |
|---|---|---|
| DEV-100 r4 | 0.0039, **0.1282, 0.1486, 0.1602, 0.1718** | 0.0085 … **0.117 (max)** |
| DEV-100 r5 | 0.0039, **0.1282, 0.1486, 0.1602, 0.1605, 0.1718** | 0.019 … **0.117 (max)** |
| NEW400 | 0.0016 … **0.1476, 0.1493, 0.1582, 0.1857, 0.2319** | 0.0 … **0.1338 (max)** |

### 6.3 Trigger curve (A4b) — trigger when the direct target is not the retrieval top-1 AND δ ≥ bar

The disagreement condition is **mandatory**, not optional: when the direct answer already agrees
with the retrieval's top-1 there is nothing for evidence to change, and firing would spend a contact
and put a one-contact trajectory at risk for nothing.

"projected" applies §3's measured anchors: recovered losses convert at 98.2%, triggered siblings
(gold at fused 2–3) at 69.6%, disturbed correct samples whose gold is *absent* from the supply are
lost at 100%, disturbed correct samples whose gold is *inside* the supply at 30.4%.

**DEV-100 round 4** (N=100, sealed 72, 63 retained, 20 trigger candidates):

| δ bar | triggered | losses recovered | other wrong | correct disturbed | of which gold absent | +contacts | projected |
|---|---|---|---|---|---|---|---|
| 0.00 | 20 | 5 | 2 | 13 | 12 | +20 | 64.6 |
| 0.02 | 17 | 4 | 2 | 11 | 11 | +17 | 64.9 |
| 0.05 | 13 | 4 | 0 | 9 | 9 | +13 | 66.9 |
| 0.08 | 8 | 4 | 0 | 4 | 4 | +8 | 71.9 |
| 0.10 | 8 | 4 | 0 | 4 | 4 | +8 | 71.9 |
| **0.12** | **4** | **4** | 0 | **0** | 0 | **+4** | **75.9** |
| **0.14** | **3** | **3** | 0 | **0** | 0 | **+3** | **75.0** |
| 0.15 | 2 | 2 | 0 | 0 | 0 | +2 | 74.0 |
| 0.18 | 0 | 0 | 0 | 0 | 0 | +0 | 72.0 |

**DEV-500 NEW400** (N=400, sealed 289, 270 retained, 78 trigger candidates):

| δ bar | triggered | losses recovered | other wrong | correct disturbed | of which gold absent | +contacts | projected |
|---|---|---|---|---|---|---|---|
| 0.00 | 78 | 12 | 11 | 55 | 37 | +78 | 260.4 |
| 0.05 | 45 | 8 | 7 | 30 | 29 | +45 | 269.6 |
| 0.08 | 22 | 7 | 3 | 12 | 12 | +22 | 284.6 |
| 0.10 | 20 | 6 | 3 | 11 | 11 | +20 | 284.6 |
| 0.12 | 7 | 5 | 1 | **1** | 1 | +7 | 293.6 |
| **0.14** | **6** | **5** | 1 | **0** | 0 | **+6** | **294.6** |
| 0.15 | 4 | 3 | 1 | 0 | 0 | +4 | 292.6 |
| 0.25 | 0 | 0 | 0 | 0 | 0 | +0 | 289.0 |

Round 5 replicates round 4 with one more member: at δ ≥ 0.14, 4 triggered / 4 recovered / 0
disturbed → 75.9; at δ ≥ 0.12, 5 / 5 / 0 → 76.9.

### 6.4 The risk side (A4c), and the knob that already exists

**Risk, known offline.** A disturbed sample's answer today **is** the logged direct-decode response,
correct by construction; overriding replaces a known-correct answer with an evidence-conditioned
one. This is why the low-bar rows are catastrophic: on DEV-100 r4 at δ ≥ 0, **12 of the 13** correct
retains the trigger selects have gold **absent from the fused set**, and §3's anchor says the core
recovers gold from a supply that does not contain it **0 / 67** times. Every one of those
disturbances is a near-certain loss of a known-correct answer. On NEW400 at δ ≥ 0 it is 37 of 55
unprotected plus 18 protected.

At the recommended bar the loss side is **structurally zero on all three populations** — no
already-correct retained sample clears it — rather than being a small difference of large numbers.

**Cannot be known offline.** The frozen core's answer to a prompt it has not been given. §3's
anchors say what happened on comparable flown trajectories; they are not a guarantee.

**The knob that already exists.** Raising `alpha` past 0.5 is the only way the frozen cell can
dispatch a live-direct trajectory without a new rule, so it is the honest comparison — a new knob
has to beat the knob already on the box. It loses badly, because alpha selects on the fused score
gap, which is degenerate:

| alpha | DEV-100 r4: newly dispatched / recovered / disturbed → projected (sealed 72) | NEW400 → projected (sealed 289) |
|---|---|---|
| 0.50–0.60 | 9 / 3 / 5 → **70.0** | 17 / 4 / 13 → **279.9** |
| 0.70 | 14 / 4 / 9 → 66.9 | 36 / 7 / 27 → 268.9 |
| 0.75–0.90 | 18 / 4 / 12 → 63.9 | 51 / 8 / 37 → 261.9 |

**Every alpha ≥ 0.5 is net-negative on every population.** The δ bar is net-positive. The difference
is not how strong the retrieval is; it is whether the KB has anything to say *for* the direct answer.

## 6.5 REGISTERED PREDICTION — A4 round 1 (A4d)

**Recommended knobs** (everything else byte-equal to the frozen cell
`configs/policy/kb-policy-v1-dev100.json`; **contact-0 unchanged**):

| knob | value | why |
|---|---|---|
| trigger signal | **retrieval-preference margin** `δ = cos_top1 − cos_direct` | the fused score, the fused margin, and `cos_top1` alone are all non-separating (§6.2) |
| **δ bar** | **0.14** | the smallest value that disturbs **zero** already-correct retains on all three sealed populations simultaneously |
| disagreement condition | **mandatory** | agreement leaves nothing for evidence to change |
| scope | trajectories retain-primary would finish in one contact | A4's entire surface |
| alternative bar | 0.12 (DEV-100-optimal) | recovers one more DEV-100 loss but costs one NEW400 disturbance; the extra recovery is inside the variance channel and the disturbance is not |

**Projected ledgers at δ ≥ 0.14:**

| | DEV-100 r4 | DEV-100 r5 | NEW400 |
|---|---|---|---|
| sealed baseline | 72/100 | 72/100 | 289/400 = 72.25% |
| triggered | 3 | 4 | 6 |
| extra frozen-core contacts | **+3** (137→140) | +4 (133→137) | **+6** (530→536) |
| retain-override losses recovered | 3 of 5 | 4 of 6 | 5 of 12 |
| other wrong retains triggered | 0 | 0 | 1 (gold at fused rank 2) |
| **correct retains disturbed** | **0** | **0** | **0** |
| band — pessimistic (69.6% conversion) | **74.1** | 74.8 | 292.5 = 73.12% |
| band — central (98.2%) | **75.0** | 75.9 | **294.6 = 73.65%** |
| band — optimistic (100%) | 75.0 | 76.0 | 294.7 = 73.67% |
| absolute bounds | [72, 75] | [72, 76] | [289, 295] |

Named samples the prediction stands or falls on — DEV-100 r4: `002814`, `010037`, `011819`
(r5 adds `012045`). NEW400: `009926`, `009999`, `010017`, `010070`, `010242`, plus `010218` as the
sibling case.

**Variance-channel honesty.** The central DEV-100 projection is **+3.0 (r4) / +3.9 (r5)** on 100,
which is **just outside** the documented ±2 per-100 direct-decode byte-variance channel — narrowly
evaluable on DEV-100, unlike E-A whose whole band sat inside it. Two things make the read cleaner
than that margin suggests: the loss side is projected at **zero by construction** at this bar rather
than being a small difference of large numbers, and the effect is carried by a **named set of 3–4
samples whose per-sample outcome is checkable**, so the round is scored per-sample and not only in
aggregate — the same discipline that turned the round-3 aggregate miss into a 96/100 per-sample hit.
The NEW400 replication projection is **+1.4 pp**, which needs the 400 tier to separate by a paired
test. **A4 should be screened on DEV-100 and confirmed at 400.**

**Effective-sample-size caveat.** Identical direct answers embed to identical query vectors, so the
candidate set collapses onto fewer distinct cosine points than it has samples: 16 distinct points
behind 20 DEV-100 r4 candidates, 17 behind 22 on r5, 51 behind 78 on NEW400. The bar's position is
fixed by a handful of clusters, not by every sample independently. The DEV-100 separation margin is
0.117 → 0.1282 (0.011 wide) and the NEW400 margin is 0.1338 → 0.1476 (0.014 wide); the two
populations agree on a clean interval of roughly **[0.135, 0.147]**, which is the only reason 0.14
is preferred over the DEV-100-optimal 0.12.

**Selection disclosure.** The bar was chosen by looking at all three sealed populations, which are
all exposed data. Under the owner's split-usage philosophy that is legitimate optimization, but it
means the bar is **fit, not validated**: its out-of-sample test is the DEV-1000 baseline-lock read
on the unexposed 500, not this projection.

**What would falsify it.** A flown A4 arm whose triggered samples do **not** convert — W→C of 0 on
the named recovered set — falsifies the central band and, with it, the transfer of the
gold-is-fused-top-1 anchor from the dead-direct dispatched subgroup to the live-direct overridden
one. A flown arm that disturbs a correct retain at this bar falsifies the zero-disturbance
construction. A flown arm at or below the sealed baseline falsifies the design.

## 7. What this document does not do

It registers no round, selects no knob, authorizes no flight, and reaches no verdict on the frozen
cell or on convergence. It adds one analysis module and this note. The queue decision — including
whether to fly A4 before or after K-WIDEN, and whether E-C is re-scoped as "E-C + A4" or dropped —
remains with the coordinator and the owner.
