# Stage-3 re-plan v2: the next experiment rounds and the training-free RL improvements (2026-09-27, ~19:30Z)

Author: Fable 5.1 (root coordinator; planning, decomposition, review). Inputs: the 2026-09-27 result notes under
`docs/results/` (mechanism synthesis, knowledge content audit, AGREE arm error sources, AGREE read, ROLL-3, W2 offline,
verdict reclassification, A2T/Earnings gap diagnosis, A2T-AA read, throughput levers, boundary-key diagnostic), the
2026-09-26 intent error decomposition, the measurement instrument (`2026-09-26-slurp-stage3-measurement-instrument-v1.md`),
and owner decisions 149-168. Every number is a development number (decisions 28, 86). Supersedes the 14:40Z plan.

## 1. What the survey settles

1. **The law of gains.** Every admitted gain was row-matched content, keyed by the row's own speech, delivered to the node
   that decides (M1 +12.61 SLU, replicated +13.70; AGREE +3.33 intent). Every harm was a change of form without new
   row-matched content (index twin -9.97, EFF-1 -9.17, narrowing -11.74).
2. **Where the intent mass is** (AGREE arm, Fold A, 14.17 pp left): consumption 10.93 pp -- Solver choice 5.37, Perception
   drop 3.33, catch-all 3.06 -- against retrieval 2.31. On 77.8 % of wrong rows the gold card was already delivered; the
   delivered wrong intent is Perception's first hypothesis on 132 of 153 rows and the exemplars outvote gold on 107 of 152.
   The missing capability is contrastive evidence at the Perception/Solver decision.
3. **Where the SLU mass is** (34.84 pp): 27.13 on intent-right rows. Value vocabularies (9.29), do-not-tag scope (9.30) and
   span extent (5.33) are conventions; slot-side retrieval has an oracle of +17.4 SLU. The type card is present on 644 of
   660 error items -- values, not types, are missing.
4. **Closed lines** (do not re-fly): sampling/aggregation (90.5 % of rows keep one intent; oracle 77.5 on DEV), rank guards
   on the vote (W2 maximum +0.31), review-loop tuning without a reach change, index form, narrowing, pruning, VAR-2.
5. **Reviewer:** the deficit is reach (REVISE on 5.45 % of visits; repairs 64 vs breaks 9). REV-TFRL-1 (+0.80 declared,
   no-harm) is the first step; the confound (Planner/Solver texts also changed in the source arm) is stated.
6. **Route to 95:** rows must move across scenarios on most intents at once (top 16 of 43 intents perfect); a
   within-scenario action fix closes only 5.09 of 12.78 pp.
7. **Instrument:** cross-flight designs cost 2.5 pp at n = 1,080; a same-flight supply-variant design would read at about
   0.7 pp but needs `supply_variants` re-authorised and `outputs.py` support. The Fold A AGREE read is circular (weight
   chosen on Fold A): KEEP-PROVISIONAL until the DEV round.

## 2. The rounds

GPU-hours are the packages' own estimates. One resident geometry at a time; the filler queue takes every gap (decision 168).

