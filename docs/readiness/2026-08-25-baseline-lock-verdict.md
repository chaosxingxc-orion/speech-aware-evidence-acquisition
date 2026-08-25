# BASELINE LOCK VERDICT — LOCKED at the v1 frozen cell; the δ override is FALSIFIED
# out of sample and removed

Date: 2026-08-25. Status: **LOCKED** (one-touch read consumed; row
`SAEA-SN-MF-DEV1000-LOCK-READ`; campaign row `SAEA-DEV1000-BASELINE-LOCK` consumed=yes;
verdict artifacts under `docs/checks/speech-aware-evidence-acquisition/2026-08-25-dev1000-lock-read/`).
Authority: the DEV-1000 baseline-lock preregistration (statistic, population, and lock
condition frozen in advance) under the owner ladder.

## 1. The registered outcome

**Primary statistic, 500 UNEXPOSED samples (DEV-1000 minus DEV-500):**
M0 278/500 = 55.60% → BLEND 379/500 = 75.80%; paired **+101 samples = +20.20 pp**;
**90% CI [+17.20, +23.40]** (0 of 10,000 replicates ≤ 0); 95% CI [+16.60, +24.00];
McNemar exact **p = 1.04e-25**; W→C 106 / C→W 5.

**LOCK CONDITION (90% CI lower bound ≥ +10 pp): MET, with +7.20 pp of margin.**

## 2. Scale stability — the question this tier exists to answer

| | DEV-500 unexposed 400 | DEV-1000 unexposed 500 |
|---|---|---|
| delta | +19.75 pp | **+20.20 pp** |
| 90% CI | [+16.50, +23.00] | [+17.20, +23.40] |
| σ̂ | 2.0563 | 1.8986 |

Each tier's point estimate lies inside the other's 90% interval and the intervals overlap:
**the effect does not shrink as the population doubles on disjoint held-out data.** The
mechanism picture is identical at both tiers: the dead-direct dispatch subgroup carries the
gain (3.13% → 62.50%, +59.38 pp on 160 samples), the retain subgroup is safe (+2.37 pp),
17 of 18 scenarios are non-negative (play +26, recommendation +23, qa +12; weather −1).

## 3. The δ retain-override is FALSIFIED out of sample and REMOVED from the locked cell

The v2 candidate carried the δ ≥ 0.14 retain-override, whose registered property was
**zero loss by construction** — it held on every exposed population (DEV-100 r4/r5,
DEV-500 NEW400) and in the A4 flight (3/3 recovered, 0 disturbed). Out of sample it
**fails**: of 14 fires, the 3 in the unexposed half recovered **0** and damaged **3**
(net −3 samples, −0.60 pp), while the 11 in the previously-exposed half recovered 11/11.
Two of the three failures are the same `music_likeness → play_music` confusion at
δ = 0.140362 — 0.000362 above the frozen bar. This is textbook overfitting of a bar fit on
exposed data, and it is exactly what the ladder's unexposed tier exists to catch.

**Consequence: the locked baseline is the v1 frozen cell**
(`configs/policy/kb-policy-v1-dev100.json`), NOT v2. This strengthens rather than weakens
the lock: without the override the unexposed-500 margin is **+20.80 pp** (382/500), i.e.
the locked configuration is the better one. The δ signal is not discarded as a research
direction — it is recorded as fit-not-validated, and any future use requires a bar derived
from unexposed data with its own held-out test.

## 4. What is locked

**`configs/policy/kb-policy-v1-dev100.json`** — α 0.45, τ 0.65, k/m 5, c 2, top_l 3, train
priors, rrf weighting, boundary stage off, facet-side percept admission, the f1060078
label-identity repair — over the KB-BUILD v1 full TRAIN snapshot
(`docs/receipts/knowledge/slurp-kb-size-full.json`), served by the BASE `llama.cpp-featcache`
binary at the np8 profile, executed through the openJiuwen AgentLoop
(`openjiuwen-workflow-v1`) with the two-contact knowledge-conditioned form.
Measured profile of the locked cell: DEV-100 72/100; DEV-500 unexposed-400 +19.75 pp;
DEV-1000 unexposed-500 **+20.20 pp measured as flown (+20.80 pp with the override removed)**.

This is the **baseline version for large-scale experiments**: its config hash, KB snapshot
hash, code commits, and serving profile are the reference every later comparison cites.

## 5. Scope — what the lock does and does not authorize

Authorizes: the Audio2Tool generality campaign against the locked form; training-free RL
work over a fixed environment (the dispatch surface is now a measured, live decision channel
— and §3 shows exactly how a hand-fit rule on that channel fails, which is the case FOR
learning it properly out of sample); DEV-tier engineering optimization (e.g. the measured
`multidim_recall` cost of 1.147 s/call × 2 per trajectory = +19 min CPU per 1,000
trajectories — vectorization/pre-indexing is the obvious target).
Does NOT authorize: test contact, superiority or generalization claims, or Stage-3 activity
(owner decision under `OWNER_GO_AND_PAPER_EXECUTION_CONTRACT`). FINAL60 stays reserved.

## 6. Disclosures carried

The δ bar was fit on exposed data and its failure is reported above rather than buried; the
preregistration §2 identity-hash erratum (DEV-100's hash quoted for DEV-1000; correct value
`8580d199…3c84` pinned and asserted at read time) moves no sample; two imported helpers
carry stale population labels in their metadata strings (arithmetic unaffected, modules
pinned to sealed reads); the 14 override trajectories' direct texts were recovered once from
the sealed durable trace and re-hashed to match. The read made zero contacts of any kind
(offline guard: 0 outbound attempts; resident service log byte- and hash-identical before
and after).
