# SLURP complete-prefix candidate support: root diagnostic

Status: completed model-free construction read; no system-gain verdict or new
GPU flight. The active evidence-path control/tools results remain unread.
The analysis retains both full PLAN/PLANR 625 sources, their actual first
Perception states and the twenty exemplars actually supplied to the first Solver.

## Question and method

Determine whether a missing initial candidate is already represented among the
labels of the actual supplied exemplars. This distinguishes a candidate/supply
coordination opportunity from a deficit in this particular label pool. It does
not prove absence from all knowledge visible to the system or from the frozen
model's capabilities.

Use the shared normalized distinct-candidate parser. Preserve the original
candidates and append unseen exemplar labels by descending occurrence count,
breaking ties lexically. Caps of 5 and 8 were fixed in the read registration; no
reference answer influences selection. Frequency is not confidence and lexical
ties are not a semantic ranking. The complete union is a label-pool coverage
ceiling, not achievable model accuracy or an upper bound on the full system.

All actor prefixes, original state hashes, full trajectory identities, frozen
minus-R01 exemplar source and row order were checked before the offline label
join. The existing governed TRAIN loader supplied evaluation labels. Neither
the current active pair nor fresh DEV/test outcomes were read.

## Coverage and input width

| Projection | PLAN covered | PLAN coverage | PLAN mean width | PLANR covered | PLANR coverage | PLANR mean width |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Original normalized candidates | 486/625 | 77.76% | 2.6240 | 483/625 | 77.28% | 2.5984 |
| Preserve and append, at most 5 | 564/625 | 90.24% | 4.1808 | 561/625 | 89.76% | 4.1824 |
| Preserve and append, at most 8 | 582/625 | 93.12% | 5.0816 | 582/625 | 93.12% | 5.0848 |
| All labels in original candidates plus actual exemplars | 586/625 | 93.76% | 5.4720 | 586/625 | 93.76% | 5.4704 |

Exemplar labels alone cover 565/625 (90.40%) in each repeat. Their union with
the initial candidates covers 586, so replacing the original candidates with
exemplar labels would discard useful coverage. Preserve the original set.

The cap of 8 adds 96/99 covered inputs relative to PLAN/PLANR's original candidates.
Expanding from the cap of 8 to the entire pool adds only four more inputs per repeat,
while the maximum width rises from 8 to 15. This is evidence of diminishing
coverage opportunity within this pool, not evidence about actual model response
to larger inputs.

At least 594/625 inputs must be covered to reach 95%. The cap of 8 remains twelve short;
the full union remains eight short. Neither meets the owner's95% target.
Each union misses 39 rows, of which 38 are shared between repeats. Identical
aggregate coverage does not mean identical covered sets.

| Weighting | Arm | Original | Cap5 | Cap8 | Full union |
| --- | --- | ---: | ---: | ---: | ---: |
| Equal weight over all 18 scenarios | PLAN | 78.78% | 90.29% | 93.17% | 93.83% |
| Equal weight over all 18 scenarios | PLANR | 78.35% | 89.94% | 93.20% | 93.84% |


## Relation to final system errors

These are descriptive partitions of the existing final intent errors, not
causal assignments or estimates of how many errors an intervention will fix.

| Final-intent error category | PLAN | PLANR |
| --- | ---: | ---: |
| Correct label already in original candidates, final intent wrong | 53 | 55 |
| Correct label absent from candidates but present in actual exemplars, final intent wrong | 92 | 98 |
| Correct label absent from both this candidate set and exemplar-label pool, final intent wrong | 39 | 39 |
| All final-intent errors | 184 | 192 |

Roughly half of final-intent errors are in the second category. This motivates
testing better coordination between candidate proposals, explanatory knowledge,
Solver selection and independent review. It does not prove that merely appending
labels will correct them. The first category also needs discriminating judgment;
larger N alone is not its solution. Slot errors and official pooled SLU-F1 remain
essential terminal endpoints for every later system experiment.

## Initial candidates are an instruction, not an observed hard ceiling

