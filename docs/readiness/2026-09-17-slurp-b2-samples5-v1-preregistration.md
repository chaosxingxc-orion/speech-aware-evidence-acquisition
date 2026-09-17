# Cell B2: sample-and-aggregate commit, preregistration

Status: **PREREGISTERED BEFORE CONTACT.** Author: the B2 preparation agent, worktree
`/home/chao/saea-worktrees/fable-b2-prep`, branch `fable/b2-prep`, base commit `6c5c9ab7`.
Authority: `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` section 4 (Phase B,
cell B2, module M2) and its engineering items E2 and E2b, under owner decision 4 of
`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`. This document grants no model
contact; all three cells stay readiness `held` until the coordinator adds the decision requirement
and flips them.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and
server contacts**. The resident service was never started, stopped or queried, and cell B0 — in
flight from a worktree pinned at `5d0d694d` while this package was prepared — was never touched.

## 1. Question

Do five sampled Solver answers, aggregated by the deterministic plurality/support commit policy,
improve official pooled SLU-F1 over the single greedy Solver of the cell B0 review-off base on
TRAIN Fold A 1,080?

The diagnosis this answers is in the spec's section 2: byte-identical greedy prompts already flip
28 % of outputs and 5 % of intents, so sampling plus deterministic aggregation has headroom; and
entity false positives (28.8 %, with 184 of 414 empty-gold rows emitting entities) are exactly what
a support filter over independent samples can suppress. The review loop's 60 % of the anchor's
contacts is the budget being re-spent here.

## 2. Arms

| role | identity |
| --- | --- |
| arm | `SAEA-SLURP-NATIVE-SAMPLES5-TRAIN-FOLD-A-V1` / `attempt-slurp-native-samples5-train-fold-a-generation-v1`, cell `slurp-native-samples5-train-fold-a-v1`, composed config `5261d4c4a572cefe65cc2162c48be673f695e0e2f288b34e9ce8b753b5cf7111`, protocol `8b28f552ffb55f2be0deecf290b3e5aab5f287f9b911573bccac0a1d610972b1` |
| twin | `SAEA-SLURP-NATIVE-SAMPLES5-GREEDY-TWIN-TRAIN-FOLD-A-V1` / `attempt-slurp-native-samples5-greedy-twin-train-fold-a-generation-v1`, cell `slurp-native-samples5-greedy-twin-train-fold-a-v1`, composed config `9abb4936406a59a4a59ef1292b9fb1e316f1dfdc8c9888cbd586004fd963acf1`, protocol `e9f8a31e30e75307bf55b23634be27c3e3474699c4d7a9d506105178bfbf70f9` |
| primary comparator | sealed bytes of cell B0, `SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-V1` / `attempt-slurp-native-review-off-train-fold-a-generation-v1`; score artifact SHA-256 and run manifest SHA-256 are `PENDING_B0_FINALIZE` and are filled in by the coordinator after B0 finalizes |
| secondary comparator | sealed bytes of `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` / `attempt-slurp-native-dual-store-train-fold-a-anchor-generation-recovery-v1`, score artifact SHA-256 `7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47`, run manifest `049ac230e536bc6c8fe45bc847756ba486c4904e9c7602c698157f78d70c0152` (pooled SLU-F1 48.53, intent 77.96, scenario 84.81, action 79.26, pooled span F1 29.50) |

Neither comparator is ever re-flown or re-scored. The **twin is flown**, because it is not a sealed
comparator but the arm's own token-matched control: identical six contacts per row, identical commit
policy, identical five pinned seeds, temperature 0 instead of 0.7. It is the only re-flown arm this
cell admits.

