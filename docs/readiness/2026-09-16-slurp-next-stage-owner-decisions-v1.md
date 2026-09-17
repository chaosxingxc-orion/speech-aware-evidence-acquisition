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