The source-bound join found 8 PLAN and 5 PLANR correct delivered intents outside
the original normalized candidate set. Both the new projection and the earlier
attribution agree on these rows and their full trajectory hashes. There is no
recorded fallback in these cases.

In PLAN, five were already intent-correct in the first Solver answer; three
became correct after a REVISE/ACCEPT path. In PLANR, all five were already correct
at the first Solver visit. The solver role text instructs selection from the
original candidates, but these retained outcomes show that candidate membership
was not an end-to-end hard constraint in these runs.

Do not rewrite these official results, drop the rows, or retrospectively impose
a strict candidate filter. Also do not claim that initial candidate coverage
mathematically caps actual system accuracy. A new comparison must preserve
delivery behavior across arms and separately report candidate membership.
This is a post-hoc cross-node follow-up, preserved as a separate pinned
derivative, not a change to the original registered support read.

## State heterogeneity

| Arm | Existing agreement state | n | Original coverage | Cap8 coverage | Full union coverage | Original misses supported by examples but final intent wrong |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| PLAN | agree-lt-0.25 | 210 | 50.95% | 86.67% | 88.57% | 71 |
| PLAN | agree-0.25-0.50 | 107 | 87.85% | 98.13% | 98.13% | 11 |
| PLAN | agree-0.50-0.75 | 99 | 87.88% | 96.97% | 96.97% | 9 |
| PLAN | agree-ge-0.75 | 209 | 94.74% | 95.22% | 95.22% | 1 |
| PLANR | agree-lt-0.25 | 209 | 50.24% | 87.08% | 88.52% | 75 |
| PLANR | agree-0.25-0.50 | 108 | 87.96% | 97.22% | 98.15% | 11 |
| PLANR | agree-0.50-0.75 | 100 | 86.00% | 97.00% | 97.00% | 11 |
| PLANR | agree-ge-0.75 | 208 | 94.71% | 95.19% | 95.19% | 1 |

The low-agreement state has most of this support gap, while the highest-agreement
state gains only one covered input from the union. This is a candidate state
feature for future logged exploration. It is not a learned trigger or permission
to select a favorable subgroup. High agreement still contains ten union misses
in each repeat; agreement is not proof of correctness.

## Root next-system decision

After the active complete-system pair is sealed and interpreted, prioritize a
bounded candidate-recovery system action for the next design review:

- Preserve the initial candidate identities and provenance. Never rewrite the
  Perception response to pretend the model generated additional candidates.
  Bind a separate derived proposal to that response and its exemplar sources.
  Make any supported additions explicit rather than expecting roles to infer an escape from an
  instruction to stay within the original list.
- Supply the added candidates' distinguishing intent information and explanatory
  slot contracts through the existing knowledge interfaces. A larger bare label
  list is not the intended action.
- Give Reviewer the proposal provenance, competing distinctions and current
  answer support; preserve Planner routing and Solver answer authority through
  final delivery. Test the whole continuation, including new harms.
- Keep a matched complete fixed-system comparator and all 625 inputs. Inspect
  actual request capacity and register exact contact ceilings before launch.
  Do not add a hidden stricter delivery filter in only one arm.
- Use complete terminal feedback for later policy sampling and updates. This
  diagnostic does not admit an RL policy, select an action from gold, set a new
  reward, or establish stable benefit.
- Investigate the remaining missing-label inputs before choosing another
  evidence source. Do not infer that Whisper or a wider knowledge search will
  necessarily resolve them. Closed lines remain closed.

The original plan's F4 direction is therefore supported as a system hypothesis,
not declared effective. The active tools family is not interrupted or changed.
The 95% target remains open, alongside full-system quality improvement.

## Complete scenario tables

All cells are percentages; n is the identical frozen roster size in each arm.

### PLAN

