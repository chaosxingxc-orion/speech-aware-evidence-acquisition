# CONTRAST-FEWSHOT (E-A) pre-analysis — model-free trigger, ceiling, and registered prediction

Date: 2026-08-24. Status: **DESIGN INPUT — no verdict, no knob selected, no E-A round
authorized.** Profile: `model-free-check`. Exposure row
`SAEA-SN-MF-CONTRAST-FEWSHOT-PREANALYSIS` (registered before any computation; **0** frozen-core
contacts, **0** embedding-tool contacts, **0** audio seconds, **0.0** GPU hours).

This document reports what the sealed frozen-cell records already contain about the
owner-prioritised targeted-contrastive-few-shot idea. It selects nothing. Whether an E-A round
flies at all, and at which operating point, belongs to the coordinator and the owner.

## 1. Authority, scope, and non-contact

- Owner discipline `2026-08-23-knowledge-plane-baseline-rulings.md` §7.2 (iterate on exposed
  data before concluding); the owner's E-A priority (targeted contrastive few-shot for
  confusable-pair errors).
- Consumed, all already landed and already scored: the sealed DEV-100 **round-4** and
  **round-5** frozen-cell attempt stores, the sealed DEV-500 confirmatory **BLEND** arm
  restricted to the unexposed **NEW400**, the committed round/arm reports and split receipts,
  the pinned TRAIN snapshot `e27b2745…a51b57`, and its landed content-facet NPZ
  `0bcb955a…21c72`. TRAIN **value** vectors stay SEALED and were not opened.
- Devel gold is read scoring-side only, over samples whose gold was already lawfully opened —
  DEV-100 at each of the six round seals, NEW400 at the one-shot `SAEA-SN-MF-DEV500-CONFIRMATORY-READ`.
- **Non-contact is proven by construction, not by a service log.** The module calls
  `analysis.dev100_reviewer_audit.arm_offline_guard()` before opening a single input; it
  replaces `socket.socket.connect`, `connect_ex`, and `socket.create_connection` with counting
  refusers. Measured: **0 outbound connection attempts**. A concurrent K-WIDEN flight may hold
  the resident decoder unit, so this analysis makes **no** server-log byte-identity claim and
  touches no file belonging to another campaign.
- Tool: `src/speech_aware_evidence_acquisition/analysis/contrast_fewshot_preanalysis.py`, which
  imports and re-runs `rails.kb_policy`'s own pure functions through the damage-channel module's
  `LandedInputs` / `replay_supply` / `replay_blend` holders. `rails/`, `core/`, and the
  launchers are untouched.

## 2. Replay fidelity — arithmetic over flown trajectories, not a model of them

| population | retain/dispatch decision vs the flown contact count | supply ids vs the flown SUPPLY channel | committed-report anchors |
|---|---|---|---|
| DEV-100 round 4 | **100/100** | **37/37** dispatched, exact | 72 correct, 63 retain-primary — both reproduced |
| DEV-100 round 5 | **100/100** | **33/33** dispatched, exact | 72 correct, 67 retain-primary — both reproduced |
| DEV-500 NEW400 | **400/400** | **130/130** dispatched, exact | outputs and mechanical report hash-pinned via `ARM_PINS` |

The content-dimension recall is vectorised for tractability and cross-checked against a real
`kb.multidim_recall` call on a bounded probe per population; the vectorised cosine is
additionally pinned to `kb_policy._cosine` on every sample's top-8 facets plus its gold-bearing
facet. Every number below is arithmetic over flown trajectories.

## 3. The trigger as briefed is DEGENERATE — and the fix is one line of arithmetic

The briefed signal is the top-2 margin of the fused label distribution. Measured, it is not a
graded signal at all; it is **bimodal**:

| population | margin = 1.0 (one supplied target) | margin ≤ 0.02 | anything in between |
|---|---|---|---|
| DEV-100 round 4 | 66/100 | 27/100 | **7/100** |
| DEV-500 NEW400 | 223/400 | 143/400 | **34/400** |

