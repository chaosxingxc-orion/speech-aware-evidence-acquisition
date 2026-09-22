# Cell R-PRIM: the Reviewer verdict as a closed set of primitives (item E37, owner decision 84) as one factor on the locked default plan: preregistration

Registered 2026-09-22 by the coordinator (Fable 5.1), by script from the sealed cell PLAN package (decision 58), before any contact. Development numbers only (owner decisions 28, 86).

## The cell

| item | value |
| --- | --- |
| base | the locked v2.0 plan, the sealed PLAN arm `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` (63.6304 / 82.2222) |
| factor | ONE factor: native_episode.reviewer_verdict = {vocabulary: saea-review-primitives-v1} together with the Reviewer instruction template probes/slurp_native_role_reviewer_primitives_v1.txt (the vocabulary once, the token on line 1, the rationale after, never parsed); the Planner keeps routing authority; illegal tokens are retained (disposition review_verdict_illegal), never raised. Everything else is the locked default plan byte for byte. Engineering number beside the verdict: the parse rate (>= 95 percent makes the primitive verdict the base's Reviewer form). |
| unchanged | roster (TRAIN Fold A 1,080), geometry (np4 x 24,576), session, stores, k = 20, no phase_tools, contact ceiling 11 |
| comparator | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`, never re-flown |
| margins | the plan's own null (PLANr): h_SLU 1.2485, h_intent 0.9943 |
| smoke | four engineering rows, structural acceptance |
| runs | `SAEA-SLURP-NATIVE-REVIEW-PRIMITIVES-V1` / `-FIT-V1`; smoke `SAEA-SLURP-NATIVE-REVIEW-PRIMITIVES-SMOKE-4-V1` / `-FIT-V1` |
| authority | owner decision 84 (2026-09-21) and 85 (pruning cells read on a measurable Reviewer); item E37 (docs/superpowers/specs/2026-09-22-slurp-reviewer-primitive-verdict-design.md, merged dc20819c); decisions 30/57/78 (the locked plan), 38 (own-null margins), 58 (script-derived registrations), 75 (frontier row), 77 (scheduled-task queue) |

## Decision rule (fixed here)

NEUTRAL: both guards non-inferior at the plan's own null (CI95 lower bound of the paired official pooled SLU-F1 delta > -h_SLU and of the intent delta > -h_intent). ADMITTED: NEUTRAL and the SLU CI95 lower bound above zero. HARMFUL: a measured loss on either guard (decision 25). Frontier row (decision 75) and per-scenario tables in both weightings on every verdict; cell-specific engineering numbers (e.g. a parse rate) are reported beside the verdict as the preregistration of the engineering item states.

## Budgets and failure rule

Ceilings as cell PLAN's (11,880 generation calls run-cumulative, 47,520 FIT endpoints, 33,930 repeated speech seconds, 12.0 GPU hours, one official complete score). First failure stops and preserves; one root-diagnosed recovery re-registration at most.
