# Handoff to ChatGPT — the Stage-3 entry point from the Fable 5.1 side

Last refreshed: 2026-09-26T14:30:00Z · maintainer: Fable 5.1 (root coordinator) · HEAD at writing
`1a82c9f8` on `master`, tree clean.

This is the standing counterpart to your `docs/handoff/HANDOFF-TO-FABLE51.md`: one short file,
refreshed **in place** after every landed result, no log section. Skeleton is fixed — state, what I
did, numbers, open items, embargoes, next action, housekeeping — so you can diff it. Freshness is
enforced by `scripts/checks/handoff_freshness_check.py`: if a newer file exists under `docs/results/`
than this stamp, the check fails and the staleness is my defect, not yours.

## 1. State

Stage 2's frozen four-node system is the asset: +27.3 pp SLU / +14.9 pp intent over the bare core on
the fresh DEV-2000-ADDED roster, replicated. **Stage 3 still has no learned update with an established
benefit**, and the owner's goal of 2026-09-26 sets the closure condition: build the academic baseline
and the optimisation space on the locked training-free RL families, name their shortcomings on these
tasks, improve the algorithm, lock on SLURP, then extend to Audio2Tool and E21 / E22 — Stage 3 closes
on a **stable gain validated on the test split**.

The dominant finding of my last working block is about the instrument, and it changes how every
number in this program must be read. It is written up in
`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md` and is binding from 2026-09-26.

## 2. What I did (2026-09-26, after the quota gap)

| work | artefact | state |
| --- | --- | --- |
| Landed your uncommitted per-group knowledge-proposal work unchanged so the tree is clean (a dirty tree refuses `core.flight.cli check`) | `15c13a00` — knowledge_edit_context per-group contexts, the group text baseline and probe, the system event view, 23 tests, design note, readiness receipt | merged |
| Stopped the stale Running scheduled task `SAEA-System-Batch001-Monitor` | — | no SAEA task is Running; no driver, no `flight.lock`, `batch-done` at 2026-09-26T12:14:46Z, GPU idle | done |
| Wrote the measurement instrument law | `1a82c9f8` — `docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md` | binding |
| In flight as I write: one decision registry (rows 115+), the five record debts (VAR-1 / VAR-2 / VERIFY-1 / F10 / evidence-path results-ledger entries and exposure closures), the two enforcement checks | branches `fable/decisions`, `fable/records`, `fable/checks` | merging today |

## 3. The numbers that matter (all from sealed arms; nothing re-run)

| measurement | value | why it matters |
| --- | --- | --- |
| A/A **within** one flight, n=200 | 91.5 % of delivered answers byte-identical, **0 / 200 intent flips**, h 0.735 SLU / 0.000 intent | inside a flight the plan is nearly deterministic |
| A/A **across** flights, n=625, request-identical (VAR1 PLAN vs PLANR, one chain) | **+1.87 pp SLU, CI95 [+0.41, +3.36]** — excludes zero — while **intent moves -1.28 pp** | a pure A/A contrast can be "significant"; the two metrics can move in opposite directions from flight variance alone |
| A/A across flights, Fold A n=1,080 / DEV n=1,000 | +0.17 (h 1.2485) / -0.25 (h 1.2525) | the offset is a random effect, not a constant |
| offline read over ONE sealed sample pool, n=625 | h **0.67** pp, zero GPU | the only precise instrument we have |
| entity support filter over sealed samples (s=3) | **+1.40 pp [+0.55, +2.29]** | clears its design's floor |
| self-selection over sealed samples (VERIFY-1) | SLU +0.70 [-0.26, +1.65]; **intent +0.544 [+0.032, +1.088]** | the only live-arm interval in Stage 3 that excludes zero |
| oracle best-of-5 over the same pool | **+6.55** (+12.55 on disagreeing rows) | the standing headroom of the selection line |
| bad-case headroom, Fold A / DEV | ENTITY-MIXED +17.4 / +16.5; INTENT-UNCOVERED +5.4 / +6.8 SLU and +12.0 / +16.9 intent | where any real gain must come from |

**Corrections the instrument law makes to the record** (please do not re-cite the old readings):
CELL-3's `-1.44` is *not distinguishable from flight variance* rather than HARMFUL (decision 111 still
stands, on the absence of benefit across four cells); CELL-1 / CELL-2 / CELL-1-GEPA were read without
an in-chain replicate and support no verdict either way; VAR-1 read its variants correctly **because
it flew PLANR** — EX-K10 / EX-K30 are +0.07 / +0.09 over PLANR, not +1.94 / +1.95 over PLAN.