The trade-off curve is consequently **flat**: on DEV-100 every threshold in `[0.10, 0.90]`
selects the identical 34 samples, 18 errors, 16 correct. On NEW400 every such threshold selects
the identical 177 samples, 75 errors, 102 correct. Choosing a threshold in that range is not a
design decision — it is a no-op.

**Why.** A content facet carries zero prior mass and a constant agreement term (§4.1 of the
damage-channel analysis), so its ranked score is the affine map `0.5·cos + 0.0667`. Cosines in
this snapshot live in a narrow band (≈0.65–0.90), so two or three sides' scores differ by a few
percent; `_fused_label_scores` then normalizes them to sum to 1, which squashes that spread
toward uniform. One supplied target normalizes to exactly 1.0. The margin therefore encodes
almost nothing except *how many targets were supplied*.

**The fix.** The un-squashed quantity is right there and is equally runtime-legal: the **cosine
margin** `cos1 − cos2` between the two sides' best percept-admitted supporting facets. Both
sides' cosines are already computed by the frozen controller before the retain/dispatch
decision, from the sample's own query vector and the frozen snapshot — no gold, no future turn,
no second answering model.

### 3.1 Trade-off curve on the cosine margin (DEV-100 round 4, N = 100, 28 errors)

"reach" = errors captured whose gold is inside the contrast pair. "disturbed" = already-correct
samples the trigger selects. "out" = of those, the ones whose gold is OUTSIDE the pair (the only
structurally unprotected case). "+contacts" = extra frozen-core contacts, i.e. triggered samples
that retain-primary would have finished in one contact.

| θ(cos) | triggered | errors captured | reach | disturbed | out | +contacts |
|---|---|---|---|---|---|---|
| 0.005 | 7 | 7 | 2 | 0 | 0 | +1 |
| 0.010 | 10 | 9 | 3 | 1 | 0 | +3 |
| **0.020** | **20** | **15** | **5** | **5** | **1** | **+7** |
| 0.030 | 26 | 17 | 5 | 9 | 3 | +11 |
| 0.050 | 31 | 17 | 5 | 14 | 7 | +16 |
| 0.120 (≡ ∞) | 34 | 18 | 6 | 16 | 7 | +18 |

### 3.2 The same curve on DEV-500 NEW400 (N = 400, 111 errors)

| θ(cos) | triggered | errors captured | reach | disturbed | out | +contacts |
|---|---|---|---|---|---|---|
| 0.005 | 33 | 15 | 3 | 18 | 5 | +17 |
| 0.010 | 57 | 24 | 10 | 33 | 6 | +34 |
| **0.020** | **91** | **38** | **14** | **53** | **12** | **+56** |
| 0.030 | 133 | 60 | 16 | 73 | 19 | +74 |
| 0.050 | 164 | 70 | 21 | 94 | 28 | +96 |
| 0.120 (≡ ∞) | 177 | 75 | 23 | 102 | 28 | +103 |

### 3.3 An optional disagreement gate, and why it is NOT recommended as the default

A second runtime-legal gate is available: fire only when the direct answer's own parsed label is
NOT the retrieval's top-1 target. It is cheap and it cuts disturbance and contact cost roughly in
half (DEV-100 at θ = 0.02: 16 triggered instead of 20, +3 contacts instead of +7).

It also **destroys two of the five reachable errors**, and it does so for a structural reason
worth recording: on the cleanest confusable pairs the direct decode and the retrieval make the
*same* mistake. `004338` (gold `takeaway_order`, direct `takeaway_query`, fused
`[takeaway_query, takeaway_order]`) and `007646` (gold `calendar_query`, direct `lists_query`,
fused `[lists_query, calendar_query]`) are exactly the cases E-A exists for, and in both the
direct label IS the retrieval top-1. The gate is therefore offered as the **conservative
variant**, not the default.

