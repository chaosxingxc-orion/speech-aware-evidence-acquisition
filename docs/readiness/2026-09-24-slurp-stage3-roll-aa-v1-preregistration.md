# Cell ROLL-AA: the Stage-3 within-flight A/A null: preregistration

Registered 2026-09-24 by the ROLL-AA registration agent (worktree
`/home/chao/saea-worktrees/fable-aanull`, branch `fable/aanull`), before any contact, from the
sealed cell ROLL-1 fragments plus the E2b greedy-repeat twin form. Development numbers only
(owner decisions 28, 86). **READINESS HELD on both cells**: this registration authorises no
flight, no readiness flip and no contact (section 7).

Authority: board route **F2** of `docs/handoff/2026-09-24-fable51/HANDOFF-STAGE3-FOR-CHATGPT-v1.md section 7.3`
(owner directive 2026-09-24 -- analyse and validate the fast routes first). Substrate: cell ROLL-1
(`docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md` section S3-2) and item
E2b of `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` section 4 ("N greedy
repeats aggregated identically"). Stage-3 algorithm label (owner decision 101): `shared-rollout`,
operator `rollout`.

## 1. Why this cell exists

Every Stage-3 result so far has been read against a **cross-flight** margin: cell PLAN against
cell PLANr on TRAIN Fold A (h_SLU 1.2485, h_intent 0.9943, n = 1,080) and its DEV-2000-ADDED
sibling (h_SLU 1.2525, h_intent 1.1520, n = 2,000). The ROLL-2 variant rollouts (board route F3)
want to compare K construction variants **per row, inside one flight**, at n = 200. Nothing in the
program says what the paired noise floor of that design is. Reading a 200-row within-flight paired
contrast against a 1,080-row cross-flight half-width is not a defensible substitute: the design,
the population and the n all differ.

ROLL-AA measures the missing number directly. It is the **A/A null of the methodology**: the same
grouped-Solver substrate ROLL-2 will use, with the variant axis set to *nothing* -- the identical
prompt, twice, greedy.

## 2. The cell

| item | value |
| --- | --- |
| base | cell ROLL-1, `configs/baseline/slurp-native-stage3-rollout-baseline-v1.json` (itself the locked v2.0 plan plus the grouped-Solver factor) |
| factor | `roles.solver.samples` 5 -> 2; `decoding_overrides.temperature` 0.7 -> 0.0; `roles.solver.twin` absent -> `"greedy-repeat"`; `commit.min_support` 3 -> 2; `seed_offset` stays 0; policy `...-samples5-v1` (19) -> `...-samples2-v1` (13) |
| not factors | `knowledge_stores`, `phase_material`, the task instruction template, the geometry (np4 x 24,576), `scorers`, `evidence_source`, the arm, the filled S3-1 preparation pins -- byte-identical to ROLL-1 (`tests/unit/test_stage3_roll_aa_baseline_cell.py`) |
| roster | `SLURP-STAGE3-ROLL-AA-R01C-200-V1`, 200 rows, `docs/receipts/rosters/slurp-stage3-roll-aa-r01c-200-v1.json` |
| nodes that run | **all four**: Perception 1, Solver 1 visit x 2 samples, Reviewer 3, Planner 1, `max_revisions` 1, `review_loop` on -- the locked plan's whole graph, unchanged. Only the Solver visit is grouped. |
| contacts per row | ceiling 13; about 5.2 expected |
| comparator | **none** -- an A/A null is its own control |
| smoke | the first four rows of the same roster, structural acceptance |
| runs | `SAEA-SLURP-STAGE3-ROLL-AA-V1` / `-FIT-V1`; smoke `-SMOKE-4-V1` / `-SMOKE-4-FIT-V1`; read `-READ-V1` |

## 3. Why the two samples are a null

`reproduction.ojw.native_group_solver.run_grouped_solver_samples` composes N independent Solver
invocations of **one visit**, each through the same metered request path, and
`reproduction.ojw.native_request.compose_solver_sample_decoding_params` overrides exactly two
request fields per sample:

* `temperature` -- **0.0 for both samples**;
* `seed` -- `fragment_seed + seed_offset + sample_index`.

Measured offline at registration, with the real fragment seed
(`rails.runner._solver_fragment_seed("phase-native-candidates-review-revise-samples2-v1")` =
2080141211):

| sample | composed request decoding params |
| --- | --- |
| 0 | `{id_slot: per-sample, max_tokens: 512, seed: 2080141211, temperature: 0.0}` |
| 1 | `{id_slot: per-sample, max_tokens: 512, seed: 2080141212, temperature: 0.0}` |

**The only field that differs is `seed`,** and at temperature 0 llama.cpp decodes greedily and does
not consult it. The grouped sampler *forces* the two seeds apart -- `sample_index` is added
unconditionally and there is no configuration that makes them equal -- which is exactly why
`rails.native_episode_config` gates temperature 0 behind the explicit `twin: "greedy-repeat"`
marker and calls those seeds *"recorded custody, never a source of diversity at temperature 0."*
So: the sampler did **not** refuse temperature 0, and it **does** force distinct seed values; both
facts are registered here, and neither breaks the null.

Everything else about the two contacts is one object: same messages, same speech packet, same
supplied knowledge, same response format, same node, same row, same flight, same resident serving
session. The residual difference is llama.cpp **batch-composition nondeterminism** -- the program's
own standing finding that greedy decoding is not bitwise reproducible across batch shapes.

## 4. Decision rule (fixed here)

**DESCRIPTIVE. Nothing is admitted, rejected or locked by this cell.**

The read produces, on the 200 rows:

1. per row, both samples' official SLU-F1 and intent (`scenario_action_exact`), scored on copies
   exactly as `scripts/analysis/stage3_rollout_score.py` scores ROLL-1's;
2. the paired per-row delta `sample1 - sample0` for each metric;
3. its distribution: mean, sd, and the **CI95 half-width of the pooled micro delta by paired row
   bootstrap, 10,000 draws, seed 20260915** -- this half-width is `h_within` (SLU-F1) and
   `h_within_intent`;
4. the **byte-identical-output share**, the **intent-flip share** and the **entity-set-flip
   share**, each with its denominator;
5. the per-stratum table and the realised cost (contacts per row, GPU hours, revision share).

`h_within` and `h_within_intent` become **registered within-flight margins**: every ROLL-2 variant
comparison at n = 200 is read against them. They are reported *beside* the cross-flight
PLAN-vs-PLANr half-widths (Fold A 1.2485 / 0.9943; DEV-2000-ADDED 1.2525 / 1.1520) as context, not
as a comparator and not as a gate.

Structural acceptance for the flight (not a result): a clean seal, 200 in / 200 out, exactly two
custodied samples per row in `solver_group` (invariant I7g) with seeds 2080141211 / 2080141212 and
temperature 0.0 on both, the plurality-commit replay reproducing the sealed delivered answer, zero
native task-contract calls, every request fitting.

**A large `h_within` is a result, not a failure.** If the within-flight paired floor is not
materially smaller than the cross-flight one, then paired within-flight rollouts buy no precision
over separate flights and ROLL-2 must be read at n well above 200. That conclusion is exactly as
useful as the opposite one and is reported the same way.

## 5. What this null does NOT measure (registered limitations)

1. **The roster is not scenario-stratified.** The selection rule was specified as *the first 200
   rows of R01C in roster order*, and R01C's order is ascending `sample_id`. SLURP's utterance ids
   cluster by scenario, so the prefix covers **9 of the parent's 18 scenario strata** -- `alarm` 17,
   `audio` 23, `datetime` 24, `iot` 23, `music` 21, `news` 30, `play` 13, `takeaway` 28,
   `weather` 21 -- and misses `calendar`, `cooking`, `email`, `general`, `lists`, `qa`,
   `recommendation`, `social` and `transport` entirely. Per-row variance is scenario-dependent, so
   `h_within` measured here is a half-width **for this nine-scenario mixture**, and it transfers to
   a ROLL-2 run on a different 200 only to the extent the mixtures agree. **Decision NOT taken by
   this registration**: drawing a scenario-stratified 200 (for example the first 11 of each of the
   18 strata) instead. Both cells are `held`, so root can re-register the roster before the flip at
   no cost; if the intent is a general n = 200 floor rather than a floor for this prefix, that is
   the change to make.
2. **It is not a PLAN-identity null.** The grouped path overrides the request seed
   (2080141211/2080141212) away from the plan's own `decoding_params.seed` (20260913), so a ROLL-AA
   sample is not byte-comparable to a cell-PLAN decode of the same row. ROLL-AA is an A/A null of
   *itself*, not of PLAN.
3. **It is not a same-batch guarantee.** The two samples of a visit are two contacts submitted
   through the same request path but not pinned to one server batch; that is precisely the noise
   being measured, and it is also the noise ROLL-2 will carry.
4. **n, geometry, sample count and session are all part of the number.** `h_within` is valid at
   n = 200, at samples 2, on the np4 x 24,576 SLURP geometry, on the resident session
   `serving-slurp-native-candidate-five-train-a-np4-v1`. No transfer is claimed.
5. **The commit is not the measured quantity.** `min_support` 2 makes the delivered answer the
   intersection of the two samples' entities on a disagreeing row. `min_support` 1 (the union) was
   considered and rejected: it would add false positives neither greedy pass delivered. The read
   scores the two **raw** samples, and the commit's divergence from both is reported as a count so
   the choice stays visible.
6. **The form has never flown.** The E2b `greedy-repeat` marker has registered precedent -- cell
   B2's twin `SAEA-SLURP-NATIVE-SAMPLES5-GREEDY-TWIN-TRAIN-FOLD-A-V1`, registered 2026-09-17 -- but
   that twin never flew (owner decisions 8/15 launch a twin only after a positive arm, and B2's arm
   CI95 lower bound was -1.4598). ROLL-AA would be the **first flight of a temperature-0 Solver
   group**. The four-row smoke is its form proof and the offline dry run
   (`docs/readiness/2026-09-24-slurp-stage3-roll-aa-v1/dry-run-v1.md`) is its zero-contact
   pre-proof.

## 6. Budgets and failure rule

| quantity | arm | smoke |
| --- | --- | --- |
| `planned_model_calls` | 2,600 = 200 x 13 | 52 = 4 x 13 |
| `fit_endpoint_calls_cap` | 10,400 = 2,600 x 4 | 208 = 52 x 4 |
| `planned_speech_audio_seconds` | 10,235 = `ceil(787.2898125 x 13)` | 222 = `ceil(17.0349375 x 13)` |
| `planned_gpu_hours` | 2.0 | 1.0 |
| `native_task_contract_calls_cap` | 0 (tool-free) | 0 (tool-free) |
| `official_complete_scoring_jobs` | 1 (at finalize, so the manifest seals in the standard shape) | 0 |

13 = `1 + (max_revisions + 1) * (solver.max_iterations * solver.samples + reviewer.max_iterations +
planner.max_iterations) = 1 + 2 * (2 + 3 + 1)`, as
`rails.native_episode_config.load_native_episode_config` resolves it and as the committed program
`phase-native-candidates-review-revise-samples2-v1` declares. Expected spend: about 5.2 contacts per
row (about 1,040 contacts, about 0.4 GPU hours), so the registered ceiling is about 2.5x the
expectation. Ceilings are bounds, never targets, and budgets are run-cumulative across every attempt
of a run id.

First failure stops and preserves. No automatic restart, replay, row filtering, roster, role-graph,
prompt, knowledge, geometry or cap change. At most one root-diagnosed recovery re-registration; a
second failure stops the flight and the fix is proven on a 4-row dry run (owner rules 2026-09-03).

## 7. What this registration does NOT authorise

`readiness.state` is `"held"` on both cells and `requirements` is deliberately empty:
`core.flight.repin._set_preparation_requirement` creates the preparation requirement on the first
successful preparation and `_upsert_decision_requirement` inserts the decision requirement at the
flip, while a placeholder decision entry without an `expected_decision_id` would be left behind
beside the real one and refuse the campaign at load. No decision id is minted, no
`scripts/flights/repin_cell.py --set-ready` has run, `core.flight.cli check` was deliberately not
run (a GPU flight was in progress; the coordinator's own clean-tree re-pin cycle runs it and
asserts the runtime-derived hashes agree with the registered ones), and neither cell is on the
batch queue. No contact of any kind was made by this registration.

## 8. Claim boundary

No superiority, generalisation, component-causal, bar, held-out, confirmatory or paper-scale claim
of any kind. The construction roster is exposed development data (owner decisions 28, 86). A null
measures noise, not effect; a zero paired delta would not mean determinism, and a non-zero one
would not mean a defect.
