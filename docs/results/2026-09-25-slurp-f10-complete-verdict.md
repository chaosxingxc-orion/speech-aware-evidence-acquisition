# F10 empty-entity representation: complete paired verdict

Status: BENEFIT_NOT_PROVEN; NOT_QUALIFIED; CLOSED.

The complete 625-row treatment does not meet the prospectively registered
primary criterion. Do not change the default knowledge view, replicate this
variant for admission, adjust the margin, or rescue it through a selected
scenario. This closes the representation variant, not knowledge engineering or
training-free RL generally.

## Complete result and decision

| Metric | Fresh control | Empty-contract treatment | Treatment minus control |
| --- | ---: | ---: | ---: |
| Official pooled word/character SLU-F1, % | 59.5717 | 59.9083 | +0.3366 pp |
| Intent accuracy, % | 70.72 | 70.88 | +0.16 pp |
| Mean per-row SLU-F1, % | 44.9684 | 44.2910 | -0.6774 pp |
| Empty-gold exact-entity FP | 142 | 120 | -22 |
| Empty-gold rows with any FP | 108 | 105 | -3 |
| Nonempty-gold exact-entity FP | 325 | 319 | -6 |
| Nonempty-gold exact-entity FN | 384 | 397 | +13 |
| Unparsed delivered rows | 1 | 0 | -1 |

Primary natural-mixture SLU-F1 CI95: [-1.4185, +2.2853] pp. Its lower endpoint
does not exceed zero, so the quality criterion fails. The intent one-sided
95% lower bound is -1.12 pp, strictly above the registered -1.44 pp protection
margin; that guard passes. Passing protection cannot replace primary efficacy.

Equal-scenario SLU-F1 delta is +1.4275 pp, CI95 [-0.6905, +3.4153].
Equal-scenario intent delta is +0.3193 pp, CI95 [-1.2166, +1.9048].
All intervals use 10,000 paired utterance-cluster bootstrap draws, seed 20260915.
The natural result is primary; equal weighting is a required accompanying view.

Do not conflate corpus micro F1 with the mean of sample F1 values. The latter
has the known empty-target blind spot and moves in the opposite direction here.

## Attribution and tradeoff

OBS is unchanged: the original prepared speech packets, frozen model and
decoder-only four-slot service are shared. ORG changes the empty example's
trailing field from none to the literal fragment "entities":[]. SUPPLY changes
those selected contents while preserving the source pool, keys and retrieval
rules. USE is the full native Perception -> Solver -> Reviewer -> Planner
episode, including revisions and the existing delivery normalizer.

The actual first Solver request uses exactly 20 examples on all 625 rows in both
arms, with identical ordered example IDs on all 625 pairs. Each arm supplies
2,414 empty examples among those 12,500 first-visit selections (19.312%);
176/625 rows receive none. This is different from the released pool's
2,741/8,554 empty-example share. Selection equality on the first visit does not
require later model states or revision paths to remain identical.

The empty-target reduction is concentrated: QA contributes -21 of the net -22
exact FP. This is descriptive and cannot justify a post-hoc QA-only application.
Seven previously clean empty-target rows acquire a false positive, while ten
previously affected rows become clean. Nonempty omissions rise by thirteen.
This supports a specificity/omission tradeoff hypothesis, not a broadly reliable
correction rule. There are 193 normalized answer disagreements between arms.

## Per-scenario diagnostic

Deltas below use exact entity FP/FN for error counts and official pooled
word/character SLU-F1 for task quality. They are not additional admission tests.