## 4. The ceiling — how much of the residual error E-A can even in principle reach

Error classes, mutually exclusive, in priority order. `retain-override-loss` is split out from
`intrinsic` deliberately: calling a sample "intrinsic" when the frozen core was never shown the
evidence would attribute a control-plane loss to the model.

### 4.1 DEV-100 round 4 — 28 errors

| class | errors | retained | dispatched | gold @ fused-1 | gold ∈ top-2 | gold ∈ top-3 | gold facet position (median / max) |
|---|---|---|---|---|---|---|---|
| recall-limited | **19** | 7 | 12 | 0 | 0 | 0 | 60 / 2572 |
| retain-override-loss | 5 | 5 | 0 | 5 | 5 | 5 | 1 / 1 |
| confusable-sibling | 4 | 2 | 2 | 0 | 4 | 4 | 2 / 3 |
| **total** | **28** | 14 | 14 | 5 | **9** | **9** | — |

Round-5 replicate (the exact-replication flight, also 28 errors): recall-limited 18,
retain-override-loss 6, confusable-sibling 4; gold ∈ top-2 = **10**, gold ∈ top-3 = **10**. The
partition is stable across the variance channel to ±1 per class.

### 4.2 DEV-500 NEW400 — 111 errors

| class | errors | retained | dispatched | gold @ fused-1 | gold ∈ top-2 | gold ∈ top-3 | gold facet position (median / max) |
|---|---|---|---|---|---|---|---|
| recall-limited | **81** | 37 | 44 | 0 | 0 | 0 | 46 / 2023 |
| confusable-sibling | 15 | 12 | 3 | 0 | 13 | 15 | 2 / 4 |
| retain-override-loss | 12 | 12 | 0 | 12 | 12 | 12 | 1 / 1 |
| intrinsic | 2 | 0 | 2 | 2 | 2 | 2 | 1 / 1 |
| admission-limited | 1 | 1 | 0 | 0 | 0 | 0 | 2 / 2 |
| **total** | **111** | 62 | 49 | 14 | **27** | **29** | — |

**Three findings the coordinator should carry forward.**

1. **The dominant channel is recall-limited: 19/28 (68%) on DEV-100 and 81/111 (73%) on
   NEW400**, with the gold-bearing facet at median position 46–60 and maxima past 2,000. No
   contrastive render reaches these — only wider recall or better keys, which is exactly the
   K-WIDEN surface. E-A and K-WIDEN are not competing designs; K-WIDEN owns three quarters of
   the residual.
2. **A two-way contrast adds essentially nothing over a three-way one.** Gold ∈ top-2 is 9 vs
   gold ∈ top-3 of 9 on DEV-100, and 27 vs 29 on NEW400. The third slot is worth **+2 samples on
   400**. Narrowing to a pair is justified by render clarity, not by coverage.
3. **The reachable set lives on the RETAINED side.** Only **2 of the 9** DEV-100 errors with
   gold in the pair, and only **4 of the 27** on NEW400, sit on trajectories that dispatched an
   evidence contact at all. So a dispatch-scoped trigger — one that only re-organises evidence
   contacts the frozen cell was going to make anyway, and therefore carries zero retained-side
   risk by construction — has a ceiling of **2 errors on DEV-100 and 4 on NEW400**. E-A confined to the existing evidence contacts is not worth a round. To reach its
   ceiling, E-A must be allowed to **override retain-primary**, which is a second variable and a
   real cost.

### 4.3 The six DEV-100 reachable errors, named

| sample | gold | direct label | fused targets (ranked) | cos margin | dispatched today |
|---|---|---|---|---|---|
| `002161` | music_settings | none | play_music, **music_settings**, play_podcasts | 0.0017 | yes |
| `004338` | takeaway_order | takeaway_query | takeaway_query, **takeaway_order** | 0.0054 | no |
| `007646` | calendar_query | lists_query | lists_query, **calendar_query** | 0.0101 | no |
| `014145` | qa_factoid | none | general_quirky, **qa_factoid** | 0.0120 | yes |
| `014125` | qa_factoid | music_query | **qa_factoid**, music_query, play_music | 0.0039 | no |
| `011819` | recommendation_locations | takeaway_query | **recommendation_locations**, iot_coffee | 0.0854 | no |

