# DEV-500 confirmatory verdict — CLAIM CONDITION MET; DEV-1000 and Audio2Tool gates open

Date: 2026-08-24. Status: **CONSUMED** (one-touch read executed once; row
`SAEA-SN-MF-DEV500-CONFIRMATORY-READ`; verdict sha256 `b3187fea…90a3`; campaign row
`SAEA-DEV500-CONFIRMATORY` consumed=yes). Sources: four sealed arms (2,506 core contacts,
zero rail incidents), all hash-verified. Authority: the confirmatory preregistration
(`2026-08-24-dev500-confirmatory-preregistration.md`) — statistic computed exactly as frozen.

## 1. Registered outcome

**Primary (the 400 UNEXPOSED samples): M0 52.50% → frozen-cell BLEND 72.25%, paired
+19.75 pp; 90% CI [+16.50, +23.00] EXCLUDES ZERO (0/10,000 replicates ≤ 0); 95% CI
[+15.75, +23.75]; McNemar exact p = 7.2e-22; W→C 81 / C→W 2.** The preregistered claim
condition is **MET**: the frozen knowledge-conditioned two-contact form beats direct decode
on held-out dev data. The dev-tuned +24 transferred as +19.75 held-out — minimal shrinkage.

## 2. Attribution (the bracketing ablations, NEW400)

- BLEND − ABL-RANDRET = **+15.75 pp** [+12.5, +19.0]: the gain requires the retrieval
  SIGNAL, not merely the supply/second-contact structure (RANDRET − M0 = +4.0 pp is the
  structural residue).
- BLEND − ABL-RANDICL = **+25.25 pp**; ABL-RANDICL − M0 = **−5.5 pp** [−9.5, −1.5]: random
  exemplars actively hurt — the "any exemplars help" alternative is excluded; retrieval
  specificity is the mechanism.
- Dispatched subgroup (n=130): BLEND 62.31% vs M0 **2.31%** (W→C 78, C→W 0) — the
  retain/dispatch decision surgically targets direct-decode failures; retain subgroup
  (n=270) is neutral (+1). Exposed-100 secondary reading concurs (+21 pp, W→C 21 / C→W 0).
- Retrieval-reachability ceiling at the frozen top-k=5: **71.50%** — BLEND (72.25%)
  operates AT the retrieval ceiling; the curve (k=32: 84.25%, k=128: 93.00%; gold facet
  present for 400/400) quantifies the next tier's headroom: wider recall + key construction,
  not blend tuning. Zero of 18 scenarios regress.

## 3. Scope and caveats

Dev-tier confirmatory only: no test contact, no generalization/superiority claim, no
controller/RL claim. The charter-constrained oracle substitution (reachability ceiling in
place of a gold-conditioned supply arm) is disclosed wherever cited. Run-dir artifact hashes
were pinned at read time (disclosed); the read row's consumed-at-registration convention
follows the E108 precedent. Campaign spend 2,506/3,200 core · 7,122/8,000 audio-s ·
2.22/3.0 GPU-h.

## 4. Gates opened (per the owner ladder and standing approvals)

1. **DEV-1000**: the frozen cell reads once on the DEV-1000 tier's unexposed remainder
   (500 samples beyond DEV-500) for the baseline-lock decision; k-widening (top-k 8–32) may
   be dev-iterated on DEV-100/500 FIRST under a new registered mini-campaign before the
   DEV-1000 touch, per iterate-before-concluding.
2. **Audio2Tool**: the generality surface (152 tools, structural headroom) proceeds under
   its owner-approved plan — A2T KB build + the same frozen form + the same reviewer
   standards.
3. The training-free RL space stays open above the frozen cell: the retain/dispatch surface
   is now a measured, live decision channel (33% dispatch rate, +78/0 flip profile).
