# SLURP next stage: owner decisions of 2026-09-16

Status: OWNER DECISIONS RECORDED. This note grants no model contact; it fixes the bar, the
comparators and the first cell of the program so later verdicts cannot move them.

## The four decisions (owner, Fable 5.1 session of 2026-09-16)

| # | Question | Decision |
| --- | --- | --- |
| 1 | What is an acceptable large gain on SLURP? | Official pooled SLU-F1 >= 64 (weakest published trained pipeline, Google/SF-ID 64.02, floor rule of 2026-09-04) AND intent >= 78, replicated on the same roster. |
| 2 | Admit the pending four-row candidate-bound slot-view proof? | Not now. The prepared configuration (`configs/experiment/slurp-candidate-slot-view-rendering-proof4-v1.json`) stays on file; re-open only if context capacity blocks an admitted module. |
| 3 | The held TRAIN A direct score? | Released as the TRAIN A direct anchor: run SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1, read once, no re-score. |
| 4 | The zero-yield Reviewer/Planner loop? | Fly a Reviewer-off ablation first; if neutral under the null margins, remove the loop from the default plan and redirect its contacts to sampling and exemplar grounding. |

## Why the bar is where it is

The retained dual-store agent reaches SLU 48.53 / intent 77.96 on TRAIN A and about 50.3 on
DEV1000 (+14.6 over direct). Intent already clears the published floor (72.06) but SLU-F1 sits
about 14 points below the weakest published trained pipeline. The bar therefore asks for the
system to be at least as good as the weakest trained pipeline on the task's own metric, on
exposed development rosters, twice. It is not a test-split or paper claim.

## Fixed consequences

- Every Phase B cell is a one-factor module admission on TRAIN A 1,080 against the sealed anchor
  bytes (run SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1) or the sealed
  predecessor cell it names; guards use the SLURP own-null half-widths (intent 0.92, SLU micro
  1.18, scenario 0.83, action 0.98).
- The TRAIN A system-versus-direct claim uses the released direct anchor; DEV1000 keeps its
  sealed direct/agent replication pair as the fresh-roster confirmation.
- Fold B and the test split stay unread until the v2 base is locked.
- Program: `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md`.
- Coordination: `docs/superpowers/plans/experiment-handoff/OWNER-FABLE-TAKEOVER-2026-09-16.md`.

## Owner decisions of 2026-09-17 (after cell B0 and the Phase A audits)

| # | Question | Decision |
| --- | --- | --- |
| 6 | Cell B0 returned HARMFUL by the preregistered intent clause although the point estimate is nil; the imported DEV1000 margin (0.92 pp) is narrower than TRAIN A's CI95 half-width (1.175 pp). | A: re-decide module M0 under the TRAIN A own null. The replicate B0r (byte-identical to B0) supplies the margins as the CI95 half-widths of (B0r minus B0); NEUTRAL needs both passes non-inferior to the anchor at those margins; the first-pass verdict stays on record beside the re-decision. |
| 7 | Projection v3 (label rule R_action then legal-label v2; filler surface normalisation) gains +3.46 / +3.73 pp official SLU of which about three quarters is case alignment scored at zero by the symmetric scorer. | A: adopt v3 as the fixed post-processing of every official number from now on; every report shows the symmetric-normalised number beside it and states that about 2.5 pp of the 64-point bar is representation alignment, not capability. |
| 8 | GPU order and twin triggering for the registered cells. | B1 -> B2 -> B4b -> B4a -> B4c; a cell's twin flies only after its arm shows a positive CI95 against the base; one cell in flight. |
| 9 | B4a's fallback candidate pulls up to 16 slot cards (median +7 values). | B4c (intent store v2 alone) flies only if B4a admits, to separate the store revision from the fallback hypothesis. |
| 10 | Codex's untracked leftovers in the main checkout and its worktrees. | Remove after merging: the three untracked files move to an archive outside the repository with a receipt; worktrees whose commits are reachable from a branch are pruned with a tombstone receipt; flight worktrees stay until their flights finalize. |

Outcome of decision 6 (2026-09-17, after the B0r read): HARMFUL under the own null (intent clause fails on both passes; SLU clause fails once by 0.028 pp). The review loop is retained; B1, B2 and B4 re-register on the anchor as v2 packages. Record: `docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md`.

## Owner directive of 2026-09-17 (mid-flight, cell B4b)

| # | Directive (translated from the owner's Chinese message; the original is quoted in the coordinator's memory record) | Consequence |
| --- | --- | --- |
| 11 | Every agent node's input context must follow ONE unified handling policy. A model's raw output is never handed to the next node unprocessed. Per-node templates are provided, and where necessary one extra model call cleans the context, so the core performs better across tasks. | A Node Context Policy (NCP) is designed for the harness: one policy object per node boundary with levels L0 raw pass-through (the anchor, byte-identical), L1 template-built structured context (deterministic, zero contacts) and L2 = L1 plus one context-cleaning contact at declared boundaries (schema-validated, falls back to L1, metered like every contact). Audit of what each node receives today first (`docs/results/2026-09-17-slurp-node-context-audit-v1.md`), then the design (`docs/superpowers/specs/2026-09-17-node-context-policy-design.md`), then the engineering item and the admission cells B7a (L1 vs the sealed anchor) and B7b (L2 vs L1) on TRAIN A 1,080 under the program rule and the measured own null. E2c (the committed grouped-Solver answer as the reviewed draft, merged 59db0f9b) is the first instance of L1. Nothing in flight changes. |