Four of the six are cases the retrieval already ranks gold first or second while a wrong direct
label is retained. `011819` is the sample the round-3 projection named as its predicted
repair-loss; it is still lost, and it is still reachable.

## 5. Exemplar availability per side — not the binding constraint

Measured over the WIDEST trigger set — every sample whose supply carries two or more targets
(DEV-100: 34 pairs / 68 sides; NEW400: 177 pairs / 354 sides), which is a superset of any
cosine-margin threshold's selection.

| tier | DEV-100 (min / p10 / median) | NEW400 (min / p10 / median) |
|---|---|---|
| supplied TODAY by the frozen fuser | 1 / 1 / **2** | 1 / 1 / **2** |
| near exemplars at τ = 0.65 | 1 / 4 / **49.5** | 1 / 3 / **44.5** |
| values in the KB for that intent | 25 / 100 / **283** | 18 / 78 / **198** |

Pairs where **both** sides have `n` near exemplars at τ: DEV-100 **32/34 (n=2), 31/34 (n=3),
30/34 (n=4)**; NEW400 **158/177 (n=2), 152/177 (n=3), 147/177 (n=4)**. The KB itself never
blocks the budget — its smallest intent carries 4 values and its median carries 128.

**The real finding here is imbalance, not scarcity.** The frozen fuser's `c = 2` cap combined
with the `top_m = 5` admitted window means only **37 of 68** DEV-100 sides and **214 of 354**
NEW400 sides currently receive two exemplars; the rest receive exactly one. **40-46% of the
sides of a confusable pair are represented by a single exemplar today**, while the other side
gets two. Balancing to `n` per side is a genuine change even on the pairs where both sides are
already present — and it is available at n = 3 on ~86–91% of triggered pairs.

## 6. Risk accounting for already-correct samples

At the recommended point (cosine margin ≤ 0.02, no disagreement gate):

| | DEV-100 | NEW400 |
|---|---|---|
| correct samples triggered | 5 | 53 |
| extra frozen-core contacts the trigger creates | +7 | +56 |
| gold inside the contrast pair (structurally protected) | 4 | 41 |
| **gold OUTSIDE the pair (unprotected worst case)** | **1** | **12** |

**Known offline.** On a retained correct sample the final answer today *is* the logged
direct-decode response, correct by construction. Forcing a contrastive dispatch replaces a
known-correct answer with an evidence-conditioned answer. That is the whole of the retained-side
risk, and it is why the dispatch-only scope carries zero retained-side risk — and also why it
has almost no ceiling (§4).

**Cannot be known offline.** The frozen core's answer to a CHANGED evidence prompt is not
knowable without a model contact. The offline record can report only the structural protection: a
contrast render keeps BOTH sides visible, so wherever gold is inside the pair the correct
exemplars stay in front of the core, and the direct answer stays in the trajectory as the blend
anchor. Where gold is outside the pair the render **removes** gold-bearing exemplars that
today's flat three-target supply carried — 1 sample on DEV-100, 12 on NEW400. That is a real,
counted, unquantifiable-offline risk.

**The standing negative control.** DEV-500 `ABL-RANDICL` proved random exemplars cost −5.5 pp
[−9.5, −1.5]. E-A must be distinguished from it *by construction*: same retriever, same
retrieved content, same exemplar source — only which of the recalled targets are supplied, and
how they are grouped and framed, changes. An E-A arm that alters the exemplar SOURCE would be
re-running `ABL-RANDICL`, not testing E-A.

## 7. REGISTERED PREDICTION for an E-A round 1