| Scenario | Rows | SLU-F1 delta, pp | Intent delta, pp | Empty FP delta | Nonempty FP delta | Nonempty FN delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 26 | -8.8068 | 3.8462 | -1 | 4 | 3 |
| audio | 30 | 17.7086 | 3.3333 | -4 | -1 | -1 |
| calendar | 42 | 3.9166 | 0.0000 | 0 | -7 | -2 |
| cooking | 31 | 0.0000 | 0.0000 | 0 | 0 | 1 |
| datetime | 39 | -0.4833 | 0.0000 | 0 | 2 | 1 |
| email | 33 | -0.7845 | 6.0606 | 1 | 0 | 1 |
| general | 42 | 2.8027 | -4.7619 | 3 | 0 | 0 |
| iot | 33 | 1.9749 | 0.0000 | -1 | 1 | 0 |
| lists | 37 | -2.2343 | 0.0000 | -1 | 0 | 3 |
| music | 27 | 6.9848 | 3.7037 | -1 | 1 | 0 |
| news | 36 | -3.4851 | 5.5556 | 0 | 2 | 0 |
| play | 37 | -0.0893 | -8.1081 | 0 | -5 | 1 |
| qa | 38 | 15.7714 | 2.6316 | -21 | 0 | -2 |
| recommendation | 29 | -4.3750 | 0.0000 | 0 | -2 | 3 |
| social | 35 | 1.6627 | 0.0000 | 0 | -2 | -2 |
| takeaway | 37 | -4.2220 | -2.7027 | 0 | 3 | 6 |
| transport | 32 | 0.3919 | -6.2500 | 1 | -2 | 0 |
| weather | 41 | -1.0387 | 2.4390 | 2 | 0 | 1 |

## Runtime, source custody and costs

Both complete attempts are FINALIZED, each with exactly one official scoring job.
All 625 rows, including finite-completion and revision-limit outcomes, remain.

| Recorded generation quantity | Control | Treatment |
| --- | ---: | ---: |
| Model contacts | 2,585 | 2,552 |
| Prompt tokens | 21,715,276 | 21,430,801 |
| Completion tokens | 162,048 | 161,279 |
| Repeated speech seconds | 11,295.7366 | 11,148.6175 |
| Solver requests | 655 | 645 |
| Reviewer requests | 655 | 645 |
| Planner requests | 650 | 637 |
| Finite-completion rows | 5 | 8 |
| Revision-limit rows | 1 | 1 |

Each arm has 625 Perception requests and zero analytical tool calls. The smoke
adds 16 model contacts, for 5,153 contacts across this family; it is engineering
evidence only. Official scores were not rerun during analysis.

The control campaign ran 10:48:53-12:04:40 UTC (75m47s); treatment ran
12:05:11-13:15:34 UTC (70m23s). The chain confirmed both complete official jobs at
13:15:57 UTC. These are campaign wall times, not GPU utilization-integral hours
or summed request latency. Existing manifests do not separate every preparation,
sealing, scoring and idle category; do not fabricate that partition.

The service remained the same process/geometry, with --no-mmproj and 4 x 24,576
slots, output512. Control-before-treatment order remains a time/order limitation.
Source code stayed frozen at 54b6e151481129f4e1915c37f42a88ade687930b through
generation and scoring. Scores and outputs were byte-bound before outcome read.

The first derived comparison undercounted terminal dispositions because its
reader checked a legacy location instead of terminal_disposition.reason.
The shared reader was fixed and tested (18 tests passed). Preserve comparison.json
as superseded and use comparison-v2.json. All task metrics, intervals and source
bindings are byte-equivalent after removing only the corrected fallback fields.
No raw artifact was changed and no generation or official scoring was repeated.

## Artifacts and next action

Prospective specification and sealed bindings:
docs/readiness/2026-09-25-slurp-stage3-f10-v1/.
Receipt: docs/receipts/continuation/2026-09-25-f10-complete-verdict.json.
External comparison-v2.json and input-supplement.json:
analysis/SAEA-SLURP-STAGE3-F10-OFFICIAL-READ-V1/ under SPEECHRL_DATA_DIR.

Continue with a coordinated evidence/review/repair system using the incumbent
knowledge view. The existing native target-knowledge tool provides source-bound
semantic lookup with a declared distinction and real tool-call custody. That
path is preferable to the diagnosed raw-review lexical key construction. It
still needs its own matched complete-system registration and execution.
