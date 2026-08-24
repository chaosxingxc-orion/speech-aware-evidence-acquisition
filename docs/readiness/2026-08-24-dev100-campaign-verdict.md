# DEV-100 campaign verdict — FROZEN at the α-0.45 cell; campaign complete at the 6-round cap

Date: 2026-08-24. Status: **CAMPAIGN COMPLETE AND FROZEN.** Authority: the campaign
preregistration (`2026-08-23-dev100-campaign-preregistration.md` + amendments) under the
owner's knowledge-plane baseline program and iterate-before-concluding rulings. Frozen knob
table: `configs/policy/kb-policy-v1-dev100.json`.

## 1. The six-round ladder (SLURP DEV-100, frozen split d676d38b…, gold at seals only)

| Round | Variable | BLEND | W→C / C→W | Notes |
|---|---|---|---|---|
| — | M0 direct decode (baseline) | 48/100 | — | 8× the 6% majority-class floor |
| 0 | baseline form (α .60, τ .5) | 63 | 26 / 11 | first dev flight of the frozen form |
| 1 | τ → .65 | 63 | 26 / 11 | **τ proven inert on [.5,.65]** |
| 2 | α → .55 | 65 | 28 / 11 | +2 later attributed to byte variance |
| 3 | label-binding repair (f1060078) | 67 | 24 / 5 | protect-direct term live; damage 11→5 |
| 4 | α → .45 (first live-α move) | 72 | 24 / **0** | damage channel CLOSED |
| 5 | exact replication (variance run) | **72** | 24 / 0 | **Δ=0; 98/100 per-sample repeats** |

Headline: **72/100 vs 48/100 direct (+24)**; zero correct→wrong at the frozen cell; cost
133-140 core contacts/round (retain-primary 63-67%). Spend: 1,550/2,500 core, 827/1,500
tool, 4,131.55/5,500 audio-s, well inside every amended ceiling.

## 2. Reviewer-elevation verdict (the owner's directive, answered)

- **Technically valid**: paired bootstrap 90% CI **[+11, +27]** (0/10,000 replicates ≤ 0);
  McNemar exact p 5.5e-4; conservative variance-channel floor **+15 [+6, +24]**; a +20
  stable core (24 repairs + 4 damages invariant across flights); train-prior rule scores
  39-41 (the gain is not a prior in disguise); in-session direct comparator gains +12..+20.
  (`2026-08-24-dev100-reviewer-audit.md`.)
- **Literature-consistent**: upper-middle of the published envelope; closest comparable
  kNN-Prompt (+13.4 avg / +28.9 max at similar baselines); the inverse-baseline-strength
  invariant reproduced internally; HyDE-mechanism pedigree for answer-text retrieval keys;
  the W→C/C→W contingency accounting is a contribution (no published precedent found).
  (`2026-08-24-dev100-literature-consistency.md`.)
- **Method demonstrated**: offline dissection → exact projection → flown verification, twice
  (round 3: 96/100 per-sample hits; round 4: 98/100; round 5 replication: 98/100 repeats;
  mechanism-level misses ZERO in all three) — the iterate-before-concluding discipline is
  now instrumented, not aspirational.

## 3. Mechanism findings of record

1. The **knowledge plane** carries the entire gain: evidence-conditioned decode with a
   TRAIN-built distribution-modeled KB; τ inert, rank-weight family mathematically inert
   (single-dimension facets), α inert until the label-binding repair.
2. The **label-identity binding repair** (f1060078) is what made the frozen baseline form's
   protect-direct term real: damage 11→5→0 as α became live; retain-primary 0→52→63-67.
3. The residual 28 errors partition into the 33-37-sample **dead-direct set** (the direct
   answer names no TRAIN intent — a key-construction topic) and **recall-limited retrieval**
   (gold facet at rank 6-82) — both OUTSIDE the registered knob family; they are the
   knowledge-construction agenda for the next tier, not tuning targets.
4. The dominant noise term is the **8-slot direct-decode byte-variance channel** (14-25/100
   direct bytes drift per rerun; ±2 samples on aggregates), fully characterized by the
   round-5 replication; single-slot decode is byte-deterministic (9× canary confirmations).

## 4. Engineering findings of record (the campaign's serving legacy)

Build-bound decode pathology (zero-copy build quarantined; base binary healthy at identical
~24.1 GiB peaks), the two-leg hosting recipe (systemd unit + Windows keepalive), the
decode-rate sentinel + canary + clock/VRAM sampling preflight suite, run-cumulative plan
semantics, AttemptStore as the spend authority, trace-sink isolation, prompt-reuse measured
at 0.83-0.88 (near the structural ceiling; per-trajectory prefix skips 100%).

## 5. What this verdict does NOT claim

No test-set contact; no DEV-500 claim (DEV-100 is a nested subset of DEV-500 — the
confirmatory statistic is registered over the 400 UNEXPOSED samples only); no
generalization or superiority claim; no controller/RL claim (the training-free RL space
sits untouched above the frozen cell, with the retain/dispatch decision now a live,
measured surface: 33-37% dispatch rate at the frozen point).

## 6. Next steps (per the ladder and the reviewer standards)

DEV-500 confirmatory preregistration: frozen cell, one-touch paired read on the unexposed
400 with CI/McNemar registered in advance; bracketing ablations (random-exemplar ICL,
random-retrieval, oracle-retrieval ceiling); a stronger prompt-matched direct control;
determinism pinning + the round-5 variance estimate carried as the config's variance prior.
Then Audio2Tool (structural-headroom surface) and DEV-1000 per the owner's ladder.