All arms share the roster `docs/receipts/rosters/slurp-evo-fold-a-v2.json`
(SHA-256 `1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d`), split
`SLURP-EVO-FOLD-A-V2`, split identity
`61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role `discovery`, and the
resident session `serving-slurp-native-candidate-five-train-a-np4-v1` (attach only, never spawn).

## 3. The one factor, and what it is not

Moved, all inside `native_episode.roles.solver` — the `episode`-class switch key
`native_episode.roles.solver` whose OFF arm is the historical Solver role
(`rails.config_tables.is_episode_null_arm`):

- `samples` absent (1) to **5**;
- `decoding_overrides` absent to **{temperature 0.7, seed_offset 0}** (twin: temperature 0 with the
  explicit `twin: "greedy-repeat"` marker, the one documented exception
  `rails.native_episode_config.NativeEpisodeRole` admits for temperature 0);
- `commit` absent to **{policy `saea-commit-plurality-support-v1`, min_support 3,
  similarity_threshold 0.8}**;
- `policy` `phase-native-candidates-solve-v1` to `phase-native-candidates-solve-samples5-v1` — the
  same four declared phases, `max_contacts` 2 to 6. The ceiling
  `1 + 1*(0 + 0 + 1*5) = 6` is the exact program maximum, not a safety bound;
- `native_contact_fit` resized to `1080 * 6 * (1 + 3) = 25920` endpoints, with its own run and
  attempt id per arm;
- the speech-feature key and matcher identity strings renamed onto each arm (provenance, never
  model-visible);
- `prepared_phase_supply` re-prepared model-free for each cell's own composed config.

Held identical: the roster and split, the model fragment and resident geometry, the promoted speech
packets, both knowledge stores with their release and snapshot hashes, the candidate supply
contract, every instruction template, the review-off role graph (reviewer and planner
`max_iterations 0`, `max_revisions 0`, `review_loop "off"`), the inert `phase_tools` block, and the
scorers.

Three request-level differences exist and all three are the module's own channel:

1. **Rendered envelope, proven row for row.** On all 1,080 rows and all four declared phases the
   rendered request differs from cell B0's by exactly one substitution, the phase-program id inside
   the `[agent control <program>:<phase>:<sample>]` marker
   (`phase-native-candidates-solve-v1` to `phase-native-candidates-solve-samples5-v1`, 9 bytes).
   Applying that substitution to cell B0's envelope reproduces cell B2's byte for byte on 1080/1080
   rows for every phase, for the arm and for the twin alike; 0 rows differ in any other way. The
   system message (SHA-256 `485f8f2033e1f133001da62cbc016b5eb0a2c20b6c7cdbe0885a083732e255eb`), the
   speech-feature part, the knowledge blocks and the entire instruction body are byte-identical.
   Receipt: `SPEECHRL_DATA_DIR/coordination/slurp-b2-samples5-v1/request-envelope-comparison-v1.json`,
   rendered through the production `core.flight.runtime.render_phase_prompt_envelopes`.
2. **The episode-limits epilogue at dispatch.** The episode runner appends a `Native episode limits`
   block to the Solver's per-turn instruction whose `remaining_model_contacts` reads 5 instead of 1
   (`max_contacts` 6 minus the one Perception contact already scheduled, against 2 minus 1).
   `max_revisions` stays 0 and `available_planner_actions` stays `[ACCEPT]`, as in cell B0. That
   block is built **once per Solver visit**, so all five samples of one row receive the
   byte-identical instruction.
3. **Decoding parameters.** The five sibling Solver requests of one visit are byte-identical to each
   other except `seed`: `fragment_seed + seed_offset + sample_index` with `fragment_seed = 1597380463`
   (`rails.runner._solver_fragment_seed` over the composed program id), so
   `1597380463 … 1597380467`, the same five seeds in the arm and in the twin. Against cell B0's
   single Solver request they differ in exactly `seed` and `temperature`; the twin's differ in
   exactly `seed`. Proven with the production composer
   `reproduction.ojw.native_request.compose_solver_sample_decoding_params`. The renderer also omits
   the per-contact invocation index the real `agent_contact_id` carries, so at dispatch the five
   samples' markers read `solver:0` … `solver:4` where cell B0's reads `solver:0`.

The prepared first-phase Perception supply was rebuilt model-free for each cell and its `output`
equals cell B0's prepared artifact `output` **and** the anchor preparation's `output` on all
1,080 rows (4/4 for the smoke against cell B0's smoke artifact), `output_sha256` included, so the
knowledge channel does not move either.

## 4. The commit policy, fixed here

`saea-commit-plurality-support-v1` (`core.base.COMMIT_POLICIES`, implemented and registered in
`rails.commit_policies`), with the **preregistered thresholds `s = 3` of 5 and char-F1 `0.8`**:

- **Intent** = the plurality `(scenario, action)` over the parsed samples; ties broken by the lowest
  first-occurrence `sample_index`.
- **Entities** = same-type mentions clustered at normalized char-F1 `>= 0.8`, kept at support
  `>= 3` of 5 among non-malformed votes, the delivered filler being the cluster medoid (highest mean
  similarity to the rest of the cluster, ties to the lowest `sample_index`).
- Deterministic given the five sealed samples, and rendered in the exact format
  `reproduction.slurp_delivery` / `reproduction.slurp_scoring` already parse and score.

Custody is machine-enforced: `rails.native_episode_receipt.validate_solver_group_receipt` and
`core.flight.runtime` refuse to seal a declared-`samples >= 2` row without a `solver_group` carrying
all five raw samples, their seeds and temperatures, their parse status, and the delivered answer's
support and tie-break provenance.

**The offline sensitivity table is reported and never used for the verdict.**
`analysis/native_commit_replay.py` re-aggregates the sealed samples at `s` in {2, 3, 4} at char-F1
0.8, zero model contact. It is a diagnostic about the shape of the support surface. The verdict is
read at `s = 3`, char-F1 0.8, as fixed above before any contact.

## 5. Metrics

Primary: **official pooled SLU micro F1** from `slurp-slu-official-train` (pinned official
`evaluate.py`, `slurp-official-8eb16545`), natural mixture, one complete score per manifest through
`core.scoring_batch`, never sharded.

Secondaries: intent (joint scenario+action) accuracy, scenario accuracy, action accuracy, official
pooled span F1. Reported beside them: per-row mean official SLU-F1 and per-row mean exact slot F1,
saves/harms/ties with the exact two-sided McNemar p against base and against twin.

Per-row agreement diagnostics, mandatory in the verdict:

- the intent support-count distribution (5/5, 4/5, 3/5, 2/5, bare plurality) and the delivered
  intent accuracy within each stratum;
- entities kept and dropped by the support filter, by slot type, with the resulting false-positive
  and false-negative movement against the base;
- malformed sample count and the rows where fewer than five samples parsed;
- rows whose delivered answer differs from sample 0;
- the arm-versus-twin per-row sample disagreement rate — the direct measure of what temperature 0.7
  bought over batch-composition nondeterminism alone.

`delta = arm minus comparator`, in percentage points; a negative delta means the arm is worse.

## 6. Resampling and tables

Paired whole-speaker cluster bootstrap, **10,000 draws, seed 20260915**, CI95 for advancement and
CI90 for diagnostics, both as percentile pairs of the same retained replicate sequence.
Sensitivity: paired scenario-stratified row bootstrap, same draws and seed. Every verdict carries
the per-scenario table in both the natural-mixture and the equal-scenario weighting; the
equal-scenario delta is reported beside the natural-mixture point estimate and never replaces it.
Speaker clusters come from the released roster metadata (125 speakers, 18 scenarios of 60 rows,
523 headset and 557 far-field rows).

Four contrasts are computed: arm versus base (primary), arm versus twin (primary), twin versus base
(diagnostic: what the aggregation alone buys), and arm versus anchor (secondary).

## 7. Decision rule (fixed here, copied from the spec)

Null half-widths from `docs/readiness/2026-09-09-slurp-own-null-replicate-v1-verdict.md`: intent
0.92, SLU micro 1.18, scenario 0.83, action 0.98 percentage points.

- **ADMITTED** if the CI95 lower bound of the primary pooled SLU delta is greater than 0 against
  **both** the base and the twin, intent is non-inferior within 0.92 pp, the normalised scorer
  agrees in sign, and no scenario loses intent beyond the null band.
- **NEUTRAL** otherwise while non-inferior; it enters the default plan only if it lowers cost, which
  at 6 contacts per row against cell B0's 2 it does not.
- **HARMFUL** if an interval excludes non-inferiority on pooled SLU or on intent.

No repeat-to-pass: the verdict is read once, from the single official score of each complete
manifest. Scenario and action margins are diagnostics for the per-scenario table, not gates.

**Re-base note.** If cell B0's verdict is HARMFUL, the coordinator re-bases both full cells on the
sealed anchor before launch: the baseline fragments become anchor-based and every hash in this
package is recomputed. The spec's Phase B table is the authority.

## 8. Cost reporting (mandatory in the verdict)

- actual generation contacts, expected exactly 6 per row and 6,480 per full arm;
- contacts per row, expected 6.000, against cell B0's 2.000 and the anchor's 5.016;
- actual repeated speech seconds, expected 6 x 3,084.528 = 18,507.17;
- actual FIT endpoints, expected 4 per realized contact and 25,920 per full arm;
- **GPU hours** read from the serving monitor
  (`SPEECHRL_DATA_DIR/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl`)
  over each lease window, never a wall-clock guess;
- mean latency, slot occupancy and duty cycle from the same monitor;
- the realized prompt-cache behaviour of the five same-prefix sibling requests;
- preprocess and scoring wall time.

Registered ceilings, which are bounds and not targets, per full arm: 6,480 generation calls, 25,920
FIT endpoints, 18,508 repeated speech seconds, 5.0 fit-inclusive GPU hours, one official complete
scoring job, zero ASR, encoder, task-contract and paid-API calls. For the four-row smoke: 24
generation calls, 96 FIT endpoints, 64 repeated speech seconds, 0.3 GPU hours, zero scoring jobs.

**The 5.0 GPU-hour ceiling rests on an assumption that is not proven here.** The five sibling Solver
requests of one row are expected to share their cached prompt prefix on one slot: the model fragment
declares `decoding_params.id_slot "per-sample"` (resolved to one stable slot by the sequential
dispatcher) and the server runs with `--cache-prompt`, so after the first sample the remaining four
should reuse the prefill. The server also runs with `--no-cache-idle-slots` and
`--slot-prompt-similarity 0`. Against cell B0's measured two-contact cost, pessimistic linear
scaling would be 3x — about 4.2 GPU hours of generation — and 5.0 is the fit-inclusive ceiling over
that. The measured GPU hours are a mandatory verdict field, and the four-row smoke is the first
place this behaviour becomes visible.

## 9. Prompt fit

Measured bound from the anchor's own sealed native contact-fit receipts for exactly the two visits
this cell renders: `solver:0` required at most **13,157** tokens (minimum margin 11,419) and
`perception:0` at most **4,270** tokens (minimum margin 20,306), over 1,080 contacts each, all
fitting against the 24,576-token slot. Cell B2's Solver request size is unchanged from cell B0's:
the rendered envelope differs by 9 marker bytes, the epilogue by one digit, and the five siblings of
one visit share one rendered request. 13,157 tokens is therefore an upper bound on cell B2's own
Solver requirement. Receipt:
`SPEECHRL_DATA_DIR/coordination/slurp-b2-samples5-v1/prompt-fit-statement-v1.json`. Every realized
request is still fitted exactly by `native_contact_fit` immediately before transmission; this is a
bound, not a substitute for that gate.

## 10. Failure rule

The first failure stops the cell and preserves everything. No automatic restart, replay, row
filtering, roster, role-graph, prompt, geometry or cap change, no change to `samples`,
`temperature`, `seed_offset`, `min_support` or `similarity_threshold`, and no silent recovery. At
most one root-diagnosed recovery re-registration; a second failure closes the flight and the fix
must be proven on a four-row dry run before another mechanism is admitted. A failed four-row smoke
stops cell B2 until the fix is proven on that same four-row roster. One cell in flight at a time:
the arm seals before the twin launches.

## 11. What is NOT claimed

- No superiority, generalization, paper-scale or held-out claim. TRAIN Fold A is an exposed
  discovery roster.
- The offline `s` in {2,3,4} sensitivity table licenses no verdict, and no threshold may be chosen
  from it after the fact.
- No component-causal attribution beyond the one moved channel: an ADMITTED result says that
  sampling plus this aggregation pays in this configuration, not that N = 5 or `s = 3` is optimal.
- Nothing about Fold B, DEV-1000 or the test split; they stay unread.
- The prompt-cache assumption behind the 5.0 GPU-hour ceiling is stated, not proven.
- A structural smoke result is never a quality result.

## 12. Analysis recipe

`docs/readiness/2026-09-17-slurp-b2-samples5-v1/analysis-recipe-v1.json` pins the four score
artifacts, the roster metadata
(`analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`,
SHA-256 `07f4cd83b83d83d65500a328e0a38421ede575195c63ae118def0d1006c14e34`), the shared estimators
(`analysis.null_calibration_cli.rows_for`, `analysis.null_calibration.pooled_f1`,
`analysis.paired.resampled_statistic`, `analysis.paired.paired_contrast`), the commit replay
(`analysis.native_commit_replay.replay_row`), the seed, the draws, the two interval levels, the four
contrasts and the metric list. It reuses the released paired-read tooling of the 2026-09-17 TRAIN A
direct anchor release rather than a private reimplementation; `analysis.score_compare_cli` is
deliberately not the runner because it hard-codes CI90 and DEV population names.

## 13. Branch base and hash validity

This registration is based on master at `6c5c9ab7`. The composed and protocol hashes in section 2
are the values of the fragments **exactly as committed on this branch**: readiness `held`, the
preparation requirement pinned, `prepared_phase_supply` pinned. `compose` hashes the whole merged
four-fragment document, so the coordinator's readiness flip — and any later master merge that
touches `rails.kb_policy`, `rails.knowledge_provider`, `rails.phase_supply`,
`rails.knowledge_stores` or `core.flight.runtime`, which the prepared artifact's identity digest
pins — changes them. `docs/readiness/2026-09-17-slurp-b2-samples5-v1/README.md` section 7 gives the
exact re-pin sequence, and section 2 the pre-launch checklist.

## 14. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b2-samples5-v1/`, outside the repository so no
receipt can dirty the tree the scoring gate reads. The table of file names, SHA-256 values and what
each proves is in `docs/readiness/2026-09-17-slurp-b2-samples5-v1/README.md` section 8. The three
`core.flight.cli check` receipts of that table also re-derive each registered protocol hash at
runtime and report `ALLOW` for every phase.
