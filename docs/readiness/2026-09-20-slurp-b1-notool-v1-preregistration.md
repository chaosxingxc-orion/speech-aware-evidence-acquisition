# Cell B1-notool preregistration: the Reviewer's task-contract tool withdrawn on the B1 base (repair form 0-B)

Registered 2026-09-20 by the coordinator (Fable 5.1), by script from the sealed cell B1r registration (owner decision 58),
before any contact. Development numbers only (owner decision 28).

## 1. Why this cell exists

Cell EFF-1 (`docs/results/2026-09-19-slurp-eff1-tool-constant-verdict.md`) measured that holding the native tools array
constant across the five roles halves GPU hours (prefilled tokens per row 26,197 -> 10,127; 3.388 -> 1.843 GPU-h per
1,080 rows) but, because the array was rendered to roles that cannot call it, 145 of 1,092 Solver completions came back
as tool-call strings and 137 rows scored zero (official SLU -4.39, intent -9.17). The only tools array in the system is
the Reviewer's `saea-tool-task-contract-v1`, whose observation is `context.task_contract` -- the contract every role
already holds verbatim in its system message. Owner decision 55 chose repair form 0-B: withdraw the tool, so that no role
renders a tools array, the prefix is constant by construction, and the failure class cannot occur; decision 56 chose the
B1 base first (option a), with the anchor-base and plan-base cells flown only if this cell's numbers differ from B1's by
more than 5 %.

## 2. The cell

| item | value |
| --- | --- |
| base | the flown B1 fragment (cell B1r's request bytes): module M1 at k = 20 on the sealed dual-store anchor |
| factor | `phase_tools` absent (the Reviewer's toolkit withdrawn); class `toolkits` |
| not factors | `native_episode.finite_completion_policy` (E13) and `native_episode.react_exhaustion_policy` (E22): failure-mode declarations that fire on no comparator row |
| unchanged | stores and supply, roster (TRAIN Fold A 1,080), geometry (np4 x 24,576), session, instruction template and fill, `tool_schema_rendering` absent, review loop, `roles.reviewer.max_iterations` 3 (the program ceiling binds it; a tool-free Reviewer answers on its first iteration), ceiling 11 |
| contacts per row | 4 (perception, solver, reviewer, planner); tool calls 0 |
| comparator | the sealed B1 arm `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2` (61.14 / 80.19), never re-flown |
| margins | B1's own null, cell B1r: h_SLU 1.2350 / h_intent 1.2212 (owner decision 38) |
| smoke | four engineering rows, structural acceptance (package README section 5) |
| runs | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-V1` / `-FIT-V1`; smoke `SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-SMOKE-4-V1` / `-FIT-V1` |

## 3. Decision rule (fixed here)

- **NEUTRAL** iff the CI95 lower bound of the paired official pooled SLU-F1 delta (arm minus B1) exceeds -1.2350 AND the
  CI95 lower bound of the paired intent delta exceeds -1.2212 (paired whole-speaker cluster bootstrap, 10,000 draws,
  seed 20260915). NEUTRAL admits the withdrawal into the SLURP default plan (it lowers cost) and makes this arm the base
  of the knowledge-index cell (decision 53).
- **ADMITTED** iff NEUTRAL and the pooled SLU lower bound is above zero.
- **HARMFUL** iff a guard fails with a measured loss (a point estimate below -h or a CI95 upper bound below zero; owner
  decision 25). Then 0-A (constant rendering kept, the tool-call token banned at decode time on the tool-free roles) is
  registered as the fallback and the owner decides again (decision 55).
- **Decision 56 clause**: if official SLU-F1 and intent each lie within 5 % (relative) of the sealed B1 values, the
  anchor-base and plan-base withdrawal cells are not flown.
- Diagnostics beside the rule: v3 and the TRAIN symmetric sibling, per-scenario tables (natural and equal weighting),
  the decision-17 net-harmed flag, revision counts, finite_completion / react_exhaustion dispositions, Solver completions
  tool-call-shaped as text (expected 0), rows the official scorer cannot parse.

## 4. Efficiency read (mandatory, reported whatever the verdict)

Prefilled tokens per row from the server.log join (per position, median and p90), cached share, packet re-decodes per
row, wall, slot occupancy, utilisation, parked fraction, GPU hours per 1,080 rows, contacts per minute from server.log
release records, projected 13,078-row read hours -- beside B1r (per-role: 3.851 GPU-h, 23.10 contacts/min) and EFF-1
(constant rendering: 10,127 prefilled tokens/row, 1.843 GPU-h, 45.94 contacts/min).

## 5. Budgets, failure rule, what is not claimed

Ceilings as cell B1r's (11,880 generation calls run-cumulative, 47,520 FIT endpoints, 33,930 repeated speech seconds,
12.0 GPU hours, native task-contract calls 0, one official complete score). First failure stops and preserves; one
root-diagnosed recovery re-registration at most. No claim about the anchor or the default plan under withdrawal (decision
56 decides), no test-split, Fold B or DEV-1000 claim, no claim that the withdrawal reaches the dev bar.
