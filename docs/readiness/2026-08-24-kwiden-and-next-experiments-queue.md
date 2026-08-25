# Next-experiment queue — K-WIDEN registered-not-flown, plus the information-gain agenda

Date: 2026-08-24 (end of session). Status: **DESIGN LANDED; NOTHING FLOWN.** Authority: the
DEV-500 confirmatory verdict §4 gates, the owner's iterate-before-concluding rulings (§7),
and the owner's 2026-08-24 directive to prioritize targeted contrastive few-shot for the
confusable-pair error class.

## 1. Error-root-cause → information-gain map (from sealed evidence)

The frozen cell's residual errors (28/100 DEV-100; 111/400 DEV-500-NEW400; C→W is 0, so
these are errors BOTH arms make) decompose as:

| Root cause | Share | Missing information gain | Registered remedy |
|---|---|---|---|
| Recall-limited (gold facet at rank 6-82; the knowledge IS in the KB) | ~1/3 | retrieval width/quality, not new knowledge | **K-WIDEN** (§2) |
| Confusable-sibling override (cooking_recipe↔cooking_query class) | ~1/4 | pair-discriminative evidence — ordinary cards do not separate siblings | **E-A contrast few-shot** (owner priority) then **E-B v5 boundary injection** |
| Dead-direct set (first answer names no TRAIN intent → protect-direct term inert) | 33-37% of samples | structured identity of the first answer | **E-C constrained contact-0** (label-enum JSON; M-line schema-v4 precedent 108/108 parse) |
| Intrinsic ambiguity / annotation noise | ~8-15/100 | none | none — reported honestly (supervised SOTA ≈85-90%) |

Information-theoretic corroboration (M-line audit): after action + entity signature, 0.55
bits of conditional scenario entropy remain, requiring pair-specific lexical evidence —
the same conclusion the error dissection reaches independently.

## 2a. K-WIDEN K1 — FLOWN AND SEALED 2026-08-25: width is INERT, and m is not the constraint

Round K1 (`recall_top_k_per_dimension` 5→8 coupled with `fusion.m` 5→8) flew on DEV-100 under row
`SAEA-DEV100-KWIDEN`, attempt `attempt-20260825T031812Z-dev100kw1`, exit 0. Spend 139/500 core,
102/300 tool, 365.81/1,500 audio-s, 0.083/0.6 GPU-h. Report
`docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-kwiden-k1/kwiden-k1-report.json`
(sha256 `66a340da…8f9f`).

| quantity | K1 (width 8) | sealed base (width 5) |
|---|---|---|
| correct | **71/100** | r4 72, r5 72 |
| W→C vs M0 (48) | 23 | 24 |
| C→W vs M0 | **0** | 0 |
| retain-primary | 64 (= direct-label-recovered 64) | 63 / 67 |
| dispatched | 36/100 | 37 / 33 |

**Delta −1: inside the ±2 byte-variance channel and inside the registered band 68–76 — no win, no
loss.** The offline width-5 supply replay (zero contacts, fidelity PASS) is the decisive read: the
width move **changed the admitted supply on 32/100 trajectories (15 dispatched) and produced 0
width-attributable outcome flips**. 12 of those 15 returned identical outcomes; the 3 flips all
carried byte-changed direct decodes, so all 3 are confounded into the variance channel.

**Why widening is inert — the structural finding.** The supplied-value distribution at m=8 is
2 values ×13, 3 ×6, 4 ×6, 5 ×8, 6 ×3: it **never exceeds 6 and mostly sits under it**, because
`fusion_c 2 × fusion_top_l 3 = 6` binds first and is **m-invariant**. Supporting facets track values
exactly. Raising m only permutes which targets are admitted inside an already-unsaturated budget, so
the k=8 reachability headroom (+2.75 pp) cannot reach the answer. Mechanism invariant held exactly
(retain == direct-label-recovered; 0 unchanged-direct anomalies, 0 mechanism anomalies).

**Stopping rule: CONVERGED-OR-FALSIFIED for width at this tier** (delta ≤ 0). **K2 at 16/32 is NOT
recommended as a width-only move** — the binding lever is the `c`/`top_l` supply budget, and beyond
it key construction. The ladder decision remains the coordinator's and the owner's.

## 2. K-WIDEN mini-campaign — original registration (superseded by §2a for outcome)

The experiment fragment `configs/experiment/slurp-dev100-kwiden-campaign-v1.json`, the
launcher `docs/checks/.../2026-08-24-dev100-kwiden-k1/launcher/launch_dev100_kwiden_k1.py`,
and `scripts/dev100_kwiden_prompt_fit.py` are complete and committed. **No exposure row was
created and nothing flew** (service log unchanged at the DEV-500 campaign's 3,571 launches;
zero contacts, zero spend) — the flight agent died on an API quota limit during prep.
Round K1's registered variable is the COUPLED width move `recall_top_k_per_dimension 5→8`
AND `fusion.m 5→8` (the damage analysis proved raising k alone changes 0 trajectories
because `top_m=5` re-truncates). Evidence basis: the DEV-500 reachability curve (k=5 71.5%,
k=8 74.25%, k=32 84.25%) with BLEND measured AT the k=5 ceiling. Resuming = register the
row, verify the prompt-fit envelope at m=8, fly.

## 3. Contrast few-shot (E-A) — owner-prioritized, pre-analysis in flight

