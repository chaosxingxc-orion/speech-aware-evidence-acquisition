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

## 2. K-WIDEN mini-campaign — REGISTERED-NOT-FLOWN

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

## 4. Queue order (each single-variable, each projected offline first)

1. **K-WIDEN K1** (width 5→8; K2 at 16/32 only if K1 converts) — recall-limited class.
2. **E-A contrast few-shot** (owner priority) — confusable class.
3. **E-C constrained contact-0** — dead-direct class (also expected to improve the query
   text feeding retrieval).
4. **E-B v5 boundary injection** — confusable class, contrasted against E-A for attribution
   (the 117 pair-boundary relations are already built and validated at 0.807 balanced
   leave-one-out accuracy; this is an already-paid asset).
5. Winner-combination freeze → **DEV-1000 baseline-lock read** (packets prepped this
   session; the lock read touches the unexposed 500 once).
6. **Audio2Tool** generality campaign (gate open).

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