**Recommended knobs** (everything else byte-equal to the frozen cell
`configs/policy/kb-policy-v1-dev100.json`):

| knob | value | why |
|---|---|---|
| trigger signal | **cosine margin** `cos1 − cos2` over the two sides' best admitted facets | the briefed fused-score margin is degenerate (§3) |
| threshold | **θ(cos) = 0.02** | the knee: 5 of the 6 DEV-100 reachable errors, 14 of 23 on NEW400, at 1 and 12 unprotected disturbances |
| exemplars per side | **n = 3** | available on 91% (DEV-100) / 86% (NEW400) of triggered pairs; ~40% of sides get only 1 today |
| pair size | **2** | the third slot is worth +0 on DEV-100 and +2 on 400 (§4) |
| scope | **override retain-primary** | the dispatch-only ceiling is 2 (DEV-100) / 4 (NEW400) — not worth a round |
| disagreement gate | **off** (conservative variant: on) | it removes 2 of 5 reachable errors (§3.3) |

**Projected DEV-100 ledger (N = 100, sealed baseline 72/100):**

| | value |
|---|---|
| triggered | 20 of 100 |
| extra frozen-core contacts | +7 (≈144 per arm, vs 137 at the frozen cell) |
| errors captured | 15 of 28 |
| **theoretically reachable errors (gold in the pair)** | **5** |
| correct samples disturbed | 5, of which 1 unprotected |
| conversion band — pessimistic (0%) | W→C 0, C→W 0 → **72/100** |
| conversion band — central (33%) | W→C 2, C→W 0 → **74/100** |
| conversion band — optimistic (62%) | W→C 3, C→W 0 → **75/100** |
| absolute bounds (all 5 convert / all 5 disturbed break) | [67, 77] |

**Projected DEV-500 NEW400 replication ledger (N = 400, sealed baseline 289/400 = 72.25%):**

| | value |
|---|---|
| triggered | 91 of 400 |
| extra frozen-core contacts | +56 |
| errors captured | 38 of 111 |
| **theoretically reachable errors (gold in the pair)** | **14** |
| correct samples disturbed | 53, of which 12 unprotected |
| conversion band — pessimistic (0% convert, 10% of the unprotected lost) | 288/400 = **72.0%** |
| conversion band — central (33% convert, 5% lost) | 293/400 = **73.25%** |
| conversion band — optimistic (62% convert, 0% lost) | 298/400 = **74.5%** |

**Where the conversion band comes from.** The optimistic anchor is the sealed DEV-500 dispatched
subgroup: BLEND 62.31% vs M0 2.31%, W→C 78 / C→W 0 over n = 130
(`2026-08-24-dev500-confirmatory-verdict.md` §2). It is discounted because E-A's population is
strictly harder: **every triggered reachable error already had the gold-bearing exemplars in its
supply and was answered wrong anyway** — the exemplars were present but unorganised, and on the
retained ones the core never even saw them. The central band therefore assumes E-A recovers
about a third of the reachable set; the pessimistic band assumes the render buys nothing.

**The honest headline.** On DEV-100 the entire credible band — 72 to 75 — sits inside or barely
outside the documented ±2 per-100 direct-decode byte-variance channel. **An E-A round cannot be
evaluated on DEV-100.** If E-A is flown, its read must be on the 400-sample tier or larger, where
the central band's +1.0 pp is still small but at least separable from noise by a paired test.

**What would falsify this prediction.** A flown E-A arm whose W→C on the triggered reachable set
is 0 while its C→W on the disturbed set is positive falsifies the central band. A flown arm at or
below the sealed baseline falsifies the design.

## 8. What this document does not do

It registers no round, selects no knob, authorizes no flight, and reaches no verdict on the
frozen cell or on convergence. It adds one analysis module and this note. The E-A decision —
including the option of spending the next round on the recall-limited 68–73% instead — remains
with the coordinator and the owner.