Design: when the fused top-2 label margin is small (a runtime-legal signal), supply n=2-3
nearest exemplars PER SIDE of the confusable pair, contrastively rendered, and let the
evidence contact discriminate. **This is categorically different from the DEV-500
ABL-RANDICL arm** (random exemplars, measured NEGATIVE −5.5 pp) and from P-FEW (inert on a
strong-baseline routing surface): the exemplars are retrieved, pair-targeted, and balanced.
Literature support: retrieval-based demonstration selection beats random (KATE line);
Clear Up Confusion (COLING 2025) is differential guidance between ambiguous fine-grained
intents. A model-free pre-analysis (row `SAEA-SN-MF-CONTRAST-FEWSHOT-PREANALYSIS`,
registered `996dba61`) computes the trigger trade-off curve, the top-2/top-3 reachable
ceiling per error class, per-side exemplar availability, and a registered projection with
recommended n and margin threshold — E-A flies against that projection.

## 3b. E-A pre-analysis outcome (landed 2026-08-25) — the queue order changed

The model-free pre-analysis (`2026-08-24-contrast-fewshot-preanalysis.md`, commits
`996dba61`/`1d1cbe49`/`56ae63e6`/`49a7b129`) returned three decision-grade findings:

1. **The briefed trigger is degenerate.** The fused top-2 margin is bimodal (DEV-100: 66
   samples at exactly 1.0, 27 at ≤0.02, 7 in between) because the ranked score is an affine
   map of cosine with zero prior mass and constant agreement — every threshold in
   [0.10, 0.90] selects the identical set. The **cosine margin (cos1 − cos2)** is the
   replacement signal (equally runtime-legal, computed pre-dispatch).
2. **The residual is dominated by recall-limitation, not confusability**: DEV-100 28 errors =
   19 recall-limited / 5 retain-override-loss / 4 confusable-sibling; NEW400 111 = 81 / 12 /
   15 (+2 intrinsic, +1 admission). Gold ∈ fused top-2 on only 9 (DEV-100) / 27 (NEW400) —
   E-A's theoretical ceiling. A NEW error class was named: **retain-override-loss** (gold is
   the fused top-1 but retain-primary discarded it unseen) — a control-plane loss, not core
   failure; reaching E-A's ceiling requires overriding retain-primary.
3. **E-A cannot be evaluated on DEV-100**: its credible band (72/74/75 at 0/33/62%
   conversion) sits INSIDE the documented ±2 byte-variance channel. Any E-A read must be at
   the 400-sample tier or larger.

**Consequences for the queue: K-WIDEN is promoted to first** (it owns 68-73% of the
residual, exactly matching the reachability curve's headroom). E-A is retained as a
DEV-500-tier experiment with the cosine-margin trigger (θ≤0.02, n=3/side, override ON),
never a DEV-100 round. The retain-override-loss class becomes its own cheap candidate
(a dispatch-rule variant), sized at 5/28 DEV-100 and 12/111 NEW400.

## 4. Queue order (each single-variable, each projected offline first)

1. **K-WIDEN K1** (width 5→8; K2 at 16/32 only if K1 converts) — recall-limited class,
   **now first** (owns 68-73% of the residual per §3b). Machinery committed, zero spend.
2. **E-C constrained contact-0** — dead-direct class (also expected to improve the query
   text feeding retrieval; the M-line schema-v4 precedent parses 108/108).
3. **Retain-override-loss dispatch variant** — the class named by the E-A pre-analysis
   (gold is fused top-1 but retain-primary discards it): a cheap dispatch-rule single
   variable, 5/28 DEV-100 and 12/111 NEW400 in scope.
4. **E-A contrast few-shot at the DEV-500 tier** (owner priority, re-scoped per §3b):
   cosine-margin trigger θ≤0.02, n=3 per side, retain-primary override ON, disagreement gate
   OFF — never a DEV-100 round (its band is inside the variance channel).
5. **E-B v5 boundary injection** — confusable class, contrasted against E-A for attribution
   (the 117 pair-boundary relations are already built and validated at 0.807 balanced
   leave-one-out accuracy; this is an already-paid asset).
6. Winner-combination freeze → **DEV-1000 baseline-lock read** (packets PROMOTED 2026-08-25,
   1,000/1,000; preregistration `2026-08-24-dev1000-baseline-lock-preregistration.md`; the
   lock read touches the unexposed 500 once, lock condition = 90% CI lower bound ≥ +10 pp).
7. **Audio2Tool** generality campaign (gate open); before it, the multi-dimensional-K form
   upgrade (§5's agreement-inertness finding).

## 5. Knowledge-organization contribution ledger (what each KB form is worth, measured)

- Content facets (utterance-level text keys): the load-bearing key — retrieval-signal effect
  +15.75 pp (vs random-retrieval); k=5 reachability 71.5% is its ceiling.
- Label facets: dual duty — closed-set vocabulary AND the identity anchor the protect-direct
  term needs (damage 11→0 once the binding was repaired).
- Value payloads (exemplar + slots + priors): converted on the dispatched subgroup at 62.31%
  vs the direct arm's 2.31%.
- Supply STRUCTURE alone (two-contact form, signal randomized): +4.0 pp — the residue.
- Prior facets / `prior_score`: measured INERT in the flown dev form (w_prior→0 changes 0
  trajectories) despite train-side sweeps favoring it.
- Speaker facets: built, never activated (no vectors, no runtime consumption) — untested,
  not disproven.
- Multi-dimensional agreement: structurally inert — every facet carries exactly ONE
  dimension, so `agreement` is a constant 1/3. **The owner's multi-dimensional K design is
  therefore NOT yet realized in the flown form**; activating a genuine second dimension is a
  form upgrade queued before the Audio2Tool campaign.
- Decision graph / boundaries (v1→v5): precise but starved on the train side (4/4 helpful at
  7/108 firings); deliberately not flown in the dev campaigns.
