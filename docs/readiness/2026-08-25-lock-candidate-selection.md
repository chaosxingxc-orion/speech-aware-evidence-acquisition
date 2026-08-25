# Lock-candidate selection — v2 = frozen cell + the δ retain-override; the retrieval-knob
# family is closed by evidence

Date: 2026-08-25. Status: **CANDIDATE FROZEN** (`configs/policy/kb-policy-v2-lock-candidate.json`).
Authority: the owner plan of 2026-08-24 (queue §4), the iterate-before-concluding rulings
(§7), and the DEV-500 confirmatory verdict §4.1 gate. This document selects what the
DEV-1000 lock read will test and records why every alternative lever was closed.

## 1. What was tried at this tier, and what each measurement returned

| Lever | Tier | Outcome |
|---|---|---|
| Retrieval width (`k`+`m` 5→8) — K-WIDEN K1, FLOWN | DEV-100 | **71/100 (Δ−1, inside the ±2 variance channel).** Offline width-5 replay: supply changed on 32/100 trajectories (15 dispatched), **0 width-attributable flips**. Structural cause: supplied values never saturate the budget, so width only permutes an unsaturated set |
| Supply budget (`c`,`top_l` variants incl. unlimited) — projection | DEV-100 + NEW400 | **0 newly gold-supplied errors on 600 sealed trajectories at ANY variant.** The real cap is `min(c·top_l, k)`; this KB associates ~one value per content facet, so the RECALL WINDOW binds, not the budget. The only channel-clearing cell is two-variable and breaks the prompt envelope by ~1,000 tokens |
| α / τ / rank weights | DEV-100 rounds 1-2 + counterfactual replays | inert (τ), degenerate (rank weights: single-dimension facets make `agreement` a constant), or exhausted (α flat across [0.30,0.45] once the label binding was repaired) |
| Constrained contact-0 (E-C as briefed) — projection | DEV-100 + NEW400 | **Rejected before flight**: recovering a direct label on every sample forces retain-primary at 100% (since `1−α > α`), taking evidence contacts to ZERO. Projected 54-67/100 vs 72 — an off-switch for the knowledge plane, 2.5-9× the variance channel |
| **Control-plane dispatch rule (δ ≥ 0.14 retain-override) — A4, FLOWN** | DEV-100 | **74/100. Prediction hit on all five registered quantities**: 3 triggered (exactly the named set), 3/3 recovered on both sealed bases, **0 correct retains disturbed**, +3 contacts, band 74.1/75.0/75.0 → flown 74. Mechanism channel = +3 clean; the aggregate +2 is inside the variance channel and is NOT claimed |

## 2. The convergent finding

Four independent measurements — one flown negative (width), one projected negative (budget),
one historical negative (α/τ/weights), one flown positive (dispatch) — say the same thing:
**the retrieval-knob family is exhausted at this tier; the control plane's dispatch rule was
the real lever.** The residual is dominated by recall-limitation (68-73%), but the reachable
route to it is the retrieval KEY (representation/construction), not width, not budget. That
places the next agenda squarely on key construction (multi-dimensional K activation — the
`agreement` term is provably constant today because every facet carries exactly one
dimension — plus the already-built v5 pair-boundary material), and it makes the dispatch
surface the natural home of the training-free RL work the owner reserved.

## 3. The lock candidate (v2)

v1 frozen cell (α .45, τ .65, k/m 5, c 2, top_l 3, train priors, rrf, boundary stage off,
facet-side admission, the f1060078 label-identity repair) **plus** the δ ≥ 0.14
retain-override on the dispatch rule. Composition rationale: the override is provably
BRANCH-ONLY (it changes which trajectories dispatch, never the blend arithmetic or the
supply), its loss side is zero BY CONSTRUCTION and held so in flight on both sealed bases,
and its recovery set is DISJOINT from every budget-variant recovery set (measured), so it
composes cleanly.

**Registered honesty (carried into the lock preregistration):** the δ bar was FIT on exposed
data (DEV-100 r4/r5 and DEV-500 NEW400) and is frozen as of this document. The DEV-1000
unexposed-500 read therefore validates the bar AND confirms the cell in a single touch —
legitimate only because the bar is frozen before the read and the fit is declared. The
lever is also close to exhausted at this tier: DEV-100's retain-override-loss class was 5
samples, the safe bar reaches 3, and the remaining two (δ 0.1282 and 0.0039) are
unreachable at any bar that preserves the zero-loss property.

## 4. What the lock read tests

Per `2026-08-24-dev1000-baseline-lock-preregistration.md`: paired BLEND(v2) − M0 over the
**500 samples unexposed at this tier** (DEV-1000 minus DEV-500), bootstrap N=10,000 seed
20260807, 90/95% CIs, McNemar; **lock condition = 90% CI lower bound ≥ +10 pp**. The
preregistration's arm definition is amended here only in that BLEND flies the v2 candidate
(hash-pinned at the flight row); the statistic, the population, the one-touch discipline,
and the lock condition are unchanged.