| Scenario | n | Original | Cap5 | Cap8 | Full union |
| --- | ---: | ---: | ---: | ---: | ---: |
| alarm | 26 | 96.15% | 96.15% | 96.15% | 96.15% |
| audio | 30 | 93.33% | 96.67% | 100.00% | 100.00% |
| calendar | 42 | 61.90% | 97.62% | 97.62% | 97.62% |
| cooking | 31 | 77.42% | 80.65% | 83.87% | 83.87% |
| datetime | 39 | 94.87% | 97.44% | 97.44% | 97.44% |
| email | 33 | 84.85% | 93.94% | 96.97% | 96.97% |
| general | 42 | 21.43% | 66.67% | 78.57% | 78.57% |
| iot | 33 | 78.79% | 87.88% | 90.91% | 90.91% |
| lists | 37 | 86.49% | 89.19% | 94.59% | 94.59% |
| music | 27 | 66.67% | 74.07% | 85.19% | 85.19% |
| news | 36 | 83.33% | 94.44% | 97.22% | 97.22% |
| play | 37 | 75.68% | 94.59% | 94.59% | 94.59% |
| qa | 38 | 60.53% | 81.58% | 84.21% | 86.84% |
| recommendation | 29 | 89.66% | 93.10% | 93.10% | 96.55% |
| social | 35 | 77.14% | 94.29% | 94.29% | 100.00% |
| takeaway | 37 | 86.49% | 97.30% | 97.30% | 97.30% |
| transport | 32 | 90.62% | 96.88% | 100.00% | 100.00% |
| weather | 41 | 92.68% | 92.68% | 95.12% | 95.12% |

### PLANR

| Scenario | n | Original | Cap5 | Cap8 | Full union |
| --- | ---: | ---: | ---: | ---: | ---: |
| alarm | 26 | 92.31% | 96.15% | 96.15% | 96.15% |
| audio | 30 | 96.67% | 100.00% | 100.00% | 100.00% |
| calendar | 42 | 61.90% | 95.24% | 97.62% | 97.62% |
| cooking | 31 | 80.65% | 80.65% | 83.87% | 83.87% |
| datetime | 39 | 94.87% | 97.44% | 97.44% | 97.44% |
| email | 33 | 84.85% | 93.94% | 96.97% | 96.97% |
| general | 42 | 16.67% | 59.52% | 76.19% | 76.19% |
| iot | 33 | 78.79% | 87.88% | 90.91% | 90.91% |
| lists | 37 | 83.78% | 86.49% | 94.59% | 94.59% |
| music | 27 | 70.37% | 74.07% | 85.19% | 85.19% |
| news | 36 | 80.56% | 94.44% | 97.22% | 97.22% |
| play | 37 | 78.38% | 94.59% | 94.59% | 94.59% |
| qa | 38 | 63.16% | 84.21% | 89.47% | 89.47% |
| recommendation | 29 | 86.21% | 93.10% | 93.10% | 96.55% |
| social | 35 | 68.57% | 94.29% | 94.29% | 100.00% |
| takeaway | 37 | 89.19% | 97.30% | 97.30% | 97.30% |
| transport | 32 | 90.62% | 96.88% | 100.00% | 100.00% |
| weather | 41 | 92.68% | 92.68% | 92.68% | 95.12% |

## Reproduction, validation and cost

Recipe: docs/readiness/2026-09-25-slurp-candidate-support-read-v1.json.
Entry: scripts/analysis/slurp_candidate_support_read.py with the registered
recipe, data root and the umbrella lock. The read took 727.24 seconds, chiefly
the existing governed TRAIN filesystem validation, with no new model,
tokenizer, ASR, encoder, server, scorer or network contact.

Four focused projection tests and all nine offline gates passed. The first
native-reuse check invocation omitted its required output argument; the corrected
invocation passed and both logs are retained. Existing runtime/source-reader code
for the detached evidence-path analysis was not changed. New independent analysis
files reuse its source formats and shared helpers.

Derived artifacts remain under
SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-CANDIDATE-SUPPORT-READ-V1.
The completion receipt pins both derivatives, repository sources and checks:
docs/receipts/continuation/2026-09-25-slurp-candidate-support-read.json.
