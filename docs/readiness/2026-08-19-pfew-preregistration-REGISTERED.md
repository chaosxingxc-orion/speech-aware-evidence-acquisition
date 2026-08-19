# P-FEW — routing few-shot form probe — REGISTERED

Date: 2026-08-19. Status: **REGISTERED — flyable once the machinery lands** (GPU gap-filler
behind the M-line queue). Profile: `bounded-discovery-probe`. Owner GO: 2026-08-19 second-arc
design order ("重新设计一组探索任务计划…让GPU利用率拉满"). Arc: probe 1 of the
routing-tier × filling-tier program. Samples: the SAME frozen 60 SLURP devel samples (seed
20260807); decode config identical to the consumed P-SLU flights.

## 1. Question

Does few-shot demonstration supply improve HIGH-ORDER routing (closed-set scenario
selection), and how bias-sensitive is it to demo label skew? Per the 2026-08-19 discussion:
the word-level resonance law does NOT extend to the label level (class labels have no
acoustic relation to the audio; cross-sample demo values measured 0/32 capture in P-TRAP's
V2 arm), so no acoustic-distance condition applies; the risks under test are the classic
ICL ones — label-prior bias and coverage.

## 2. Arms (3 × 60 = 180 requests, one session)

All arms: closed-set scenario choice over the 18 canonical SLURP labels (the consumed
A1'r phase-1 construction, reused verbatim), single-phase (routing only — no phase-2
supply; this probe measures the ROUTER).

| Arm | Demos | n |
|---|---|---|
| FS-NONE | zero demos (in-session comparator; A1'r phase-1's 47/60 gold agreement is CITED context, never a substitute) | 60 |
| FS-BAL | K=4 demos, seeded from the TRAIN split (legal per the split philosophy, gold labels included), label-BALANCED (4 distinct scenarios, never the target's own recording) | 60 |
| FS-SKEW | K=4 demos, all four carrying the SAME seeded wrong-for-most-samples label (maximal prior skew) | 60 |

Demo rendering: transcript-text demos from TRAIN metadata (train gold transcripts are
legal supply per the program split philosophy — they never touch devel gold); demo format =
(utterance text → scenario label) pairs; seed 20260807; demo assignments fixed per sample
at binding, hash-pinned.

## 3. Metrics and verdicts (CI discipline; scoring-side gold labels)

Per arm: closed-set scenario accuracy vs gold (scoring-side), mapping-outcome distribution
(exact/case/substring/unmapped — the A1'r parser reused), per-sample 3-arm table; paired
bootstrap (shared `analysis/bootstrap.py`) on the two contrasts.
- **FS-HELPS**: acc(FS-BAL) − acc(FS-NONE) ≥ +0.10 AND CI lower bound > 0.
- **FS-INERT**: |acc(FS-BAL) − acc(FS-NONE)| ≤ 0.05 with the CI inside [−0.05, +0.05]
  (equivalence, CI-gated per the program's amendment discipline).
- **BIAS-SENSITIVE** (independent overlay): acc(FS-NONE) − acc(FS-SKEW) ≥ +0.15 AND the
  skew-label capture rate (fraction of FS-SKEW answers equal to the skewed label on samples
  where it is wrong) ≥ 0.25 — the router parrots the demo prior.
- Otherwise **INCONCLUSIVE-FEW**. Pre-read reachability statement mandatory (headroom on
  each contrast given FS-NONE's own measured accuracy).

## 4. Cost (registered ceilings)

180 requests; ≤200 core calls; ≤700 metered audio-seconds; ≤0.25 GPU-h.

## 5. Discipline

One-shot read; pinned suite (`analysis/pfew_read.py`, reusing the A1'r closed-set parser
and the shared bootstrap) built and coordinator-reviewed BEFORE the read; exposure row
`SAEA-PROBE-pfew-180` at registration (consumed=no); demo content TRAIN-split only
(binding-time fail-closed check: no demo recording id in devel; no devel gold anywhere in
any prompt); SLURP audio CC BY-NC 4.0 carried.
