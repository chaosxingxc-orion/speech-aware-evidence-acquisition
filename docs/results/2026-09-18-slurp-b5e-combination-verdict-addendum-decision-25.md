# Cell B5e: post-read addendum under owner decision 25 (combination re-read as NEUTRAL)

Status: **ADDENDUM, POST-READ.** Author: Fable 5.1, root coordinator, 2026-09-18. Authority: owner
decision 25 of 2026-09-18 (`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`).
The sealed verdict `docs/results/2026-09-18-slurp-b5e-combination-verdict.md` (sha256
`5e2ba383341f2c5544df044d5145b2064b5d5251f5981a27e1a56a6a00e54b6f`) is not edited; this note
supersedes ONE line of it, the combination status, and changes no number.

## What changes

The registered clause 3 (HARMFUL trigger) fired because the intent CI95 lower bound of
(B5e minus B1), -1.5136, crossed the own-null margin -1.0051, while the point estimate was -0.09
(26 saves / 27 harms, McNemar p = 1.000). Owner decision 25 fixes, for combination cells, that a
HARMFUL reading requires a measured loss: the intent or pooled SLU point estimate below -h, or a
CI95 upper bound below zero. Neither holds here (intent upper bound +1.38; SLU +1.20 [-0.11, +2.48]).

Amended combination status: **NEUTRAL; non-inferiority not proven at the request-identical margin.**
The beneficial gain is recorded as the owner asked: inside the combination M4b adds +1.20 pp official
pooled SLU-F1 [-0.11, +2.48] over B1 with the intent a tie, and its date/time work is visible in the
diagnostics (time omissions 15 -> 8, exact time mentions 30 -> 39 against B1). The interaction
-1.36 [-3.29, +0.56] stays a reported diagnostic.

## What does not change

The bar outcome (official 62.34 / 80.09: NOT MET by 1.66 pp SLU, owner decision 23), the
decision-20 path (B2 v3, B7a, B4a, then B5b), the non-registration of B5er, every contrast, every
table and the exposure statement of the sealed verdict.

## Why the margin misfired, for later preregistrations

h_intent = 1.0051 and h_SLU = 1.1218 are the CI95 half-widths of (B0r minus B0), two byte-identical
configurations differing only in batch composition: the narrowest interval this roster can produce.
A contrast between two DIFFERENT configurations is wider by construction (1.45 pp here), so its lower
bound crosses -h even at a true effect of zero. The single-factor admission clauses are unaffected
(they read the lower bound against zero for gains); combination cells now use the decision-25 form.
When a configuration's own request-identical replicate exists (the B4b replicate resume for M4b), its
half-widths are the preferred margins for contrasts involving that configuration.
