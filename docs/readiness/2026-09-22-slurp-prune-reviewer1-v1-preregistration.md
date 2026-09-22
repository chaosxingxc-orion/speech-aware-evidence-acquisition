# Cell P1: Reviewer 3 -> 1 on the measurable-Reviewer base (cell R-PRIM), the first decision-85 pruning cell: preregistration

Registered 2026-09-22 by the coordinator (Fable 5.1), by script from the sealed cell PLAN package (decision 58), before any contact. Development numbers only (owner decisions 28, 86).

## The cell

| item | value |
| --- | --- |
| base | the locked v2.0 plan, the sealed PLAN arm `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` (63.6304 / 82.2222) |
| factor | native_episode.roles.reviewer.max_iterations 3 -> 1 on the cell R-PRIM fragment (the locked plan plus the primitive verdict, decision 97); everything else byte-identical |
| unchanged | roster (TRAIN Fold A 1,080), geometry (np4 x 24,576), session, stores, k = 20, no phase_tools, contact ceiling 11 |
| comparator | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`, never re-flown |
| margins | the plan's own null (PLANr): h_SLU 1.2485, h_intent 0.9943 |
| smoke | four engineering rows, structural acceptance |
| runs | `SAEA-SLURP-NATIVE-PRUNE-REVIEWER1-V1` / `-FIT-V1`; smoke `SAEA-SLURP-NATIVE-PRUNE-REVIEWER1-SMOKE-4-V1` / `-FIT-V1` |
| authority | owner decisions 85 and 97; base cell R-PRIM (read 2026-09-22: SLU +0.58 non-inferior, intent -0.09 within width, not HARMFUL) |

## Decision rule (fixed here)

NEUTRAL: both guards non-inferior at the plan's own null (CI95 lower bound of the paired official pooled SLU-F1 delta > -h_SLU and of the intent delta > -h_intent). ADMITTED: NEUTRAL and the SLU CI95 lower bound above zero. HARMFUL: a measured loss on either guard (decision 25). Frontier row (decision 75) and per-scenario tables in both weightings on every verdict; cell-specific engineering numbers (e.g. a parse rate) are reported beside the verdict as the preregistration of the engineering item states.

## Budgets and failure rule

Ceilings as cell PLAN's (11,880 generation calls run-cumulative, 47,520 FIT endpoints, 33,930 repeated speech seconds, 12.0 GPU hours, one official complete score). First failure stops and preserves; one root-diagnosed recovery re-registration at most.