## 4. The law, in four lines

1. If an action's effect can be computed over an already-sealed sample pool, read it there (0.67 pp,
   no GPU) — selection, commit, verification, projection, re-ranking of already-retrieved content.
2. Otherwise prefer per-row paired arms inside ONE campaign (`supply_variants`, item E42; needs owner
   re-authorisation because the family was closed, and needs `core/bundle/outputs.py` to learn
   `supply_variants` under invariant I7g before any number from it is reported).
3. Cross-flight only with an in-chain A/A replicate, and only for effects above ~3 pp at n=625 or
   ~2.5 pp at n=1,080.
4. Under ~200 rows is a form proof, never evidence of benefit. Terminal feedback on 4-16 trajectories
   cannot see anything this program is chasing — please size the next memory / knowledge batch
   accordingly, or make its acceptance test an offline read over sealed bytes.

## 5. Route ledger (carried over from my 2026-09-24 board, statuses current)

| route | what | status |
| --- | --- | --- |
| F0 bad-case bank | typed classes, headroom, gold-free signatures | DONE, `docs/results/2026-09-24-slurp-plan-bad-case-bank.md` |
| F1 offline aggregation | rules over ROLL-1's sealed 5 samples | DONE; support filter +1.40, medoid nil |
| F2 within-flight null | ROLL-AA | DONE; h 0.735 / 0.000 |
| F3 supply variants | VAR-1 six arms | DONE; no stable winner over PLANR |
| F7 / F11 selection | VERIFY-1 | DONE; benefit not proven, intent interval excludes zero |
| F10 empty-answer form | released view + arm | DONE; +0.34, closed |
| F12 per-row interleaving | mechanism merged; VAR-2 arm aborted twice | mechanism READY, family CLOSED — re-authorisation is an owner decision |
| F4 candidate proposal | INTENT-UNCOVERED, the largest intent headroom | OPEN — the biggest untouched lever |
| F5 per-intent legal slot-type constraint | type swap, illegal types | OPEN, offline count first |
| F8 verifier with evidence | give the Reviewer sample disagreement, support counts, checker verdicts | OPEN — my next line |
| F9 contract / instruction search | date-time FN, empty-gold FP | parked |

## 6. Open items and embargoes I am honouring

Yours, unchanged: revalidate live identity before acting, never treat historical PIDs as targets, no
progress-monitor subagents, one generating flight plus one scorer, ≤8 preparation workers during a
campaign; control625 quality unread; DEV6570 and test13078 closed; no second recovery on any closed
family; do not restart semantic-delta, VAR-2, F10 or evidence-path arms; power mode settled.
Mine, added: no cross-flight claim without an in-chain replicate; no benefit claim under 200 rows.

Open and needing an owner decision, not mine to take: re-authorising the `supply_variants` mechanism
(closed family, but it is the only sub-1 pp instrument for actions that need new contacts), and the
`core/bundle/outputs.py` I7g gap that must close before any interleaved number is reported.

## 7. My next action

Phase 1 of `D:\.claude\plans\…-rustling-hennessy.md`, all zero-contact: (a) the combined-commit
offline read — *model selects the answer* composed with the *deterministic support filter over its
entities*, plus per-field variants and checker pruning, over ROLL-1's sealed 625×5 samples and
VERIFY-1's sealed choices, at the 0.67 pp floor; (b) the academic-baseline report covering the four
locked families as implemented here, each with its faithful-implementation statement, measured effect,
cost and named failure mode (ACE is registered but never flown — I will either fly it once cheaply or
record it as not-run with the reason); (c) assemble SYS-1, one whole-system policy variant whose
predicted effect clears the cross-flight bar by construction, and register it with an in-chain
replicate. GPU stays free for your queued knowledge-proposal generations until SYS-1 is registered.

## 8. Housekeeping we share

WSL2 `Ubuntu-24.04`, `/home/chao/.venvs/speechrl/bin/python`, English documents, one generating flight
plus one scorer, merge finished work into master promptly, keep both entry points short and current.
When you land a result, my freshness check will fail until I refresh this file — that is the intended
signal, not a conflict.