| # | round | cells | GPU-h | reads against | status |
| --- | --- | --- | ---: | --- | --- |
| A0 | E41 four-row dry run (decision 158) | 1 | 0.2 | form gates R1-R3 | flip-ready, queued |
| A1 | COMP-1 + G5 on Fold A (decisions 152, 153, 160, 161) | 6 | ~9 | shared in-chain A/A; COMP-1 declared 3.23 | flip-ready, queued |
| A2 | **COMP-1 replication on DEV-2000-ADDED** (arm + A/A); the synthesis's rank-1 item; settles AGREE's KEEP-PROVISIONAL and every plan derived from it | 2 | ~3.4 | in-chain A/A, h 1.1520 intent | to register (model-free, now) |
| A3 | Wave 1 (decision 164): shared A/A of the AGREE bytes, then W1 card selection (K8, no-harm), W3a contrast cards (K1), W4 slot conventions (K2+K3+K4, no-harm; M4b analogue 1.33-2.20 is below the floor) | 4 | ~8 | the wave A/A | registering; W3 re-derived as W3a alone: the W3b exemplar cap removes no wrong-intent plurality on Fold A, scores GAIN 0 / HARM 0 on Fold B, and touches 700 blocks on rows AGREE got right, so it is a second change with no measured upside and is dropped (decision 164's one-change rule) |
| A4 | REV-TFRL-1 (decision 165) | 3 | 4.6 | own A/A, no-harm | registered, to re-flip |
| A5 | Filler chunks on Fold B, then re-seeded rounds (decision 168) | 6+ | 2.4 per round | pool reads | held, fills gaps |
| B1 | **Rank-visible rendering**: conversion probe (0.1 GPU-h, sealed rows) then arm + A/A; targets the 5.37 pp Solver-choice class (89 delivered-but-wrong rows, oracle 8.2 pp; Spearman of today's exemplar order 0.007) | 1 + 2 | 0.1 + ~3.8 | probe declares the expectation (decision 139) | to register after the probe |
| B2 | **W5 slot-side retrieval**: the candidate-conditioned slot view with a filter, plus speech-plus-candidate slot exemplars (oracle +17.4 / +16.5 SLU); the SLU main line, the same mechanism as M1 | 1 (+ the wave A/A) | ~3.5 | the wave A/A | to register |
| B3 | **Catch-all rule** on the agree-1 all-utterances signal (K5 3.06 pp, about 1.2 at the CONV rate; +1.4 tokens per row): offline design on sealed pools first, then one arm | offline, then 1 | ~1.9 | wave A/A | offline now (model-free) |
| B4 | **Explicit empty-entity decision** (FP-only rows 12.1 % / 10.8 %): offline first, but the offline floor on DEV-2000-ADDED is unmeasured (ROLL-3 measured only within-pool half-widths), so its own offline null is the first step | offline | 0 | offline null | model-free now |
| B5 | Reviewer TF-RL round 2: reach first (an explicit top-2 contrast shown to the Reviewer; engineering item) | 3 | ~4.6 | own A/A | after A4 reads |
| C1 | Milestone reads on the signed test sample (decision 151) after a dev-admitted composed arm and the owner's go | -- | ~1 | -- | after A2 |
| C2 | Audio2Tool: A2T-ORG-1 re-read against h_A2T 1.625 (model-free, now); A-C1 do-no-harm candidate formation with a same-chain direct A/A beside every arm (parameter-F1 margin 2.23); then A-C3 value grounding; the exemplar store (decision 157) after | 2 per arm | ~1 per pair | same-chain direct A/A | after the SLURP lock |
| C3 | Earnings: E41 sub10 (E-C0), then KC-E1f into the default plan (E-C1, needs an owner row), then retrieval-fed repair (E-C2) and the numeric re-listen (E-C3) | -- | -- | E21 own null | after A0 |

Order on the card: A0, A1, A2, A3, A4, B1 probe, B2, B1 arm, B3 arm, B5; A5 in every gap; C2/C3 when the SLURP line is
locked or the card would otherwise idle. About 31 GPU-h for A0-A4 plus B1-B3, roughly 1.5 days saturated.

Admission rule unchanged: an item enters COMP-2 (decision 138) only after its predecessor is replicated or root-caused;
the wave may fly before A2 reads (each cell measures one change against the AGREE bytes) but nothing from it is admitted
before AGREE replicates. No if-then on unread results (decision 139).

## 3. Training-free RL: the shortfalls the survey exposes, and the changes

The locked algorithm: sealed-credit inner loop on sealed rollouts (`sealed-credit-system-policy-v1`), per-node credit,
fly only the composed policy, read against an in-chain A/A.

| shortfall (measured) | change | instantiated by |
| --- | --- | --- |
| The policy space explored is almost only *what to supply*; the residual mass (10.93 pp) sits at the decision node, where the policy has no discriminative action | Add a **contrast action** to the node policy: the deciding node is shown the top-2 (boundary plus exemplar) contrast, rank-visible, not a longer list | W3a (K1), B1 rank-visible rendering, B5 Reviewer top-2 |
| Credit is assigned on visits; the Reviewer intervenes on 5.45 % of visits, so its credit is thin and tuning quality first cannot move the arm | Optimise **reach before quality** for gate-shaped nodes (when to intervene); read the reach change as its own factor | REV-TFRL-1, then B5 |
| Rollout variation by temperature is exhausted (90.5 % one intent; oracle +1.74) | Vary the **evidence**, not the temperature: rollouts differ in supply (variants of the same row), which is also the same-flight design that reads at about 0.7 pp instead of 2.5 | engineering item: `supply_variants` re-authorised for the inner loop plus `outputs.py` support (owner decision needed) |
| Circular reads: weights tuned and read on Fold A | **Tune on Fold B / sealed pools, read on Fold A and DEV**; make the tuning roster and the read roster registered fields checked by the pre-launch gate | the wave already builds outside Fold A; add the gate field |
| Conventions delivered as rule cards are a form change (the harm pattern) | Deliver conventions as **retrieved row-matched slot exemplars** (the M1 mechanism); keep rule cards no-harm only | W4 read no-harm; W5 as the SLU main line |
| Entity credit is per item and the two taxonomies disagree (278/198 vs 253/173) | Register **one entity taxonomy** (SPURIOUS / MISSING / WRONG-TYPE / BOUNDARY) as the credit surface; W4 and W5 state which they are read against | a registration field in W4 and W5 |
| Cross-carrier bars: A2T parameter F1 moves +2.23 under a pure A/A; the tool-accuracy CI spans 8.5 points at n = 400 | Every Audio2Tool arm carries a same-chain direct A/A; parameter-F1 claims need the 2.23 margin | C2 |

## 4. Review checkpoints the coordinator holds (script-run, not prose)

- Before the wave flips: W1's selection rule is gold-free and keeps delivered-type coverage (a cap of 10 cuts it from
  99.3 % to 87.5 %); W4 states its base (the AGREE bytes, one change) and its taxonomy; the wave A/A plan bytes are proven
  identical to the AGREE arm.
- Before A2 flips: the DEV package's comparator is the in-chain A/A; the expected effect is declared from A1's read only
  after A1 is read (decision 139); the roster is DEV-2000-ADDED with its own null (h 1.1520 / 1.2525).
- Before B1's arm: the probe's conversion rate is the declared basis; the rendering changes nothing but order and rank labels.
- Every launch: `flight_registration_check.py`, `cli check`, the seven offline gates, and the handoff freshness stamp.

## 5. Decisions the owner is asked for

1. Insert A2 (the COMP-1 DEV-2000-ADDED replication) before the wave. Recommended: yes.
2. Register W5 slot-side retrieval against the wave A/A as the SLU main line. Recommended: yes, after W4 in the same chain.
3. Register the B1 rank-visible conversion probe (0.1 GPU-h) and the B3/B4 offline designs now. Recommended: yes.
4. Authorise the same-flight supply-variant instrument as an engineering-base item (sub-2.5 pp reads; also the rollout
   variation for the inner loop). Recommended: yes, engineering base.
5. A2T-ORG-1 re-read against h_A2T now (model-free); A-C1 registration after the SLURP lock. Recommended: yes / later.
6. Earnings E-C1 (KC-E1f into the default plan) after the E41 sub10 harness proof. Recommended: yes, one row.
