# SLURP intent lock at COMP-1b (owner decision 229, 2026-10-09)

Author: Fable 5.1 (root coordinator). Zero contacts; every number is read from sealed, scored arms already in
the record. Status: **binding lock for the SLURP INTENT metric**; SLU-F1 stays OPEN (the NX slot line,
`docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md`).

## 1. Rule (decision 229)
"Replicated" = the CI95 lower bound of the paired delta is above zero on DEV-2000-ADDED AND on the signed test
sample `SLURP-TEST-SAMPLE-3010-V1`, for the same metric, with the same arm bytes. This rules decision 210.

## 2. Evidence

| read | roster | n | intent delta pp [CI95] | SLU-F1 delta pp [CI95] | source |
| --- | --- | ---: | ---: | ---: | --- |
| A2 (COMP-1b vs A/A) | DEV-2000-ADDED | 1,000 | +4.60 [+2.58, +6.73] | +0.53 (crosses 0) | `docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md` |
| milestone successor (COMP-1b vs PLAN) | signed test sample, natural mixture | 3,010 | +5.80 [+4.04, +7.42] | +0.79 [-0.44, +2.02] | `docs/results/2026-10-01-slurp-milestone-successor1-read.md` |
| same, equal intent strata | | | +3.02 [+1.03, +4.82] | +0.91 [-0.38, +2.42] | same |

Intent levels on the test sample: 77.02 % (PLAN) -> 82.82 % (COMP-1b). Both lower bounds are above zero for
intent; neither is for SLU-F1.

## 3. What is locked
The COMP-1b arm bytes as flown in the milestone (lock v2.1 base + `agree-vote-seed` + `centroid-boundary-key` +
the k60 recall pool; cell lineage `slurp-native-stage3-comp1b-*`, milestone package
`docs/readiness/2026-09-29-slurp-stage3-comp1b-testsample-v1/`). It is the ONE base of every NX round (decision
228 = A). The bundle is locked as a whole: the milestone cannot credit a single component (the read's own caveat).

## 4. What is not claimed
No SLU-F1 gain; no final test, publication or generalisation claim (study CLAUDE.md, Stage-3 boundary); no
carrier release -- Audio2Tool / Earnings-21 stay HELD until the R5 composed read (decision 229 as ruled); the
test sample is closed again until a second allowance is signed (decision 233). Development numbers remain
development numbers (decision 28).
